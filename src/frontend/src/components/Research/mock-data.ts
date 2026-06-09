export interface SessionGroup {
  id: string
  name: string
  createdAt: string
  isCollapsed: boolean
}

export interface ResearchSession {
  id: string
  title: string
  groupId: string | null
  createdAt: string
  updatedAt: string
  currentStep: number
  steps: StepState[]
  messages: ChatMessage[]
  config: ResearchConfig
}

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: string
  step: number
}

export interface ArtifactVersion {
  id: string
  version: number
  label: string
  timestamp: string
  content?: string
  artifacts?: Artifact[]
}

export interface StepState {
  status: "pending" | "running" | "completed" | "failed"
  versions: ArtifactVersion[]
  activeVersionId: string | null
  logs: LogEntry[]
  messages: ChatMessage[]
}

export interface Artifact {
  id: string
  name: string
  type: "code" | "pdf" | "markdown" | "chart"
  content: string
}

export interface LogEntry {
  id: string
  timestamp: string
  level: "info" | "warn" | "error" | "debug"
  message: string
}

export interface ResearchConfig {
  provider: string
  model: string
  evolutionAlgorithm: "IslandGA" | "DyCA" | "MEoH"
  maxIterations: number
  populationSize: number
  temperature: number
}

export interface SessionSnapshot {
  id: string
  sessionId: string
  name: string
  createdAt: string
  currentStep: number
  steps: StepState[]
  config: ResearchConfig
}

export const DEFAULT_CONFIG: ResearchConfig = {
  provider: "openai",
  model: "gpt-4o",
  evolutionAlgorithm: "IslandGA",
  maxIterations: 50,
  populationSize: 20,
  temperature: 0.7,
}

export function createEmptySession(
  id: string,
  title: string,
  groupId: string | null = null,
): ResearchSession {
  return {
    id,
    title,
    groupId,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    currentStep: 0,
    steps: [
      {
        status: "pending",
        versions: [],
        activeVersionId: null,
        logs: [],
        messages: [],
      },
      {
        status: "pending",
        versions: [],
        activeVersionId: null,
        logs: [],
        messages: [],
      },
      {
        status: "pending",
        versions: [],
        activeVersionId: null,
        logs: [],
        messages: [],
      },
      {
        status: "pending",
        versions: [],
        activeVersionId: null,
        logs: [],
        messages: [],
      },
    ],
    messages: [],
    config: { ...DEFAULT_CONFIG },
  }
}

const MOCK_BACKGROUND_V1 = `## Background Research: TSP

### Problem Definition
The Traveling Salesman Problem (TSP) is a classic combinatorial optimization problem.

### Related Work
- **Branch and Bound**: Guarantees optimal solution but exponential time
- **Nearest Neighbor**: Simple greedy approach, O(n²)
- **Genetic Algorithm**: Population-based evolutionary approach
`

const MOCK_BACKGROUND_V2 = `## Background Research: Traveling Salesman Problem (TSP)

### Problem Definition
The Traveling Salesman Problem (TSP) is a classic combinatorial optimization problem. Given a set of cities and distances between them, the goal is to find the shortest possible route that visits each city exactly once and returns to the origin city.

### Related Work

#### Exact Methods
- **Branch and Bound**: Guarantees optimal solution but exponential time complexity
- **Dynamic Programming (Held-Karp)**: O(n²·2ⁿ) time, practical for n ≤ 25

#### Heuristic Methods
- **Nearest Neighbor**: Simple greedy approach, O(n²)
- **Christofides Algorithm**: 3/2-approximation guarantee
- **Lin-Kernighan**: One of the best local search heuristics

#### Metaheuristic Methods
- **Genetic Algorithm**: Population-based evolutionary approach
- **Ant Colony Optimization**: Inspired by ant foraging behavior
- **Simulated Annealing**: Probabilistic local search

#### Neural Combinatorial Optimization
- **Attention Model (Kool et al.)**: Transformer-based learned heuristic
- **RL for Routing**: Reinforcement learning for sequential decision making

### Key Insights
1. LLM-based algorithm design can discover novel heuristics
2. Combining local search with evolutionary strategies shows promise
3. Instance-specific algorithm selection can improve performance

### Proposed Direction
Design an adaptive heuristic using LLM-guided evolution that combines:
- Constructive heuristics for initial solutions
- Perturbation operators for diversification
- Local search for intensification
`

