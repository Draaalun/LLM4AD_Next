# Advanced Configuration

This guide covers advanced usage patterns and configurations for LLM4AD.

## Multi-Objective Optimization

LLM4AD supports optimizing multiple objectives simultaneously.

### Defining Multiple Metrics

Define multiple metrics in your evaluator:

```python
@property
def metrics(self) -> list[Metric]:
    return [
        Metric(
            name="accuracy",
            type=MetricType.MAXIMIZE,
            weight=1.0
        ),
        Metric(
            name="inference_time",
            type=MetricType.MINIMIZE,
            weight=0.5
        ),
        Metric(
            name="memory_usage",
            type=MetricType.MINIMIZE,
            weight=0.3
        ),
    ]
```

### Pareto Front Analysis

LLM4AD automatically computes Pareto-optimal solutions:

```yaml
evolution:
  # Enable Pareto front tracking
  track_pareto_front: true
  pareto_epsilon: 0.01  # Tolerance for dominance
```

## Distributed Computing

Use Ray for distributed evaluation across multiple machines.

### Enabling Ray

```yaml
infra:
  type: "ray"
  ray:
    address: "auto"  # or "ray://head-node:10001"
    num_workers: 4
    resources_per_worker:
      cpu: 2
      memory: "4GB"
```

### Ray Cluster Setup

```bash
# Start Ray head node
ray start --head --port=6379

# Start worker nodes
ray start --address=head-node:6379

# Run LLM4AD with Ray
llm4ad run config.yaml
```

## Custom Selection Strategies

Implement custom selection strategies for evolution.

### Creating Custom Selector

```python
from llm4ad.utils.registry import Registry

selector_registry = Registry("selector", BaseSelector)


@selector_registry.register("my_selector")
class MySelector(BaseSelector):
    """Custom selection strategy."""

    def select(
        self,
        population: list[Individual],
        num_parents: int
    ) -> list[Individual]:
        """Select parents for reproduction."""
        # Your selection logic here
        pass
```

### Using Custom Selector

```yaml
evolution:
  selection_strategy: "my_selector"
  custom_selector_params:
    param1: value1
    param2: value2
```

## Memory System

Configure memory for storing and retrieving past designs. The memory system supports:

- **Static memory cards**: domain knowledge and hints defined in YAML config
- **Auto-extraction**: LLM-based extraction of insights from evaluated algorithms (both good and bad)
- **Persistent storage**: memory cards saved as individual YAML files in a dedicated `memory/` subdirectory

### Basic Configuration

```yaml
memory:
  max_entries: 10000
  similarity_threshold: 0.8
  decay_factor: 0.99
  max_prompt_cards: 5       # Max cards per sampler prompt
  persist: true              # Persist auto-extracted cards to disk
```

### Static Memory Cards

Define domain knowledge and hints inline in your config:

```yaml
memory:
  static_cards:
    - type: "domain_knowledge"
      title: "Platform constraints"
      content: "Limited stack depth (1024 frames). Prefer iterative algorithms."
      tags: [constraints, platform]
    - type: "general_insight"
      title: "Sorting tip"
      content: "Hybrid approaches combining quicksort with insertion sort work well."
      tags: [sorting, hybrid]
```

### Auto-Extraction

The system automatically extracts memory from two types of algorithms after evaluation:

- **Good algorithms** (top performers): captures what worked and why
- **Bad algorithms** (poor performers / failures): captures what to avoid

```yaml
memory:
  auto_extraction:
    enabled: true
    max_cards_per_generation: 3
    extraction_temperature: 0.3

    # Good algorithm extraction
    extract_good: true
    good_relative_threshold: 0.8   # Top 20% of population

    # Bad algorithm extraction
    extract_bad: true
    bad_relative_threshold: 0.2    # Bottom 20% of population
    extract_on_failure: true       # Also extract from crashes/timeouts
```

### Memory in Prompts

Memory context is automatically injected into all sampler prompts, organized into clear sections:

```
### Successful Patterns (what works)
- **Hybrid quicksort** (score: 0.92, gen 5): Combining quicksort with insertion sort...

### Pitfalls to Avoid (what doesn't work)
- **Pure recursive approach** (score: 0.12, gen 2): Deep recursion caused stack overflow...

### Domain Knowledge
- **Platform constraints**: Limited stack depth. Prefer iterative algorithms.
```

## Checkpointing and Resume

Save and resume from checkpoints.

### Checkpoint Configuration

```yaml
evolution:
  checkpoint_interval: 10  # Save every 10 generations
  max_checkpoints: 5    # Keep last 5 checkpoints

  # Checkpoint format
  checkpoint_format: "json"  # or "pickle", "yaml"
```

### Resuming from Checkpoint

