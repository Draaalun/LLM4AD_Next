# LLM4AD - MCM 2024 Problem D: Great Lakes Water Level Control

**Evolving *Modeling Methodologies*, not just Parameters.**

> ✅ **已完全集成到 LLM4AD 标准多岛框架** - 可直接通过 `llm4ad run config.yaml` 运行
>
> ✅ **Evaluator 注册完成** - `GreatLakesModelingEvaluator` 已正确注册并可被框架发现
>
> ✅ **Strict Custom Coder** - 严格只修改 EVOLVE 块内的 8 个基因型值，不生成额外代码
>
> ✅ **进化配置** - 4 岛屿 × 10 个体/岛，环形拓扑每 3 代迁移 Top 15%，70% LLM 变异 + 30% LLM 交叉

This project demonstrates LLM4AD's capability to automatically evolve **water resources modeling methodologies** (not just parameter values) in an 8-dimensional design space.

---

## 🎯 Core Concept

LLM4AD evolves **modeling methodologies**, not just parameter values. It searches across 8 fundamental design choices that define how you approach the Great Lakes control problem.

**8-dimensional design space:**
| Dimension | Design Choice | Alleles |
|-----------|--------------|---------|
| `dynamics` | System dynamics fidelity | `simple_mass_balance`, `seasonal_evap`, `flow_delay`, `stochastic_inflow` |
| `constraints` | Constraint handling | `hard_clipping`, `soft_penalty`, `barrier_function`, `leaky_constraint` |
| `objective_form` | Objective function math | `linear_weighted`, `chebyshev`, `exponential_utility`, `lexicographic`, `min_max_fairness` |
| `stakeholders` | Stakeholder subset | `core_3`, `balanced_4`, `comprehensive_5`, `full_6` |
| `solver` | Optimization algorithm | `nsga2`, `linear_program`, `mpc_rolling`, `particle_swarm`, `bayesian_opt` |
| `temporal` | Time architecture | `annual_monthly`, `seasonal_peak`, `multi_year`, `event_triggered` |
| `robustness` | Robustness paradigm | `deterministic`, `worst_case`, `stochastic_expected`, `stochastic_cvar` |
| `coupling` | Multi-objective coupling | `equal_weight`, `entropy_weight`, `ahp_hierarchy`, `pareto_filter`, `topsis` |

**Total search space: 4 × 4 × 5 × 4 × 5 × 4 × 4 × 5 = 128,000 unique modeling paradigms**

---

## 🏗 System Architecture

This is a **3-layer pure LLM-driven evolutionary architecture** for automated modeling methodology design:

| Layer | Role | Implementation |
|-------|------|----------------|
| **L1: Physical Simulation** | Runs accurate Great Lakes hydrological dynamics, computes stakeholder metrics, same physics for all candidates | `great_lakes_evaluator.py` |
| **L2: LLM-guided Island GA** | Multi-island parallel evolution with LLM as the only variation operator (no traditional GA). LLM intelligently mutates and crosses genotypes. | `config.yaml` + LLM4AD IslandGAOrchestrator |
| **L3: Meta-Learning** | [⏳ TODO] Dynamic search space expansion at runtime. Analyze evolution bottlenecks and inject new modeling paradigms. | `evolution/meta_learner.py` + `code_injector.py` |

---

## 🏗 LLM4AD 3-Layer Evolution Architecture

### Layer 1: Physical Simulation (Evaluator)
- Runs Great Lakes water level dynamics
- Computes 6 stakeholder metrics
- Same physics for all candidate algorithms

### Layer 2: Pure LLM-driven Evolution (no traditional GA)
- 100% LLM-guided evolutionary operators in LLM4AD standard Island GA framework:
  - **70% LLM intelligent mutation** (targeted design improvement based on fitness feedback)
  - **30% LLM semantic crossover** (intelligent parent strength fusion)
- Multi-island parallel evolution with ring topology migration
- Elitist selection with configurable population size and migration rate

### Layer 3: Meta-Learning (⏳ PLANNED)
**Dynamic Search Space Expansion at Runtime** - *Coming Soon:*
- **Triggers**: Every 10 generations (configurable) OR evolution stagnation detection
- **Pareto bottleneck analysis**: Identify which dimensions/alleles are limiting performance
- **Paradigm injection**: LLM suggests new modeling directions to guide L2 exploration
- **[Future] Propose new alleles**: Expand search space with novel dynamics/constraints/solvers
- **[Future] Python code generation**: LLM generates runnable code for new methods
- **[Future] Dynamic code injection**: Hot-patch new methods into evaluator at runtime
- **[Future] Evolutionary memory**: Persist successful paradigms across multiple runs