const MOCK_DESIGN_CONTENT = `## Algorithm Design: Adaptive LLM-Evolved TSP Heuristic

### Architecture Overview
The algorithm consists of three main components:
1. **Solution Constructor** - Builds initial solutions using learned priority rules
2. **Perturbation Engine** - Applies evolved perturbation operators
3. **Local Search Module** - Refines solutions using 2-opt and Or-opt moves

### Key Design Decisions
| Component | Choice | Rationale |
|-----------|--------|-----------|
| Representation | Permutation | Natural for TSP |
| Construction | Priority-based | Flexible, learnable |
| Local Search | 2-opt + Or-opt | Good balance of quality and speed |
| Evolution | Island GA | Diversity preservation |

### Fitness Function
\`\`\`
fitness(algorithm) = -average_tour_length(algorithm, test_instances)
\`\`\`
`

const MOCK_ALGORITHM_CODE = `import numpy as np
from typing import List

def heuristic(distance_matrix: np.ndarray) -> List[int]:
    """Adaptive TSP heuristic evolved by LLM4AD_Next."""
    n = len(distance_matrix)
    visited = [False] * n
    tour = [0]
    visited[0] = True

    for _ in range(n - 1):
        current = tour[-1]
        best_next = -1
        best_score = float('inf')

        for j in range(n):
            if not visited[j]:
                dist = distance_matrix[current][j]
                min_ahead = min(
                    (distance_matrix[j][k] for k in range(n)
                     if not visited[k] and k != j),
                    default=0
                )
                score = dist + 0.3 * min_ahead
                if score < best_score:
                    best_score = score
                    best_next = j

        tour.append(best_next)
        visited[best_next] = True

    improved = True
    while improved:
        improved = False
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                delta = (
                    distance_matrix[tour[i-1]][tour[j]]
                    + distance_matrix[tour[i]][tour[(j+1) % n]]
                    - distance_matrix[tour[i-1]][tour[i]]
                    - distance_matrix[tour[j]][tour[(j+1) % n]]
                )
                if delta < -1e-10:
                    tour[i:j+1] = reversed(tour[i:j+1])
                    improved = True

    return tour
`

