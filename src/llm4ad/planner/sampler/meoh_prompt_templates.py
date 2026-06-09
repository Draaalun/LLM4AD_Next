"""Prompt templates for the MEoH planner samplers."""

from __future__ import annotations

import re

from llm4ad.infra.repo_analyzer.base import EvolveBlock
from llm4ad.planner.base import Algorithm


def format_block_context(block: EvolveBlock | None) -> str:
    """Format EVOLVE block context for prompts."""
    if block is None:
        return "No EVOLVE block context is available."

    return (
        f"Target file: {block.file_path}\n"
        f"Language: {block.language}\n"
        f"Block name: {block.block_name or 'unnamed'}\n"
        "Context before:\n"
        f"{block.context_before}\n\n"
        "Current block content:\n"
        f"{block.original_content}\n\n"
        "Context after:\n"
        f"{block.context_after}\n"
    )


def summarize_algorithm_code(algorithm: Algorithm) -> str:
    """Create a code summary for an algorithm.

    Shows full code content so operators can understand and diverge
    from existing implementations.
    """
    if not algorithm.code_artifacts:
        return "No code artifacts."

    chunks: list[str] = []
    for artifact in algorithm.code_artifacts[:3]:
        chunks.append(f"File: {artifact.file_path}\n{artifact.content.strip()}")
    return "\n\n".join(chunks)


def format_parent_context(parents: list[Algorithm]) -> str:
    """Format parent algorithms for prompts (includes code)."""
    if not parents:
        return "No parent algorithms are provided."

    sections: list[str] = []
    for index, parent in enumerate(parents, start=1):
        sections.append(
            "\n".join(
                [
                    f"Parent {index}: {parent.name or parent.id}",
                    f"Description: {parent.description}",
                    f"Metrics: {parent.metrics}",
                    f"Score: {parent.score}",
                    f"Code summary: {summarize_algorithm_code(parent)}",
                ]
            )
        )
    return "\n\n".join(sections)


def format_parent_summaries_no_code(parents: list[Algorithm]) -> str:
    """Format parent algorithms without code — only descriptions and metrics."""
    if not parents:
        return "No parent algorithms are provided."

    sections: list[str] = []
    for index, parent in enumerate(parents, start=1):
        sections.append(
            "\n".join(
                [
                    f"Algorithm {index}: {parent.name or parent.id}",
                    f"Description: {parent.description}",
                    f"Metrics: {parent.metrics}",
                    f"Score: {parent.score}",
                ]
            )
        )
    return "\n\n".join(sections)


def extract_function_skeleton(block: EvolveBlock | None) -> str:
    """Extract function signature from an EVOLVE block with an empty body.

    Returns the function definition line(s) followed by ``pass``, forcing
    the LLM to write the implementation from scratch rather than copying
    from an existing body.
    """
    if block is None:
        return "# No EVOLVE block available — write a standalone function."

    content = block.original_content.strip()
    lines = content.split("\n")

    header_lines: list[str] = []
    for line in lines:
        header_lines.append(line)
        stripped = line.rstrip()
        if stripped.endswith(":") and not stripped.startswith("#"):
            break
        if stripped.endswith("):"):
            break

    if not header_lines:
        return content

    indent = ""
    match = re.match(r"(\s+)", lines[0])
    if match:
        indent = match.group(1)

    body_indent = indent + "    "
    return "\n".join(header_lines) + f"\n{body_indent}pass  # Your implementation here"


# Shared JSON format instruction for all unified prompts
_UNIFIED_JSON_SUFFIX = (
    'You MUST respond with a valid JSON object containing exactly three fields:\n'
    '{"name": "<algorithm name>", "description": "<your algorithm description>", '
    '"code": "<complete replacement code>"}\n'
    "CRITICAL JSON rules:\n"
    "- The entire response must be a single JSON object on one line or properly escaped\n"
    "- In the 'code' field, ALL newlines must be escaped as \\n (backslash-n), NOT literal newlines\n"
    "- In the 'code' field, ALL double-quotes must be escaped as \\\" \n"
    "The 'code' field must contain the COMPLETE code to place between "
    "EVOLVE_START and EVOLVE_END markers. This MUST include:\n"
    "- import statements at the top (e.g. import sys, import json, import numpy as np)\n"
    "- The function definition with the EXACT SAME NAME AND SIGNATURE as the function "
    "that already exists in 'Current block content' — do NOT rename it\n"
    "The code after EVOLVE_END calls the function by name and depends on these imports, "
    "so keep the exact function name from 'Current block content'. "
    "Do not include markdown fences or the EVOLVE markers themselves in the code field.\n"
    "IMPORTANT: The function receives 'nodes' as a Python list of (x, y) tuples (from json.loads), "
    "NOT a numpy array. You must convert it with np.array(nodes) before doing any numpy operations."
)