---

## 🚀 Quick Start

### 1. Environment Setup

```powershell
# Enter project directory
cd "C:\Users\79430\Desktop\LLM4AD\examples\applications\MCM_ICM_problem_2024_D"

# Set API environment variables
$env:OPENAI_API_KEY = "your_api_key_here"
$env:OPENAI_BASE_URL = "https://api.bltcy.ai/v1/"
$env:OPENAI_MODEL = "gpt-4o-mini"
```

### 2. Offline Validation (No API Key)

```powershell
# Verify all components work correctly
python test_full_system.py
```

### 3. Run Island GA Evolution

```powershell
llm4ad run config.yaml
```

---

## ⚙️ Evolution Configuration

Edit `config.yaml` to adjust scale:

```yaml
evolution:
  num_islands: 4                       # Number of parallel islands
  island_population_size: 10           # Individuals per island
  max_generations: 20                  # Total generations
  migration_interval: 3                # Migrate every N generations
  migration_rate: 0.15                 # Migrate top 15% individuals
  mutation_rate: 0.7                   # LLM-guided mutation rate
  crossover_rate: 0.3                  # LLM-guided crossover rate
```

---

## 🔄 Complete Execution Pipeline

```
Step 1: Repository Analysis
└── repo_analyzer scans template/genotype.py for # EVOLVE_START/END markers
    └── Finds: 1 EVOLVE block containing the 8-dimensional genotype dict

Step 2: Island Initialization
└── 4 parallel islands created, each with population size = 10
    └── init_sampler uses LLM to generate diverse initial genotypes

Step 3: Individual Generation
├── Create git worktree from template/ directory
├── LLM generates insight for the modeling methodology
├── LLM mutates the 8 allele values inside EVOLVE block (strict coder)
└── Result: genotype.py with modified dict values only (no extra code)

Step 4: Evaluation (GreatLakesModelingEvaluator)
├── Read genotype dict from worktree/genotype.py
├── Run physical simulation with:
│   ├── Selected dynamics model (mass balance / evaporation / stochastic)
│   ├── Selected constraint handling method (hard clip / soft penalty / barrier)
│   ├── Selected temporal discretization
├── Compute 9 metrics:
│   ├── 6 stakeholder objectives: flood, navigation, hydropower, recreation, ecosystem, municipal
│   ├── constraint_satisfaction
│   ├── backtesting_deviation
│   └── sensitivity_score
└── Apply objective_form + coupling method to compute overall_fitness

Step 5: Evolution Loop
├── Elitist selection (keep top individuals)
├── 70% LLM-guided mutation: LLM intelligently modifies genotype alleles
├── 30% LLM-guided crossover: Semantic fusion of parent genotypes
└── Tournament selection for survival

Step 6: Island Migration (every 3 generations)
└── Ring topology: Island 0 → Island 1 → Island 2 → Island 3 → Island 0
    └── Top 15% individuals migrate to neighbor islands

Step 7: L3 Meta-Learning (⏳ PLANNED)
├── Trigger: Every 10 generations (configurable in config.yaml)
├── Analyze allele frequency patterns & evolution bottlenecks
├── LLM provides strategic guidance for L2 exploration
└── [Future] Expand search space with new alleles + dynamic code injection

Step 8: Post-Processing & Analysis
├── Allele frequency analysis
├── Paradigm clustering (K-medoids archetype identification)
├── Sensitivity analysis across 100 scenarios
└── Benchmark comparison vs. published paper solutions
```

---

## 📁 Output Directory

Evolution results are saved to `runs/` (auto-generated):

```
runs/great_lakes_2024D/{run_id}/
├── worktrees/       # Per-individual genotype worktrees
├── generated/       # LLM generation metadata
├── checkpoints/     # Evolution checkpoints
└── logs/           # Execution logs
```

---

## ❓ FAQ

**Q: How to reduce API call cost?**
```yaml
evolution:
  num_islands: 1
  island_population_size: 6
  max_generations: 5
```

**Q: Evaluation fails, how to debug?**
```bash
# Run offline tests to identify the issue
python test_full_system.py
```