export const MOCK_SESSIONS: ResearchSession[] = [
  {
    id: "session-1",
    title: "TSP Heuristic Design",
    groupId: null,
    createdAt: "2025-05-08T10:30:00Z",
    updatedAt: "2025-05-08T14:20:00Z",
    currentStep: 2,
    steps: [
      {
        status: "completed",
        versions: [
          {
            id: "v0-1",
            version: 1,
            label: "v1",
            timestamp: "2025-05-08T10:30:15Z",
            content: MOCK_BACKGROUND_V1,
          },
          {
            id: "v0-2",
            version: 2,
            label: "v2 (refined)",
            timestamp: "2025-05-08T10:30:30Z",
            content: MOCK_BACKGROUND_V2,
          },
        ],
        activeVersionId: "v0-2",
        logs: [
          {
            id: "l1",
            timestamp: "2025-05-08T10:30:05Z",
            level: "info",
            message: "Starting background research...",
          },
          {
            id: "l1b",
            timestamp: "2025-05-08T10:30:08Z",
            level: "info",
            message: "Querying literature database for TSP-related papers...",
          },
          {
            id: "l1c",
            timestamp: "2025-05-08T10:30:10Z",
            level: "info",
            message: "Found 47 relevant papers from 2020-2025",
          },
          {
            id: "l2",
            timestamp: "2025-05-08T10:30:12Z",
            level: "info",
            message: "Analyzing related work on TSP...",
          },
          {
            id: "l2b",
            timestamp: "2025-05-08T10:30:15Z",
            level: "info",
            message:
              "Categorizing approaches: exact, heuristic, metaheuristic, ML-based",
          },
          {
            id: "l2c",
            timestamp: "2025-05-08T10:30:18Z",
            level: "debug",
            message: "Extracting key findings from top-cited papers",
          },
          {
            id: "l2d",
            timestamp: "2025-05-08T10:30:20Z",
            level: "info",
            message: "Summarizing neural combinatorial optimization methods",
          },
          {
            id: "l2e",
            timestamp: "2025-05-08T10:30:22Z",
            level: "info",
            message: "Comparing performance benchmarks across approaches",
          },
          {
            id: "l2f",
            timestamp: "2025-05-08T10:30:24Z",
            level: "warn",
            message:
              "Some benchmark results may not be directly comparable due to different instance sizes",
          },
          {
            id: "l2g",
            timestamp: "2025-05-08T10:30:26Z",
            level: "info",
            message: "Identifying research gaps and opportunities",
          },
          {
            id: "l2h",
            timestamp: "2025-05-08T10:30:28Z",
            level: "info",
            message: "Generating structured literature review document",
          },
          {
            id: "l3",
            timestamp: "2025-05-08T10:30:30Z",
            level: "info",
            message: "Background research completed successfully.",
          },
        ],
        messages: [],
      },
      {
        status: "completed",
        versions: [
          {
            id: "v1-1",
            version: 1,
            label: "v1",
            timestamp: "2025-05-08T11:02:30Z",
            content: MOCK_DESIGN_CONTENT,
            artifacts: [
              {
                id: "a1",
                name: "heuristic.py",
                type: "code",
                content: MOCK_ALGORITHM_CODE,
              },
            ],
          },
        ],
        activeVersionId: "v1-1",
        logs: [
          {
            id: "l4",
            timestamp: "2025-05-08T11:00:05Z",
            level: "info",
            message: "Initializing algorithm design module...",
          },
          {
            id: "l4b",
            timestamp: "2025-05-08T11:00:12Z",
            level: "info",
            message: "Loading background research context (2 documents)",
          },
          {
            id: "l4c",
            timestamp: "2025-05-08T11:00:18Z",
            level: "info",
            message: "Analyzing problem structure and constraints",
          },
          {
            id: "l4d",
            timestamp: "2025-05-08T11:00:25Z",
            level: "debug",
            message:
              "Identified key operators: construction, perturbation, local search",
          },
          {
            id: "l4e",
            timestamp: "2025-05-08T11:00:35Z",
            level: "info",
            message: "Designing solution representation (permutation-based)",
          },
          {
            id: "l4f",
            timestamp: "2025-05-08T11:00:48Z",
            level: "info",
            message:
              "Generating constructive heuristic with look-ahead scoring",
          },
          {
            id: "l4g",
            timestamp: "2025-05-08T11:01:00Z",
            level: "info",
            message: "Generating 2-opt local search refinement module",
          },
          {
            id: "l4h",
            timestamp: "2025-05-08T11:01:15Z",
            level: "info",
            message:
              "Composing algorithm pipeline: construct → perturb → refine",
          },
          {
            id: "l4i",
            timestamp: "2025-05-08T11:01:30Z",
            level: "warn",
            message:
              "Look-ahead depth > 2 may impact performance on large instances",
          },
          {
            id: "l4j",
            timestamp: "2025-05-08T11:01:45Z",
            level: "info",
            message: "Writing algorithm code to heuristic.py",
          },
          {
            id: "l4k",
            timestamp: "2025-05-08T11:02:00Z",
            level: "info",
            message: "Generating evaluation harness and test dataset",
          },
          {
            id: "l4l",
            timestamp: "2025-05-08T11:02:15Z",
            level: "info",
            message: "Running syntax validation on generated code",
          },
          {
            id: "l5",
            timestamp: "2025-05-08T11:02:22Z",
            level: "info",
            message: "Validation passed — no syntax errors detected",
          },
          {
            id: "l6",
            timestamp: "2025-05-08T11:02:30Z",
            level: "info",
            message: "Algorithm design completed successfully.",
          },
        ],
        messages: [],
      },
      {
        status: "running",
        versions: [
          {
            id: "v2-1",
            version: 1,
            label: "v1 (running)",
            timestamp: "2025-05-08T12:00:00Z",
            content:
              "### Evolution Progress\n\nGeneration 12/50 | Best fitness: -1523.4 | Avg fitness: -1876.2",
          },
        ],
        activeVersionId: "v2-1",
        logs: [
          {
            id: "l7",
            timestamp: "2025-05-08T12:00:00Z",
            level: "info",
            message: "Initializing evolutionary engine (Island GA)",
          },
          {
            id: "l7b",
            timestamp: "2025-05-08T12:00:05Z",
            level: "info",
            message: "Population size: 20 | Generations: 50 | Islands: 4",
          },
          {
            id: "l7c",
            timestamp: "2025-05-08T12:00:10Z",
            level: "info",
            message: "Generating initial population from seed heuristic",
          },
          {
            id: "l7d",
            timestamp: "2025-05-08T12:00:18Z",
            level: "info",
            message: "Evaluating initial population on 10 TSP instances",
          },
          {
            id: "l7e",
            timestamp: "2025-05-08T12:00:30Z",
            level: "info",
            message: "Initial best fitness: -2100.5 | Avg: -2503.8",
          },
          {
            id: "l8",
            timestamp: "2025-05-08T12:01:00Z",
            level: "info",
            message: "Generation 5: best=-1645.2, avg=-2012.3",
          },
          {
            id: "l8b",
            timestamp: "2025-05-08T12:01:15Z",
            level: "debug",
            message:
              "Island migration triggered (ring topology, top-2 individuals)",
          },
          {
            id: "l8c",
            timestamp: "2025-05-08T12:01:30Z",
            level: "info",
            message: "Generation 7: best=-1598.1, avg=-1965.7",
          },
          {
            id: "l8d",
            timestamp: "2025-05-08T12:01:45Z",
            level: "warn",
            message:
              "Island 3 showing low diversity — injecting random mutants",
          },
          {
            id: "l9",
            timestamp: "2025-05-08T12:02:00Z",
            level: "info",
            message: "Generation 10: best=-1548.7, avg=-1901.5",
          },
          {
            id: "l9b",
            timestamp: "2025-05-08T12:02:20Z",
            level: "info",
            message: "New best individual found via crossover on Island 1",
          },
          {
            id: "l9c",
            timestamp: "2025-05-08T12:02:40Z",
            level: "debug",
            message:
              "LLM mutation applied: modified look-ahead weight from 0.3 to 0.25",
          },
          {
            id: "l10",
            timestamp: "2025-05-08T12:03:00Z",
            level: "info",
            message: "Generation 12: best=-1523.4, avg=-1876.2",
          },
          {
            id: "l10b",
            timestamp: "2025-05-08T12:03:10Z",
            level: "info",
            message: "Evolution in progress — 38 generations remaining...",
          },
        ],
        messages: [],
      },
      {
        status: "pending",
        versions: [],
        activeVersionId: null,
        logs: [],
        messages: [],
      },
    ],
    messages: [
      {
        id: "m1",
        role: "user",
        content:
          "Research the Traveling Salesman Problem (TSP), focusing on heuristic and metaheuristic approaches suitable for LLM-based algorithm design.",
        timestamp: "2025-05-08T10:30:00Z",
        step: 0,
      },
      {
        id: "m2",
        role: "assistant",
        content:
          "I'll research TSP optimization methods with a focus on heuristic approaches. Let me analyze the literature.",
        timestamp: "2025-05-08T10:30:03Z",
        step: 0,
      },
      {
        id: "m2b",
        role: "user",
        content:
          "Make sure to cover both classical approaches and recent neural methods. I want a comprehensive comparison.",
        timestamp: "2025-05-08T10:30:06Z",
        step: 0,
      },
      {
        id: "m2c",
        role: "assistant",
        content:
          "Understood. I'll structure the research into four categories: exact methods, classical heuristics, metaheuristics, and neural combinatorial optimization.",
        timestamp: "2025-05-08T10:30:09Z",
        step: 0,
      },
      {
        id: "m2g",
        role: "assistant",
        content:
          "Based on the literature, I'd recommend building on metaheuristic methods — specifically evolutionary approaches. They naturally support population-based search and the operator design space is rich and learnable.",
        timestamp: "2025-05-08T10:30:21Z",
        step: 0,
      },
      {
        id: "m5",
        role: "user",
        content:
          "Design an adaptive heuristic that combines constructive methods with local search. Use priority-based construction.",
        timestamp: "2025-05-08T11:00:00Z",
        step: 1,
      },
      {
        id: "m6",
        role: "assistant",
        content:
          "I'll design a two-phase algorithm: priority-based construction with look-ahead scoring, followed by 2-opt local search refinement.",
        timestamp: "2025-05-08T11:00:03Z",
        step: 1,
      },
      {
        id: "m6c",
        role: "assistant",
        content:
          "I recommend a 1-step look-ahead with a weighted score. This keeps complexity at O(n²) while still capturing some future cost information.",
        timestamp: "2025-05-08T11:00:15Z",
        step: 1,
      },
      {
        id: "m6g",
        role: "assistant",
        content:
          "Code generated. The implementation handles single city, two cities, and general case with full construction + 2-opt.",
        timestamp: "2025-05-08T11:00:35Z",
        step: 1,
      },
      {
        id: "m7",
        role: "user",
        content: "Start evolution with population size 20, 50 generations.",
        timestamp: "2025-05-08T12:00:00Z",
        step: 2,
      },
      {
        id: "m8",
        role: "assistant",
        content:
          "Evolution started. Using island GA with 20 individuals across 50 generations. Current progress: generation 12/50.",
        timestamp: "2025-05-08T12:00:02Z",
        step: 2,
      },
      {
        id: "m8c",
        role: "assistant",
        content:
          "Islands 1, 2, and 4 maintain good diversity. Island 3 is converging too quickly — I've injected random mutants to restore diversity.",
        timestamp: "2025-05-08T12:01:25Z",
        step: 2,
      },
    ],
    config: {
      provider: "openai",
      model: "gpt-4o",
      evolutionAlgorithm: "IslandGA",
      maxIterations: 50,
      populationSize: 20,
      temperature: 0.7,
    },
  },
]