# ---------------------------------------------------------------------------
# Legacy (description-only) prompt builders — kept for backward compatibility
# ---------------------------------------------------------------------------


def build_i1_prompt(background: str, block: EvolveBlock | None) -> str:
    """Build the initial MEoH prompt."""
    return (
        "You are proposing an initial algorithm idea for automatic algorithm design.\n"
        f"Task background:\n{background}\n\n"
        f"Repository context:\n{format_block_context(block)}\n\n"
        "Return a concise algorithm name and a detailed description of a strong initial approach. "
        "The description should explain the main idea and intended benefit."
    )


def build_e1_prompt(background: str, block: EvolveBlock | None, parents: list[Algorithm]) -> str:
    """Build the E1 prompt."""
    return (
        "You are proposing a new algorithm with a substantially different form from the existing ones.\n"
        f"Task background:\n{background}\n\n"
        f"Repository context:\n{format_block_context(block)}\n\n"
        f"Existing algorithms:\n{format_parent_context(parents)}\n\n"
        "Create a new algorithm that is clearly distinct from the parents while staying relevant to the task."
    )


def build_e2_prompt(background: str, block: EvolveBlock | None, parents: list[Algorithm]) -> str:
    """Build the E2 prompt."""
    return (
        "You are proposing a new algorithm inspired by the common backbone of several existing methods.\n"
        f"Task background:\n{background}\n\n"
        f"Repository context:\n{format_block_context(block)}\n\n"
        f"Existing algorithms:\n{format_parent_context(parents)}\n\n"
        "Identify a shared backbone idea, then describe a new algorithm that is motivated by it but not a copy."
    )


def build_m1_prompt(background: str, block: EvolveBlock | None, parent: Algorithm) -> str:
    """Build the M1 prompt."""
    return (
        "You are mutating one existing algorithm into a structurally different variant.\n"
        f"Task background:\n{background}\n\n"
        f"Repository context:\n{format_block_context(block)}\n\n"
        f"Parent algorithm:\n{format_parent_context([parent])}\n\n"
        "Propose a modified algorithm with a noticeably different structure or search strategy."
    )


def build_m2_prompt(background: str, block: EvolveBlock | None, parent: Algorithm) -> str:
    """Build the M2 prompt."""
    return (
        "You are mutating one existing algorithm by changing parameters, scoring, or local heuristics.\n"
        f"Task background:\n{background}\n\n"
        f"Repository context:\n{format_block_context(block)}\n\n"
        f"Parent algorithm:\n{format_parent_context([parent])}\n\n"
        "Propose a modified algorithm that keeps the high-level idea but changes important parameters or local rules."
    )


def build_direct_code_prompt(background: str, block: EvolveBlock | None, algorithm: Algorithm) -> str:
    """Build a prompt for direct EVOLVE block code generation."""
    block_context = format_block_context(block)
    language = block.language if block is not None else "python"
    return (
        "You are implementing an evolved algorithm directly inside an EVOLVE block.\n"
        f"Task background:\n{background}\n\n"
        f"Repository context:\n{block_context}\n\n"
        f"Algorithm name: {algorithm.name}\n"
        f"Algorithm description:\n{algorithm.description}\n\n"
        "Return only the replacement code that should appear between EVOLVE START and EVOLVE END. "
        f"Do not include markdown fences. The language is {language}."
    )


# ---------------------------------------------------------------------------
# Unified prompt builders — produce thought + code in one LLM call
# ---------------------------------------------------------------------------


def build_i1_unified_prompt(background: str, block: EvolveBlock | None) -> str:
    """Build the unified I1 prompt (initial algorithm with code)."""
    block_ctx = format_block_context(block)
    return (
        f"{background}\n\n"
        f"Repository context (code surrounding the EVOLVE block):\n{block_ctx}\n\n"
        "Please propose an initial algorithm for the task described above.\n"
        "1. First, describe your algorithm: name it and explain the main idea.\n"
        "2. Then, write the complete replacement code for the EVOLVE block. "
        "Your code must define the same function(s) that the code after EVOLVE_END calls. "
        "Look at the 'Context after' section to see what function name and signature is expected.\n\n"
        f"{_UNIFIED_JSON_SUFFIX}"
    )


