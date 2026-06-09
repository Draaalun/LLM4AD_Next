"""TaskCreator agent: generate all LLM4AD application artifacts.

Takes an AnalysisResult from TaskAnalyzer and produces a complete
TaskBlueprint with evaluator code, algorithm code, YAML config,
and debug runner.
"""

from __future__ import annotations

import ast
import json
import re
import textwrap
from typing import Any

from loguru import logger

from llm4ad.builder.blueprint import AnalysisResult, TaskBlueprint
from llm4ad.builder.config_recommender import render_default_evolution_yaml
from llm4ad.builder.prompts import (
    CODER_PROMPT_TEMPLATE,
    CONFIG_YAML_TEMPLATE,
    CREATE_TASK_FROM_DRIVER_PROMPT,
    CREATE_TASK_MULTIMODAL_PROMPT,
    CREATE_TASK_PROMPT,
    GENERATE_DRIVER_PROMPT,
    get_algorithm_template,
    get_evaluator_template,
    get_multimodal_algorithm_template,
    get_multimodal_evaluator_template,
)
from llm4ad.infra.provider.base import BaseProvider


class TaskCreator:
    """Generate all LLM4AD application artifacts from analysis."""

    def __init__(self, provider: BaseProvider) -> None:
        """Initialize with an LLM provider for generation calls."""
        self._provider = provider

    async def create(
        self,
        analysis: AnalysisResult,
        description: str,
        *,
        multimodal: bool = False,
    ) -> TaskBlueprint:
        """Generate a complete TaskBlueprint from the analysis.

        Args:
            analysis: Structured problem analysis from TaskAnalyzer.
            description: Original user description for context.
            multimodal: Whether to generate a multimodal evaluator.

        Returns:
            TaskBlueprint with all artifacts populated.
        """
        if analysis.has_evolve_markers:
            return await self._create_reuse_algorithm(analysis, description, multimodal=multimodal)

        evaluator_register_name = analysis.project_name.replace("-", "_") + "_evaluator"
        metrics_json = json.dumps(analysis.metrics, indent=2)

        if multimodal:
            evaluator_template = get_multimodal_evaluator_template()
            algorithm_template = get_multimodal_algorithm_template()
            viz_spec = analysis.visualization_spec or {}
            prompt = CREATE_TASK_MULTIMODAL_PROMPT.format(
                project_name=analysis.project_name,
                background=analysis.background,
                function_name=analysis.function_name,
                function_signature=analysis.function_signature,
                function_description=analysis.function_description,
                input_format=analysis.input_format,
                output_format=analysis.output_format,
                metrics_json=metrics_json,
                algorithm_dir_name=analysis.algorithm_dir_name,
                algorithm_file_name=analysis.algorithm_file_name,
                evaluator_register_name=evaluator_register_name,
                evaluator_template=evaluator_template,
                algorithm_template=algorithm_template,
                visualization_spec_json=json.dumps(viz_spec, indent=2),
            )
        else:
            evaluator_template = get_evaluator_template()
            algorithm_template = get_algorithm_template()
            prompt = CREATE_TASK_PROMPT.format(
                project_name=analysis.project_name,
                background=analysis.background,
                function_name=analysis.function_name,
                function_signature=analysis.function_signature,
                function_description=analysis.function_description,
                input_format=analysis.input_format,
                output_format=analysis.output_format,
                metrics_json=metrics_json,
                algorithm_dir_name=analysis.algorithm_dir_name,
                algorithm_file_name=analysis.algorithm_file_name,
                evaluator_register_name=evaluator_register_name,
                evaluator_template=evaluator_template,
                algorithm_template=algorithm_template,
            )

        result = await self._provider.generate(prompt, temperature=0.4, max_tokens=8192)
        sections = self._parse_sections(result.text)

        evaluator_code = sections.get("EVALUATOR_CODE", "")
        algorithm_code = sections.get("ALGORITHM_CODE", "")
        debug_run_code = sections.get("DEBUG_RUN", "")
        test_evaluator_code = sections.get("TEST_EVALUATOR", "")
        sample_data_raw = sections.get("SAMPLE_DATA", "")
        metadata_raw = sections.get("METADATA", "{}")

        # Parse metadata
        metadata = self._parse_json_safe(metadata_raw)
        evaluator_class_name_raw = self._extract_evaluator_class_name(evaluator_code)
        evaluator_class_name: str = (
            evaluator_class_name_raw
            if evaluator_class_name_raw
            else metadata.get("evaluator_class_name", "TaskEvaluator")
        )

        # Build dataset files
        dataset_files: dict[str, str] = {}
        if sample_data_raw.strip() and sample_data_raw.strip().upper() != "NONE":
            dataset_files["data/sample/instance_001.json"] = sample_data_raw.strip()

        # Build evaluator filename
        evaluator_file_name = evaluator_register_name + ".py"

        # Build config YAML (programmatic, not LLM-generated)
        config_yaml = self._build_config_yaml(
            analysis, evaluator_class_name, evaluator_file_name, multimodal=multimodal,
        )

        return TaskBlueprint(
            project_name=analysis.project_name,
            task_description=analysis.background,
            evaluator_code=evaluator_code,
            algorithm_code=algorithm_code,
            config_yaml=config_yaml,
            debug_run_code=debug_run_code,
            evaluator_class_name=evaluator_class_name,
            evaluator_file_name=evaluator_file_name,
            algorithm_dir_name=analysis.algorithm_dir_name,
            algorithm_file_name=analysis.algorithm_file_name,
            function_to_evolve=analysis.function_name,
            metrics=analysis.metrics,
            dataset_files=dataset_files,
            source_code_path=None,
            test_evaluator_code=test_evaluator_code,
        )

    # ------------------------------------------------------------------
    # Reuse algorithm path (from_code with EVOLVE markers)
    # ------------------------------------------------------------------

    async def _create_reuse_algorithm(
        self,
        analysis: AnalysisResult,
        description: str,
        *,
        multimodal: bool = False,
    ) -> TaskBlueprint:
        """Generate artifacts using the EVOLVE block, branching on its semantic role.

        For complete_solver: programmatically assemble algorithm file.
        For sub_function/helper: LLM generates a driver script that wires the EVOLVE function.
        Then LLM generates evaluator + supporting files based on the algorithm/driver.
        """
        evaluator_register_name = analysis.project_name.replace("-", "_") + "_evaluator"
        metrics_json = json.dumps(analysis.metrics, indent=2)
        evaluator_template = (
            get_multimodal_evaluator_template() if multimodal else get_evaluator_template()
        )

        # Branch on function role
        if analysis.function_role == "complete_solver":
            algorithm_code = self._assemble_algorithm_file(analysis)
        else:
            # sub_function or helper: generate driver via LLM
            algorithm_code = await self._generate_driver_via_llm(analysis, description)

        # Generate evaluator + supporting files using the algorithm/driver as contract
        input_schema_json = json.dumps(analysis.input_schema or {}, indent=2)
        output_schema_json = json.dumps(analysis.output_schema or {}, indent=2)

        prompt = CREATE_TASK_FROM_DRIVER_PROMPT.format(
            project_name=analysis.project_name,
            background=analysis.background,
            function_name=analysis.function_name,
            metrics_json=metrics_json,
            algorithm_dir_name=analysis.algorithm_dir_name,
            algorithm_file_name=analysis.algorithm_file_name,
            driver_code=algorithm_code,
            input_schema_json=input_schema_json,
            output_schema_json=output_schema_json,
            evaluator_register_name=evaluator_register_name,
            evaluator_template=evaluator_template,
        )

        if multimodal:
            viz_spec = analysis.visualization_spec or {}
            prompt += (
                "\n\n## IMPORTANT: Multimodal Evaluator Requirements\n"
                "The evaluator MUST be a **multimodal** evaluator that generates "
                "visualization images alongside metrics.\n\n"
                f"Visualization spec: {json.dumps(viz_spec, indent=2)}\n\n"
                "Additional requirements:\n"
                "1. Import `BehaviorData`, `BehaviorVisualization` from `llm4ad.evaluator.behavior`\n"
                "2. Import `BaseRenderer` from `llm4ad.evaluator.renderer`\n"
                "3. Implement `_render_result_image()` that produces a base64 PNG visualization\n"
                "4. Implement `_build_observation_text()` for LLM-readable text summary\n"
                "5. Register a `BaseRenderer` subclass with `@BaseRenderer.register(...)`\n"
                "6. Handle `cfg.behavior_storage` modes: 'rendered', 'raw', 'none'\n"
                "7. Build `BehaviorData` with observation text + `BehaviorVisualization`\n"
            )

        result = await self._provider.generate(prompt, temperature=0.4, max_tokens=16384)
        sections = self._parse_sections(result.text)

        evaluator_code = sections.get("EVALUATOR_CODE", "")
        debug_run_code = sections.get("DEBUG_RUN", "")
        test_evaluator_code = sections.get("TEST_EVALUATOR", "")
        sample_data_raw = sections.get("SAMPLE_DATA", "")
        metadata_raw = sections.get("METADATA", "{}")

        metadata = self._parse_json_safe(metadata_raw)
        evaluator_class_name_raw = self._extract_evaluator_class_name(evaluator_code)
        evaluator_class_name: str = (
            evaluator_class_name_raw
            if evaluator_class_name_raw
            else metadata.get("evaluator_class_name", "TaskEvaluator")
        )

        dataset_files: dict[str, str] = {}
        if sample_data_raw.strip() and sample_data_raw.strip().upper() != "NONE":
            dataset_files["data/sample/instance_001.json"] = sample_data_raw.strip()

        evaluator_file_name = evaluator_register_name + ".py"

        config_yaml = self._build_config_yaml(
            analysis, evaluator_class_name, evaluator_file_name,
            multimodal=multimodal,
            algorithm_code_override=algorithm_code,
        )

        return TaskBlueprint(
            project_name=analysis.project_name,
            task_description=analysis.background,
            evaluator_code=evaluator_code,
            algorithm_code=algorithm_code,
            config_yaml=config_yaml,
            debug_run_code=debug_run_code,
            evaluator_class_name=evaluator_class_name,
            evaluator_file_name=evaluator_file_name,
            algorithm_dir_name=analysis.algorithm_dir_name,
            algorithm_file_name=analysis.algorithm_file_name,
            function_to_evolve=analysis.function_name,
            metrics=analysis.metrics,
            dataset_files=dataset_files,
            source_code_path=None,
            test_evaluator_code=test_evaluator_code,
        )

    async def _generate_driver_via_llm(
        self,
        analysis: AnalysisResult,
        description: str,
    ) -> str:
        """Generate a driver script via LLM for sub_function/helper roles."""
        classifier_output = json.dumps({
            "function_role": analysis.function_role,
            "input_schema": analysis.input_schema,
            "output_schema": analysis.output_schema,
            "needed_helpers": analysis.needed_helpers,
            "driver_strategy": analysis.driver_strategy,
        }, indent=2)

        prompt = GENERATE_DRIVER_PROMPT.format(
            description=description,
            full_code=analysis.algorithm_full_code or "",
            evolve_block=analysis.evolve_block_content or "",
            classifier_output=classifier_output,
        )

        result = await self._provider.generate(prompt, temperature=0.3, max_tokens=16384)
        return result.text.strip()

    @staticmethod
    def _assemble_algorithm_file(analysis: AnalysisResult) -> str:
        """Programmatically assemble a standalone algorithm file from the EVOLVE block.

        For complete_solver role: wraps the EVOLVE function with solve()/main() boilerplate.
        Uses input_schema to determine how to call the function.
        """
        evolve_content = analysis.evolve_block_content or ""
        func_name = analysis.function_name
        input_schema = analysis.input_schema or {}

        # Separate import lines from the rest of the EVOLVE block
        import_lines: list[str] = []
        code_lines: list[str] = []
        for line in evolve_content.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")) and "EVOLVE" not in stripped:
                import_lines.append(line)
            else:
                code_lines.append(line)

        evolve_body = "\n".join(code_lines)

        # Auto-detect commonly used modules referenced in the EVOLVE block
        auto_imports: list[str] = []
        all_evolve_text = evolve_content
        existing_import_text = "\n".join(import_lines)

        module_patterns = [
            ("np.", "numpy", "import numpy as np"),
            ("np.ndarray", "numpy", "import numpy as np"),
            ("math.", "math", "import math"),
            ("heapq.", "heapq", "import heapq"),
            ("heapq.heappush", "heapq", "import heapq"),
            ("copy.", "copy", "import copy"),
            ("copy.deepcopy", "copy", "import copy"),
            ("random.", "random", "import random"),
            ("itertools.", "itertools", "import itertools"),
            ("collections.", "collections", "from collections import deque"),
            ("deque(", "collections", "from collections import deque"),
            ("defaultdict(", "collections", "from collections import defaultdict"),
        ]
        for pattern, _module, import_stmt in module_patterns:
            if pattern in all_evolve_text and import_stmt not in existing_import_text:
                auto_imports.append(import_stmt)
                existing_import_text += f"\n{import_stmt}"

        # Combine all imports (deduplicated)
        all_imports = list(dict.fromkeys(import_lines + auto_imports))
        extra_imports = "\n".join(all_imports)
        if extra_imports:
            extra_imports = extra_imports + "\n"

        # Generate solve() body based on input_schema
        # If schema has a single key, pass that value directly; otherwise use **input_data
        if len(input_schema) == 1:
            single_key = list(input_schema.keys())[0]
            solve_call = f"result = {func_name}(input_data[\"{single_key}\"])"
        else:
            solve_call = f"result = {func_name}(**input_data)"

        return (
            "#!/usr/bin/env python3\n"
            f'"""Standalone algorithm file for LLM4AD evolution.\n'
            f"\n"
            f"Function to evolve: {func_name}\n"
            f'"""\n'
            "\n"
            "import json\n"
            "import sys\n"
            f"{extra_imports}"
            "\n"
            "# EVOLVE_START\n"
            f"{evolve_body}\n"
            "# EVOLVE_END\n"
            "\n"
            "\n"
            f"def solve(input_data):\n"
            f'    """Main solving function that delegates to the evolved algorithm."""\n'
            f"    {solve_call}\n"
            f"    if isinstance(result, dict):\n"
            f"        return result\n"
            f"    return {{\"result\": result}}\n"
            "\n"
            "\n"
            "def main():\n"
            '    """Entry point: read JSON from sys.argv[1], run algorithm, print JSON result."""\n'
            "    if len(sys.argv) < 2:\n"
            '        print("Usage: python solve.py \'<input_json>\'")\n'
            "        sys.exit(1)\n"
            "\n"
            "    input_data = json.loads(sys.argv[1])\n"
            "    result = solve(input_data)\n"
            "    print(json.dumps(result))\n"
            "\n"
            "\n"
            'if __name__ == "__main__":\n'
            "    main()\n"
        )

    # ------------------------------------------------------------------
    # Config generation (programmatic)
    # ------------------------------------------------------------------

    def _build_config_yaml(
        self,
        analysis: AnalysisResult,
        evaluator_class_name: str,
        evaluator_file_name: str,
        *,
        multimodal: bool = False,
        algorithm_code_override: str | None = None,
        evolution_yaml: str | None = None,
    ) -> str:
        """Build the YAML config programmatically from analysis results.

        Args:
            analysis: Structured problem analysis.
            evaluator_class_name: Name of the generated evaluator class.
            evaluator_file_name: Filename of the generated evaluator module.
            multimodal: Whether to include multimodal config section.
            algorithm_code_override: Custom algorithm code for the prompt template.
            evolution_yaml: Pre-rendered evolution YAML block. When ``None``,
                the default (simple-tier) parameters are used.
        """
        # Indent background for YAML block scalar
        background_indented = textwrap.indent(analysis.background.strip(), "  ")

        # Evaluator module reference
        evaluator_module = f"{evaluator_file_name}:{evaluator_class_name}"

        # Metrics list for YAML
        metric_names = [m["name"] for m in analysis.metrics]
        metrics_list = json.dumps(metric_names)

        # Dataset YAML
        if analysis.dataset_summary:
            dataset_yaml = '    mode: "directory"\n    path: "data/sample"\n    recursive: false'
        else:
            dataset_yaml = '    mode: "directory"\n    path: "data/sample"\n    recursive: false'

        # Multimodal config section
        if multimodal:
            multimodal_config_yaml = (
                "# ===== Multimodal Configuration =====\n"
                "multimodal:\n"
                '  enabled: true\n'
                '  max_images_per_prompt: 3\n'
                '  image_max_size_kb: 512\n'
                '  include_observation_text: true\n'
                '  behavior_storage: "rendered"\n'
                "\n"
            )
            planner_samplers_yaml = (
                '    - name: "multimodal_mutation_sampler"\n'
                '    - name: "multimodal_crossover_sampler"'
            )
        else:
            multimodal_config_yaml = ""
            planner_samplers_yaml = (
                '    - name: "mutation_sampler"\n'
                '    - name: "crossover_sampler"'
            )

        # Evolution parameters (rule-based or default)
        evo_yaml = evolution_yaml if evolution_yaml is not None else render_default_evolution_yaml()

        # Build coder prompt_template
        prompt_template = self._build_coder_prompt(
            analysis, algorithm_code_override=algorithm_code_override,
        )
        prompt_template_indented = textwrap.indent(prompt_template, "    ")

        config = CONFIG_YAML_TEMPLATE.format(
            project_name=analysis.project_name,
            background_indented=background_indented,
            multimodal_config_yaml=multimodal_config_yaml,
            evaluator_module=evaluator_module,
            metrics_list=metrics_list,
            dataset_yaml=dataset_yaml,
            algorithm_dir_name=analysis.algorithm_dir_name,
            planner_samplers_yaml=planner_samplers_yaml,
            prompt_template_indented=prompt_template_indented,
            evolution_yaml=evo_yaml,
        )
        return config

    def _build_coder_prompt(
        self,
        analysis: AnalysisResult,
        *,
        algorithm_code_override: str | None = None,
    ) -> str:
        """Build the coder prompt_template field for the YAML config.

        Args:
            analysis: Structured problem analysis.
            algorithm_code_override: When set, use this as the algorithm code
                in the prompt instead of generating a placeholder.
        """
        # Build optimization goals from metrics
        goals = []
        for m in analysis.metrics:
            direction = "higher is better" if m.get("type") == "maximize" else "lower is better"
            goals.append(f"- {m['name']}: {m.get('description', '')} ({direction})")
        optimization_goals = "\n".join(goals)

        if algorithm_code_override is not None:
            algorithm_code_for_prompt = algorithm_code_override
        else:
            # Build a placeholder algorithm code block for the prompt
            algorithm_code_for_prompt = (
            f"import json\nimport sys\n\n"
            f"# EVOLVE_START\n"
            f"{analysis.function_signature}\n"
            f"    \"\"\"{analysis.function_description}\"\"\"\n"
            f"    pass\n"
            f"# EVOLVE_END\n\n"
            f"def process(data):\n"
            f"    result = {analysis.function_name}(data)\n"
            f"    return {{\"result\": result}}\n\n"
            f"def main():\n"
            f"    if len(sys.argv) < 2:\n"
            f"        sys.exit(1)\n"
            f"    input_data = json.loads(sys.argv[1])\n"
            f"    result = process(input_data)\n"
            f"    print(json.dumps(result))\n\n"
            f"if __name__ == \"__main__\":\n"
            f"    main()"
        )

        return CODER_PROMPT_TEMPLATE.format(
            task_description=analysis.project_name.replace("_", " "),
            background=analysis.background,
            function_name=analysis.function_name,
            algorithm_code_for_prompt=algorithm_code_for_prompt,
            input_format=analysis.input_format,
            output_format=analysis.output_format,
            optimization_goals=optimization_goals,
        )

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_sections(text: str) -> dict[str, str]:
        """Parse delimited sections from LLM response.

        Expects format: ===SECTION_NAME=== followed by content.
        """
        sections: dict[str, str] = {}
        pattern = r"===([A-Z_]+)==="
        parts = re.split(pattern, text)

        # parts[0] is before first delimiter, then alternating name/content
        i = 1
        while i < len(parts) - 1:
            name = parts[i].strip()
            content = parts[i + 1].strip()
            # Strip leading/trailing markdown code fences
            content = _strip_code_fences(content)
            sections[name] = content
            i += 2

        if not sections:
            logger.warning("No delimited sections found in response, treating as single evaluator block")
            sections["EVALUATOR_CODE"] = _strip_code_fences(text)

        return sections

    @staticmethod
    def _parse_json_safe(text: str) -> dict[str, Any]:
        """Parse JSON from text, handling common LLM formatting issues."""
        text = text.strip()
        text = _strip_code_fences(text)
        try:
            result = json.loads(text)
            return result if isinstance(result, dict) else {}
        except json.JSONDecodeError:
            # Try to find JSON object
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    result = json.loads(text[start:end + 1])
                    return result if isinstance(result, dict) else {}
                except json.JSONDecodeError:
                    pass
        return {}

    @staticmethod
    def _extract_evaluator_class_name(evaluator_code: str) -> str | None:
        """Extract the evaluator class name from generated code using AST."""
        try:
            tree = ast.parse(evaluator_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a BaseEvaluator subclass
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == "BaseEvaluator":
                            return node.name
            return None
        except SyntaxError:
            return None


def _strip_code_fences(text: str) -> str:
    r"""Remove markdown code fences and any surrounding prose.

    Common LLM output patterns:
      1. Prose on both sides: "Here is the code:\n```python\n...\n```\nHope this helps."
      2. Only opening fence, no closing fence (truncated by max_tokens).
      3. Multiple fence blocks (rare; we take the first one).

    Take the content between the first fence and the next fence (or EOF).
    Any leftover ``` lines (nested or extra) are stripped defensively to
    avoid leaving fence markers inside the returned code.
    """
    text = text.strip()
    fence_start = text.find("```")
    if fence_start == -1:
        return text

    after_fence = text[fence_start:]
    lines = after_fence.split("\n")
    # Drop the opening ```python / ``` line.
    lines = lines[1:]
    # Cut at the next standalone ``` (closing fence) and discard trailing prose.
    for idx, line in enumerate(lines):
        if line.strip() == "```":
            lines = lines[:idx]
            break
    cleaned = "\n".join(lines).strip()
    # Defensive: drop any remaining bare ``` lines so they don't cause SyntaxError.
    cleaned_lines = [
        line for line in cleaned.split("\n")
        if line.strip() != "```" and not line.strip().startswith("```")
    ]
    return "\n".join(cleaned_lines).strip()