export const MOCK_GROUPS: SessionGroup[] = [
  {
    id: "group-tsp",
    name: "TSP Research",
    createdAt: "2025-05-01T08:00:00Z",
    isCollapsed: false,
  },
  {
    id: "group-vrp",
    name: "VRP Experiments",
    createdAt: "2025-05-03T10:00:00Z",
    isCollapsed: false,
  },
  {
    id: "group-archive",
    name: "Archive",
    createdAt: "2025-04-20T09:00:00Z",
    isCollapsed: true,
  },
]

export const MOCK_EXTRA_SESSIONS: ResearchSession[] = [
  {
    id: "session-2",
    title: "Bin Packing Optimization",
    groupId: null,
    createdAt: "2025-05-10T09:00:00Z",
    updatedAt: "2025-05-10T11:30:00Z",
    currentStep: 1,
    steps: [
      {
        status: "completed",
        versions: [],
        activeVersionId: null,
        logs: [],
        messages: [],
      },
      {
        status: "running",
        versions: [],
        activeVersionId: null,
        logs: [],
        messages: [],
      },
      {
        status: "pending",
        versions: [],
        activeVersionId: null,
        logs: [],
        messages: [],
      },
      {
        status: "pending",
        versions: [],
        activeVersionId: null,
        logs: [],
        messages: [],
      },
    ],
    messages: [
      {
        id: "s2m1",
        role: "user",
        content: "Research bin packing heuristics for 2D irregular shapes.",
        timestamp: "2025-05-10T09:00:00Z",
        step: 0,
      },
      {
        id: "s2m2",
        role: "assistant",
        content:
          "I'll research 2D irregular bin packing approaches including NFP-based methods and metaheuristics.",
        timestamp: "2025-05-10T09:00:05Z",
        step: 0,
      },
    ],
    config: { ...DEFAULT_CONFIG },
  },
  {
    id: "session-3",
    title: "TSP with Time Windows",
    groupId: "group-tsp",
    createdAt: "2025-05-05T14:00:00Z",
    updatedAt: "2025-05-06T16:00:00Z",
    currentStep: 3,
    steps: [
      {
        status: "completed",
        versions: [],
        activeVersionId: null,
        logs: [],
        messages: [],
      },
      {
        status: "completed",
        versions: [],
        activeVersionId: null,
        logs: [],
        messages: [],
      },
      {
        status: "completed",
        versions: [],
        activeVersionId: null,
        logs: [],
        messages: [],
      },
      {
        status: "running",
        versions: [],
        activeVersionId: null,
        logs: [],
        messages: [],
      },
    ],
    messages: [
      {
        id: "s3m1",
        role: "user",
        content: "Design a heuristic for TSP with time window constraints.",
        timestamp: "2025-05-05T14:00:00Z",
        step: 0,
      },
      {
        id: "s3m2",
        role: "assistant",
        content:
          "I'll research TSPTW approaches combining insertion heuristics with constraint handling.",
        timestamp: "2025-05-05T14:00:05Z",
        step: 0,
      },
    ],
    config: { ...DEFAULT_CONFIG, evolutionAlgorithm: "DyCA" },
  },
  {
    id: "session-4",
    title: "Asymmetric TSP",
    groupId: "group-tsp",
    createdAt: "2025-05-07T10:00:00Z",
    updatedAt: "2025-05-07T12:00:00Z",
    currentStep: 0,
    steps: [
      {
        status: "running",
        versions: [],
        activeVersionId: null,
        logs: [],
        messages: [],
      },
      {
        status: "pending",
        versions: [],
        activeVersionId: null,
        logs: [],
        messages: [],
      },
      {
        status: "pending",
        versions: [],
        activeVersionId: null,
        logs: [],
        messages: [],
      },
      {
        status: "pending",
        versions: [],
        activeVersionId: null,
        logs: [],
        messages: [],
      },
    ],
    messages: [
      {
        id: "s4m1",
        role: "user",
        content:
          "Research asymmetric TSP methods where distances are direction-dependent.",
        timestamp: "2025-05-07T10:00:00Z",
        step: 0,
      },
    ],
    config: { ...DEFAULT_CONFIG },
  },
  {
    id: "session-5",
    title: "CVRP Capacity Planning",
    groupId: "group-vrp",
    createdAt: "2025-05-04T08:30:00Z",
    updatedAt: "2025-05-04T15:00:00Z",
    currentStep: 2,
    steps: [
      {
        status: "completed",
        versions: [],
        activeVersionId: null,
        logs: [],
        messages: [],
      },
      {
        status: "completed",
        versions: [],
        activeVersionId: null,
        logs: [],
        messages: [],
      },
      {
        status: "running",
        versions: [],
        activeVersionId: null,
        logs: [],
        messages: [],
      },
      {
        status: "pending",
        versions: [],
        activeVersionId: null,
        logs: [],
        messages: [],
      },
    ],
    messages: [
      {
        id: "s5m1",
        role: "user",
        content:
          "Design algorithms for capacitated vehicle routing with heterogeneous fleet.",
        timestamp: "2025-05-04T08:30:00Z",
        step: 0,
      },
      {
        id: "s5m2",
        role: "assistant",
        content:
          "I'll research CVRP with heterogeneous fleet constraints, focusing on adaptive large neighborhood search.",
        timestamp: "2025-05-04T08:30:05Z",
        step: 0,
      },
    ],
    config: { ...DEFAULT_CONFIG, evolutionAlgorithm: "MEoH" },
  },
]