```bash
# List available checkpoints
llm4ad list-checkpoints ./runs/my-project/

# Resume from specific checkpoint
llm4ad resume ./runs/my-project/checkpoint_gen_20.json
```

## Version Control Integration

Use Git worktrees for isolated code generation.

### Git Worktree Configuration

```yaml
version_control:
  enabled: true
  type: "git_worktree"
  repo_path: "."
  worktree_base: "./worktrees"
  auto_cleanup: true

  # Commit settings
  commit_on_success: true
  commit_message_template: "Algorithm: {algorithm_name}, Score: {score}"
```

### Branch Management

```bash
# Create feature branch for experiment
git checkout -b experiment-001

# Run LLM4AD (creates worktrees)
llm4ad run config.yaml

# Merge best algorithm back
git checkout main
git merge experiment-001
```

## Monitoring and Logging

Configure monitoring for production use.

### Prometheus Metrics

```yaml
monitoring:
  type: "prometheus"
  prometheus:
    enabled: true
    port: 9090
    metrics:
      - "generation_time"
      - "evaluation_time"
      - "population_score"
      - "convergence_rate"
```

### Structured Logging

```yaml
logging:
  level: "INFO"
  format: "json"  # JSON format for log aggregation
  file: "./logs/experiment.jsonl"
  console: false

  # Log rotation
  rotation:
    max_size: "100MB"
    backup_count: 10
```

## Hyperparameter Tuning

Use LLM4AD for hyperparameter optimization.

### Grid Search

```python
import itertools

# Define parameter grid
param_grid = {
    "temperature": [0.3, 0.5, 0.7],
    "population_size": [20, 50, 100],
    "mutation_rate": [0.2, 0.3, 0.4],
}

# Generate all combinations
for params in itertools.product(*param_grid.values()):
    config = load_base_config()
    config.providers[0].temperature = params[0]
    config.evolution.population_size = params[1]
    config.evolution.mutation_rate = params[2]

    # Run experiment
    run_experiment(config)
```

### Bayesian Optimization

```python
from optuna import create_study

def objective(trial):
    config = load_base_config()

    # Suggest parameters
    config.providers[0].temperature = trial.suggest_float("temp", 0.1, 1.0)
    config.evolution.population_size = trial.suggest_int("pop_size", 10, 100)
    config.evolution.mutation_rate = trial.suggest_float("mut_rate", 0.1, 0.5)

    # Run experiment and return score
    result = run_experiment(config)
    return result.best_score

# Run optimization
study = create_study(direction="maximize")
study.optimize(objective, n_trials=50)
```

## Custom Coder Strategies

Implement custom code generation strategies.

### Targeted Evolution

```yaml
coder:
  type: "custom"
  strategy: "targeted_evolution"

  # Target specific code blocks
  targets:
    - "EVOLVE: main_loop"
    - "EVOLVE: optimization"

  # Evolution parameters
  evolution_params:
    insertion_rate: 0.2
    deletion_rate: 0.1
    replacement_rate: 0.3
```

### Multi-File Generation

```python
class MultiFileCoder(BaseCoder):
    """Generates multiple files."""

    async def generate(self, prompt: str) -> dict[str, str]:
        """Generate multiple code files."""
        files = {}

        # Generate main file
        files["main.py"] = await self._generate_main(prompt)

        # Generate helper files
        files["utils.py"] = await self._generate_utils(prompt)
        files["config.py"] = await self._generate_config(prompt)

        return files
```

## Performance Optimization

### Parallel Evaluation

```yaml
evaluator:
  parallel: true
  batch_size: 10  # Evaluate 10 instances in parallel

  # Process pool settings
  max_workers: 8
  chunk_size: 5
```

### Caching

```yaml
cache:
  enabled: true
  cache_dir: "./cache"
  max_size: "1GB"

  # Cache keys
  cache_by: "code_hash"  # or "prompt_hash", "full_hash"
```

### Resource Limits

```yaml
resources:
  max_memory: "16GB"
  max_cpu: 8
  max_gpu: 1

  # Timeout per generation
  generation_timeout: 300
  evaluation_timeout: 60
```

## Best Practices

1. **Start Small**: Begin with simple configurations
2. **Monitor Resources**: Track CPU, memory, and API usage
3. **Use Checkpoints**: Enable checkpointing for long runs
4. **Tune Parameters**: Adjust evolution parameters for your problem
5. **Version Control**: Use Git worktrees for clean code management
6. **Distribute Work**: Use Ray for large-scale experiments
7. **Log Everything**: Enable structured logging for analysis

## Next Steps

- [Configuration Guide](configuration.md) - Basic configuration
- [Writing Evaluators](evaluators.md) - Create custom evaluators
- [Quick Start Guide](quickstart.md) - Run your first experiment
