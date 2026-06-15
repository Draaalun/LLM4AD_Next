# LLM4AD_Next

<p align="center">
  <strong>LLM for Algorithm Design</strong><br>
  Automated Algorithm Design powered by Large Language Models and Evolutionary Computation
</p>

<p align="center">
  <a href="https://pypi.org/project/llm4ad/">
    <img src="https://img.shields.io/pypi/v/llm4ad?color=blue" alt="PyPI Version">
  </a>
  <a href="https://pypi.org/project/llm4ad/">
    <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python Versions">
  </a>
  <a href="https://github.com/Optima-CityU/LLM4AD_Next/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-BSD--3--Clause-blue" alt="License">
  </a>
  <a href="https://github.com/Optima-CityU/LLM4AD_Next/actions/workflows/ci.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/Optima-CityU/LLM4AD_Next/ci" alt="CI">
  </a>
</p>

## Overview

LLM4AD is a modular platform that combines Large Language Models (LLMs) with evolutionary computation to automatically
design and optimize algorithms. It provides a flexible framework for leveraging AI to explore, generate, and evolve
algorithm implementations.

## Quick Start

<table>
  <tr>
    <td align="center" width="33%">
      <strong>Try Online</strong><br>
    </td>
    <td align="center" width="33%">
      <strong>Watch Instruction</strong><br>
    </td>
    <td align="center" width="33%">
      <strong>Read Docs</strong><br>
    </td>
  </tr>
  <tr>
    <td align="center" width="33%">
      Run LLM4AD_Next in your browser. No installation or API key required.
    </td>
    <td align="center" width="33%">
      Watch the introduction before installing or configuring a local environment.
    </td>
    <td align="center" width="33%">
      Use the documentation path map for setup, configuration, examples, and Web UI deployment.
    </td>
  </tr>
  <tr>
    <td align="center" width="33%">
      <a href="http://8.163.71.37/">
        <img src="https://img.shields.io/badge/Launch%20Online%20Demo-Open%20Now-2ea44f?style=for-the-badge"
             alt="Launch Online Demo">
      </a>
    </td>
    <td align="center" width="33%">
      <a href="https://youtu.be/x47kEosu0jk" target="_blank" rel="noopener noreferrer">
        <img src="https://img.shields.io/badge/Watch%20Instruction-YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white"
             alt="Watch the instruction video on YouTube">
      </a>
    </td>
    <td align="center" width="33%">
      <a href="docs/en/index.md">
        <img src="https://img.shields.io/badge/Open%20Documentation-Read%20Now-0969da?style=for-the-badge"
             alt="Open Documentation">
      </a>
    </td>
  </tr>
</table>

## Instruction Video

<div align="center">
  <a href="https://youtu.be/x47kEosu0jk" target="_blank" rel="noopener noreferrer">
    <img src="https://img.youtube.com/vi/x47kEosu0jk/maxresdefault.jpg"
         alt="LLM4AD_Next instruction video"
         width="720"
         height="405">
  </a>
</div>

## Features

- 🧠 **LLM-Powered Design** - Leverage state-of-the-art language models for algorithm ideation and generation
- 🧬 **Evolutionary Optimization** - Apply genetic algorithms to improve algorithm performance over generations
- 💬 **Interactive Configuration** - AI-powered consultant guides you through pipeline setup via conversation, generating
  a complete runnable application (evaluator, algorithm, config, debug runner)
- 🔍 **Evolve-Block Advisor** - On-demand feasibility/significance/concerns/suggestions for a user-selected code block
  versus a stated evolution goal
- 🎯 **Evolve-Block Recommender** - Point the platform at a repo + a goal and get ranked candidate blocks to evolve, each
  pre-scored by the advisor
- 📊 **Flexible Evaluation** - Define custom evaluation metrics and benchmarks with the registry-based evaluator system
- 🔌 **Multi-Provider Support** - Use OpenAI, Anthropic, or any OpenAI-compatible LLM providers
- 🚀 **Distributed Computing** - Scale experiments using Ray infrastructure
- 📝 **YAML Configuration** - Declarative configuration with global settings and environment variable support
- 💾 **Checkpoint & Resume** - Automatic checkpointing to resume interrupted experiments

## Run LLM4AD

### Option A: Online Demo (No Installation Required)