def build_e1_unified_prompt(
    background: str, block: EvolveBlock | None, parents: list[Algorithm]
) -> str:
    """Build the unified E1 prompt — totally different form, with parent code as reference."""
    parent_context = format_parent_context(parents)
    block_ctx = format_block_context(block)
    return (
        f"{background}\n\n"
        f"Repository context (code surrounding the EVOLVE block):\n{block_ctx}\n\n"
        f"I have {len(parents)} existing algorithms (shown with code for reference):\n"
        f"{parent_context}\n\n"
        "Please help me create a new algorithm that has a totally different form "
        "from the given ones.\n"
        "IMPORTANT: The parent code is provided only as REFERENCE to understand what "
        "has been tried. Do NOT copy or closely imitate their structure — your algorithm "
        "should use a fundamentally different approach or strategy.\n"
        "1. First, describe your new algorithm and main steps.\n"
        "2. Then, write the complete replacement code for the EVOLVE block. "
        "Your code must define the same function(s) that the code after EVOLVE_END calls. "
        "Look at the 'Context after' section to see what function name and signature is expected.\n\n"
        f"{_UNIFIED_JSON_SUFFIX}"
    )


def build_e2_unified_prompt(
    background: str, block: EvolveBlock | None, parents: list[Algorithm]
) -> str:
    """Build the unified E2 prompt — backbone-inspired, with parent code as reference."""
    parent_context = format_parent_context(parents)
    block_ctx = format_block_context(block)
    return (
        f"{background}\n\n"
        f"Repository context (code surrounding the EVOLVE block):\n{block_ctx}\n\n"
        f"I have {len(parents)} existing algorithms (shown with code for reference):\n"
        f"{parent_context}\n\n"
        "Please help me create a new algorithm that has a different form but is "
        "motivated by the backbone idea of the given algorithms.\n"
        "IMPORTANT: The parent code is provided only as REFERENCE. Identify the shared "
        "backbone IDEA (not code), then build a new algorithm that differs in implementation.\n"
        "1. First, identify the shared backbone idea from the algorithms above.\n"
        "2. Then, describe a new algorithm that builds on this backbone but differs in form.\n"
        "3. Write the complete replacement code for the EVOLVE block. "
        "Your code must define the same function(s) that the code after EVOLVE_END calls. "
        "Look at the 'Context after' section to see what function name and signature is expected.\n\n"
        f"{_UNIFIED_JSON_SUFFIX}"
    )


def build_m1_unified_prompt(
    background: str, block: EvolveBlock | None, parent: Algorithm
) -> str:
    """Build the unified M1 prompt — structural mutation, includes parent code."""
    parent_context = format_parent_context([parent])
    block_ctx = format_block_context(block)
    return (
        f"{background}\n\n"
        f"Repository context (code surrounding the EVOLVE block):\n{block_ctx}\n\n"
        f"I have one algorithm:\n{parent_context}\n\n"
        "Please help me create a modified version of this algorithm with a noticeably "
        "different structure or search strategy, while keeping it relevant to the task.\n"
        "The parent code is provided as reference. You should make structural changes to "
        "the approach, not just surface-level modifications.\n"
        "1. First, describe your new algorithm and what structural changes you make.\n"
        "2. Then, write the complete replacement code for the EVOLVE block. "
        "Your code must define the same function(s) that the code after EVOLVE_END calls. "
        "Look at the 'Context after' section to see what function name and signature is expected.\n\n"
        f"{_UNIFIED_JSON_SUFFIX}"
    )


def build_m2_unified_prompt(
    background: str, block: EvolveBlock | None, parent: Algorithm
) -> str:
    """Build the unified M2 prompt — parameter mutation, includes parent code."""
    parent_context = format_parent_context([parent])
    block_ctx = format_block_context(block)
    return (
        f"{background}\n\n"
        f"Repository context (code surrounding the EVOLVE block):\n{block_ctx}\n\n"
        f"I have one algorithm:\n{parent_context}\n\n"
        "Please help me create a modified version of this algorithm that keeps the "
        "high-level idea but changes important parameters, scoring functions, or local rules.\n"
        "The parent code is provided as reference. Focus on tuning parameters, thresholds, "
        "scoring functions, or local heuristic rules.\n"
        "1. First, describe what parameter/rule changes you make and why.\n"
        "2. Then, write the complete replacement code for the EVOLVE block. "
        "Your code must define the same function(s) that the code after EVOLVE_END calls. "
        "Look at the 'Context after' section to see what function name and signature is expected.\n\n"
        f"{_UNIFIED_JSON_SUFFIX}"
    )
