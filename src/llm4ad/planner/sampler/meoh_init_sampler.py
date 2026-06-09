"""Initial sampler for MEoH."""

from __future__ import annotations

import json
import re
import time
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from llm4ad.infra.provider.base import BaseProvider
from llm4ad.infra.repo_analyzer.base import AnalyzedRepository
from llm4ad.infra.timing import ExecutionTiming
from llm4ad.planner.base import Algorithm, GenerationMetadata, InsightType
from llm4ad.planner.memory import Memory
from llm4ad.planner.sampler.base import BaseSampler
from llm4ad.planner.sampler.meoh_prompt_templates import build_i1_unified_prompt


class MEoHAlgorithmSchema(BaseModel):
    """Structured response for MEoH insight generation."""

    name: str | None = Field(default=None, description="Concise algorithm name")
    description: str = Field(..., description="Detailed algorithm description")


class MEoHUnifiedSchema(BaseModel):
    """Schema for unified MEoH generation (thought + code in one call)."""

    name: str | None = Field(default=None, description="Concise algorithm name")
    description: str = Field(..., description="Algorithm description and main steps")
    code: str = Field(..., description="Complete implementation code for the EVOLVE block")


class _BaseMEoHSampler(BaseSampler):
    """Shared helper for MEoH samplers."""

    def __init__(
        self,
        provider: BaseProvider,
        memory: Memory,
        config: dict[str, Any],
        analyzed_repository: AnalyzedRepository,
    ) -> None:
        super().__init__(provider, memory, config, analyzed_repository)
        provider_cfg = getattr(provider, 'config', None) or {}
        self.temperature = self._get_config_value("temperature", config, provider_cfg, default=0.7)
        self.max_tokens = self._get_config_value("max_tokens", config, provider_cfg, default=4096)

    def _first_block(self):
        if self.analyzed_repository and self.analyzed_repository.evolvable_blocks:
            return self.analyzed_repository.evolvable_blocks[0]
        return None

    async def _generate_algorithm(
        self,
        prompt: str,
        *,
        generation: int,
        insight_type: InsightType,
        operator: str,
        parent_ids: list[str],
    ) -> Algorithm:
        start_time = time.time()
        response = await self.provider.generate(
            prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            schema=MEoHAlgorithmSchema,
            request_stage="planner",
        )
        if response.parsed is None:
            raise ValueError(f"MEoH sampler {operator} failed to parse model output")

        payload: MEoHAlgorithmSchema = response.parsed  # type: ignore[assignment]
        algorithm_name = payload.name or self._derive_name(payload.description, operator)
        algorithm = Algorithm(
            insight_type=insight_type,
            name=algorithm_name,
            description=payload.description,
            generation=generation,
            parent_ids=parent_ids,
        )
        algorithm.update_timing(
            response.timing or ExecutionTiming.from_llm_stage("planner", (time.time() - start_time) * 1000)
        )
        algorithm.generation_meta = GenerationMetadata(
            operator=operator,
            llm_provider=self.provider.__class__.__name__,
            llm_model=getattr(self.provider, "model", "unknown"),
            temperature=self.temperature,
            generation_time_ms=(time.time() - start_time) * 1000,
            tokens_used=response.total_tokens,
            agent_name=self.__class__.__name__,
            change_description=payload.description,
            targeted_files=[self._first_block().file_path] if self._first_block() else [],
        )
        algorithm.custom_metadata["meoh_operator"] = operator
        return algorithm

    @staticmethod
    def _fallback_parse_unified(raw_text: str) -> MEoHUnifiedSchema | None:
        """Best-effort parser when the LLM emits malformed JSON (e.g. raw newlines in code field)."""
        if not raw_text:
            return None

        # Strip markdown fences
        text = raw_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```[^\n]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
            text = text.strip()

        # Attempt 1: fix unescaped newlines inside JSON string values by replacing
        # literal \n with \\n only inside quoted strings.
        try:
            # Replace real newlines inside JSON string values with \n escape
            fixed = re.sub(
                r'("(?:[^"\\]|\\.)*")',
                lambda m: m.group(0).replace("\n", "\\n"),
                text,
                flags=re.DOTALL,
            )
            data = json.loads(fixed)
            return MEoHUnifiedSchema(
                name=data.get("name"),
                description=data.get("description", ""),
                code=data.get("code", ""),
            )
        except Exception:
            pass

        # Attempt 2: regex-extract each field individually
        try:
            name_m = re.search(r'"name"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
            desc_m = re.search(r'"description"\s*:\s*"((?:[^"\\]|\\.)*)"', text, re.DOTALL)

            # For code, find everything between "code": " and the final closing "}\s*$
            code_m = re.search(r'"code"\s*:\s*"(.*?)"\s*\}', text, re.DOTALL)

            if desc_m and code_m:
                name = name_m.group(1) if name_m else None
                description = desc_m.group(1).replace("\\n", "\n").replace('\\"', '"')
                code = code_m.group(1).replace("\\n", "\n").replace('\\"', '"')
                return MEoHUnifiedSchema(name=name, description=description, code=code)
        except Exception:
            pass

        # Attempt 3: extract a markdown code block as the code, description from before it
        try:
            code_block_m = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
            if code_block_m:
                code = code_block_m.group(1).strip()
                before = text[: code_block_m.start()].strip()
                name_m = re.search(r'"name"\s*:\s*"([^"]+)"', before)
                desc_m = re.search(r'"description"\s*:\s*"((?:[^"\\]|\\.)*)"', before)
                description = desc_m.group(1) if desc_m else before[:200]
                name = name_m.group(1) if name_m else None
                return MEoHUnifiedSchema(name=name, description=description, code=code)
        except Exception:
            pass

        return None

    async def _generate_unified(
        self,
        prompt: str,
        *,
        generation: int,
        insight_type: InsightType,
        operator: str,
        parent_ids: list[str],
    ) -> Algorithm:
        """Generate algorithm description and code in a single LLM call."""
        start_time = time.time()
        response = await self.provider.generate(
            prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            schema=MEoHUnifiedSchema,
            request_stage="planner",
        )
        payload: MEoHUnifiedSchema | None = response.parsed  # type: ignore[assignment]

        if payload is None and response.text:
            payload = self._fallback_parse_unified(response.text)
            if payload is not None:
                logger.debug(f"MEoH unified sampler {operator}: used fallback JSON parser")

        if payload is None:
            raise ValueError(f"MEoH unified sampler {operator} failed to parse model output")

        algorithm_name = payload.name or self._derive_name(payload.description, operator)
        algorithm = Algorithm(
            insight_type=insight_type,
            name=algorithm_name,
            description=payload.description,
            generation=generation,
            parent_ids=parent_ids,
        )
        algorithm.custom_metadata["unified_code"] = payload.code
        algorithm.update_timing(
            response.timing or ExecutionTiming.from_llm_stage("planner", (time.time() - start_time) * 1000)
        )
        algorithm.generation_meta = GenerationMetadata(
            operator=operator,
            llm_provider=self.provider.__class__.__name__,
            llm_model=getattr(self.provider, "model", "unknown"),
            temperature=self.temperature,
            generation_time_ms=(time.time() - start_time) * 1000,
            tokens_used=response.total_tokens,
            agent_name=self.__class__.__name__,
            change_description=payload.description,
            targeted_files=[self._first_block().file_path] if self._first_block() else [],
        )
        algorithm.custom_metadata["meoh_operator"] = operator
        return algorithm

    @staticmethod
    def _derive_name(description: str, operator: str) -> str:
        """Derive a fallback algorithm name from the description."""
        words = [word.strip(" ,.:;()[]{}") for word in description.split() if word.strip(" ,.:;()[]{}")]
        if not words:
            return f"MEoH_{operator.upper()}"
        return " ".join(words[:6])


@BaseSampler.register("meoh_init_sampler")
class MEoHInitSampler(_BaseMEoHSampler):
    """Generate an initial MEoH insight."""

    @property
    def n_parents(self) -> int:
        """Return the number of required parents."""
        return 0

    @property
    def name(self) -> str:
        """Return the sampler name."""
        return "meoh_init_sampler"

    async def sample(self, population: list[Algorithm], generation: int, **kwargs) -> Algorithm:
        """Sample a new I1 algorithm."""
        prompt = build_i1_unified_prompt(kwargs.get("background", ""), self._first_block())
        return await self._generate_unified(
            prompt,
            generation=generation,
            insight_type=InsightType.INITIAL,
            operator="i1",
            parent_ids=[],
        )