Use the online demo from [Quick Start](#quick-start), or open it directly:
[Launch Online Demo](http://8.163.71.37/).

No setup, no API key needed — just open the link and start designing algorithms.

### Option B: Local Installation

```bash
# Clone the repository
git clone https://github.com/Optima-CityU/LLM4AD_Next.git
cd LLM4AD_Next

# Install dependencies
uv sync

# Configure your LLM provider (see Global Settings section below)
# Or set environment variables directly:
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_API_KEY="your-api-key"
export LLM_MODEL="gpt-4o"

# Option 1: Interactive configuration (recommended for new users)
llm4ad chat

# Option 2: Run with an existing config file
llm4ad run examples/applications/tsp_benchmark_python/config.yaml
```

## Installation

### Requirements

- Python 3.10, 3.11, or 3.12
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Install uv (optional)

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Install LLM4AD

```bash
# Clone and install in development mode
git clone https://github.com/Optima-CityU/LLM4AD_Next.git
cd LLM4AD_Next
uv sync
```

### Optional Dependencies

Install specific groups based on your needs:

| Group       | Description                             |
|-------------|-----------------------------------------|
| `infra`     | Distributed computing (Ray, Prometheus) |
| `providers` | LLM provider integrations               |
| `eval`      | Evaluation and benchmarking tools       |
| `dev`       | Development tools (testing, linting)    |
| `docs`      | Documentation tools                     |
| `all`       | All optional dependencies               |

```bash
# Install with specific extras
uv sync --extra providers --extra infra
```

## Usage

### Command Line Interface

```bash
# Show help
llm4ad --help

# List registered components
llm4ad list

# Interactive configuration consultant (builds a full application)
llm4ad chat

# Use a specific provider from global settings
llm4ad chat --provider my_provider

# Resume a saved session
llm4ad chat --resume <session_id>

# Run a pipeline
llm4ad run config.yaml

# Evolve-Block Advisor: analyze a selected block against an evolution goal
llm4ad advise -g "minimize comparisons" -r ./solver --file algo.py --range 42:87
llm4ad advise --config advise_config.yaml

# Generate an advisor config template
llm4ad advise-init -o advise_config.yaml

# Evolve-Block Recommender: propose which block to evolve given a repo + goal
llm4ad recommend -g "reduce TSP tour length" -r ./solver
```

### Global Settings

Create `~/.llm4ad/settings.yaml` to configure shared providers across all projects:

```yaml
providers:
  - name: default
    type: openai
    api_key: ${OPENAI_API_KEY}
    model: gpt-4o
  - name: anthropic
    type: anthropic
    api_key: ${ANTHROPIC_API_KEY}
    model: claude-sonnet-4-20250514
```

Task configs then only need the provider name — credentials and model are resolved from global settings automatically.

### Interactive Chat (Task Builder)

`llm4ad chat` is an interactive assistant that guides you through building a complete LLM4AD application. It runs a
three-phase pipeline:

1. **Needs Gathering** - Conversational interview to understand your problem
2. **Building** - Generates evaluator, algorithm skeleton with `EVOLVE` markers, YAML config, and debug runner
3. **Review** - Presents the generated code for confirmation or modification

For existing projects, the chat can detect and reuse your evaluator, algorithm, config, and dataset — only generating
what's missing.

### Evolve-Block Advisor

The advisor answers: **"Is THIS block worth evolving for THIS goal?"** It runs a single LLM call on a user-selected
block and returns structured advice — feasibility, significance, concerns, suggestions, rationale.

```bash
# Analyze a specific block by file + line range
llm4ad advise -g "minimize comparisons" -r ./solver --file algo.py --range 42:87

# Repo with exactly one EVOLVE-marked block
llm4ad advise -g "reduce tour length" -r ./solver

# Raw snippet (no repo)
llm4ad advise -g "..." --code "$(cat patch.py)"
```

Python API:

```python
from llm4ad.advisor import advise_block_sync

advice = advise_block_sync(
    goal="minimize comparisons on random inputs",
    repo_path="./solver",
    file_path="algo.py",
    line_range=(42, 87),
    api_key="sk-...",
    model="gpt-4o",
)
print(advice.feasibility, advice.significance)
```

### Evolve-Block Recommender

When a user arrives with only a repo and a goal — no specific selection yet — the recommender **proposes** which block(
s) to evolve. It returns three tiers:

- **core**: the single most promising minimal block
- **expanded**: 0-3 widenings of core (same file, include helpers)
- **alternatives**: 0-3 independent blocks elsewhere worth evolving

```bash
# Scan a repo, print JSON to stdout
llm4ad recommend -g "reduce TSP tour length" -r ./solver

# Human-readable panels
llm4ad recommend -g "improve policy reward" -r ./lander --pretty
```

Python API:

```python
from llm4ad.advisor import recommend_blocks_sync

result = recommend_blocks_sync(
    goal="reduce TSP tour length",
    repo_path="./solver",
    api_key="sk-...",
    model="gpt-4o",
)
print(result.core.file_path, result.core.line_start, result.core.line_end)
```

### Python API

```python
import asyncio
from llm4ad import LLM4AD


async def main():
    llm4ad = LLM4AD("config.yaml")
    result = await llm4ad.run()
    if result.best_individual:
        print(f"Best score: {result.best_individual.score:.4f}")


asyncio.run(main())
```

## Documentation

- [Documentation Home](docs/en/index.md)
- [Quick Start Guide](docs/en/guides/quickstart.md)
- [Configuration Guide](docs/en/guides/configuration.md)
- [Writing Evaluators](docs/en/guides/evaluators.md)

### Local Development

```bash
# Serve documentation with live reload
mkdocs serve

# Build static documentation
mkdocs build
```

## Project Structure

```
LLM4AD/
├── src/llm4ad/          # Main source code
│   ├── config/           # Configuration schemas and global settings
│   ├── consultant/       # Interactive configuration wizard
│   ├── builder/          # Task builder (analyzer, creator, validator, writer)
│   ├── advisor/          # Evolve-block advisor and recommender
│   ├── provider/         # LLM provider implementations
│   ├── planner/          # Algorithm planning layer
│   ├── coder/            # Code generation layer
│   ├── evaluator/        # Evaluation layer
│   ├── orchestrator/     # Workflow orchestration
│   ├── infra/            # Infrastructure (Ray, monitoring)
│   └── utils/            # Utilities
├── examples/             # Example configurations and applications
├── tests/                # Test suite
└── docs/                 # Documentation
```

## Contributing

Contributions are welcome! Please read our [Contributing Guide](docs/en/contributing/guidelines.md) for details.

```bash
# Set up development environment
uv sync --extra all

# Run tests
pytest

# Format code
black src/ tests/
ruff check src/ tests/ --fix
```

## License

This project is licensed under the BSD 3-Clause License - see the [LICENSE](LICENSE) file for details.

## Support

- [Documentation](docs/en/index.md)
- [Discussions](https://github.com/Optima-CityU/LLM4AD_Next/discussions)
- [Issue Tracker](https://github.com/Optima-CityU/LLM4AD_Next/issues)

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Optima-CityU/LLM4AD_Next&type=Date)](https://www.star-history.com/#Optima-CityU/LLM4AD_Next&Date)