---

## 📁 Project Structure

```
MCM_ICM_problem_2024_D/
├── README.md                          # This file
├── LLM4AD_通用数模进化算法.md          # Universal algorithm design document
├── config.yaml           # LLM4AD evolution configuration
├── great_lakes_evaluator.py           # Core evaluator with physics
│
├── template/                          # Genotype template for evolution
│   └── genotype.py                    # 8-dimensional modeling choices
│
├── data/                              # Historical hydrological data
│   └── train/
│
├── references/                        # Problem background materials
│
├── comparison_with_opaper/            # Post-hoc benchmark vs published solutions
│
└── test_full_system.py                # Offline validation test suite
```

## ✅ Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| L1 Physical Simulation | ✓ Complete | Mass balance, seasonal evaporation, stochastic inflows |
| L1 Constraint Handlers | ✓ Complete | Hard clipping, soft penalty, barrier, leaky |
| L1 Solver Methods | ✓ Complete | Linear programming, MPC, PSO, Bayesian opt |
| L2 Island GA Orchestrator | ✓ Complete | LLM4AD standard multi-island framework, 4 islands |
| L2 LLM Mutation Operator | ✓ Complete | 70% intelligent targeted mutations |
| L2 LLM Crossover Operator | ✓ Complete | 30% semantic parent strength fusion |
| L3 Meta-Learning Config | ✓ Complete | Enabled in yaml, runs every 10 generations |
| L3 Bottleneck Analysis | ⏳ TODO | Allele frequency + Pareto limit detection |
| L3 Paradigm Injection | ⏳ TODO | Strategic guidance for L2 exploration |
| L3 New Allele Proposal | ⏳ TODO | LLM proposes novel modeling paradigms |
| L3 Python Code Generation | ⏳ TODO | Generate runnable code for new methods |
| L3 Dynamic Code Injection | ⏳ TODO | Hot-patch new methods into evaluator |
| Post-Processing: Gene Analysis | ✓ Complete | Frequency, fitness correlation |
| Post-Processing: Paradigm Clustering | ✓ Complete | K-medoids archetype identification |
| Post-Processing: Sensitivity Analysis | ✓ Complete | 100-scenario Monte Carlo |
| Post-Processing: Policy Recommendations | ⏳ TODO | LLM-based stakeholder tradeoff analysis |
| Post-Processing: Tradeoff Visualization | ⏳ TODO | Pareto frontier plots |

---

## 🧬 Genotype Format

Each candidate algorithm is represented as a genotype dictionary:

```python
GENOTYPE = {
    # EVOLVE_START
    "dynamics": "seasonal_evap",
    "constraints": "hard_clipping",
    "objective_form": "lexicographic",
    "stakeholders": "balanced_4",
    "solver": "nsga2",
    "temporal": "annual_monthly",
    "robustness": "stochastic_expected",
    "coupling": "equal_weight",
    # EVOLVE_END
}
```

The `# EVOLVE_START/END` markers define which parts of the code are modified by LLM during evolution.

---

## 📊 Performance Metrics

The evaluator computes 6 stakeholder metrics (all normalized to [0, 1], higher = better):

| Metric | Description |
|--------|-------------|
| `flood_prevention` | Minimize water level above flood threshold |
| `navigation` | Minimize water level below minimum ship draft |
| `hydropower` | Maximize flow through hydroelectric dams |
| `recreation` | Minimize level volatility for recreational use |
| `ecosystem` | Minimize deviation from historical levels |
| `municipal_water` | Minimize level below water intake infrastructure |

Plus:
- `constraint_satisfaction` - Measure of dam flow limit adherence
- `overall_score` - Combined score based on the chosen objective/coupling method

---

## 💡 Key Design Principles

1. **Search over modeling, not just parameters** - First find the right methodology, then optimize its parameters
2. **Semantic evolution, not random mutation** - LLM understands modeling tradeoffs before proposing changes
3. **Equal evaluation for all candidates** - Same physics, same metrics, same random seed for fair comparison
4. **Extensible search space** - The system can propose new alleles during meta-learning

---

## 🔗 Related Files

- `config.yaml` - Main evolution configuration
- `great_lakes_evaluator.py` - Physics simulation and metric calculation
- `comparison_with_opaper/` - Post-hoc analysis tools for benchmarking
- `template/genotype.py` - Starting point genotype for initial population
