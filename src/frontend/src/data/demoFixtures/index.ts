import type { ProjectResponse, TaskResponse, TaskStatus } from "@/client"
import type {
  GANode,
  IslandGAData,
} from "@/components/Evolution/TaskDetail/island-ga-mock-data"
import type { DemoPhase } from "@/hooks/useDemoMode"
import { DEMO_PROJECT_ID, DEMO_TASK_ID } from "./constants"

export {
  DEMO_PROJECT_ID,
  DEMO_TASK_ID,
  isDemoProjectId,
  isDemoTaskId,
} from "./constants"

const NOW = "2026-06-01T00:00:00Z"

export const DEMO_PROJECT: ProjectResponse = {
  id: DEMO_PROJECT_ID,
  created_time: NOW,
  updated_time: NOW,
  name: "✨ Demo · TSP Heuristic",
  description:
    "Read-only example project. Walk through it to see how LLM4AD designs an algorithm end-to-end.",
  icon: "nexus",
  user_id: "__demo__",
}

export const DEMO_TASK: TaskResponse = {
  id: DEMO_TASK_ID,
  created_time: NOW,
  updated_time: NOW,
  project_id: DEMO_PROJECT_ID,
  name: "Demo · Greedy + Local Search",
  description: "Auto-designed heuristic for the Travelling Salesman Problem.",
  status: "completed",
  active_status: "completed",
  input_args: {
    task_name: "tsp_construct",
    population_size: 8,
    max_generations: 12,
  },
  ai_built: true,
  ai_build_started: true,
  children_count: 0,
}

/**
 * Map a demo phase to the task `status` field. The view picker in
 * `_layout_evolution` reads `effectiveStatus` and chooses
 * UninitializedView / ChatTuneView / InitializedView based on it, so swapping
 * the status as the user advances drives the live view transitions for free.
 */
export function demoPhaseToStatus(phase: DemoPhase): TaskStatus {
  switch (phase) {
    case "uninitialized":
    case "configuring":
      return "uninitialized"
    case "building":
    case "running":
      return "running"
    case "completed":
      return "completed"
  }
}

/** Build a demo task whose status reflects the current demo phase. */
export function buildDemoTask(phase: DemoPhase): TaskResponse {
  const status = demoPhaseToStatus(phase)
  return {
    ...DEMO_TASK,
    status,
    active_status: status,
    // ai_built only flips on once the simulated AI Build finishes — before that
    // the AI panel is the active surface; after it, the task moves into the
    // initialized result views.
    ai_built: phase === "running" || phase === "completed",
    ai_build_started: phase !== "uninitialized",
  }
}

/**
 * Pre-baked evolution graph for the demo task. Nodes are spread across two
 * islands and 12 generations; scores monotonically improve so the trajectory
 * looks like a successful run.
 */
function buildDemoNodes(): GANode[] {
  const nodes: GANode[] = []
  const islands = ["A", "B"]
  const prevByIsland: Record<string, string | null> = { A: null, B: null }
  // Deterministic pseudo-random for reproducible demo geometry.
  let seed = 42
  const rand = () => {
    seed = (seed * 1103515245 + 12345) & 0x7fffffff
    return seed / 0x7fffffff
  }

  for (let gen = 0; gen <= 12; gen++) {
    for (const island of islands) {
      const id = `demo-${island}-${gen}`
      const baseRaw = 100 - gen * 5
      const raw = baseRaw + rand() * 4 - 2
      const parents: string[] = []
      const prev = prevByIsland[island]
      if (prev) parents.push(prev)
      // Cross-island parent every 3 generations to make the graph interesting.
      if (gen > 1 && gen % 3 === 0) {
        const otherIsland = island === "A" ? "B" : "A"
        const otherPrev = prevByIsland[otherIsland]
        if (otherPrev) parents.push(otherPrev)
      }
      nodes.push({
        id,
        generation: gen,
        island: island === "A" ? 0 : 1,
        islandId: island,
        name: `gen${gen}_${island}`,
        fileName: `gen_${gen}_${island}.py`,
        score: 0, // filled in by the caller's normalize step
        rawScore: raw,
        parentIds: parents,
      })
      prevByIsland[island] = id
    }
  }
  // Min-max normalize so the renderer has a [0,1] score column.
  const min = Math.min(...nodes.map((n) => n.rawScore))
  const max = Math.max(...nodes.map((n) => n.rawScore))
  const range = max - min
  for (const n of nodes) {
    n.score = range > 0 ? (n.rawScore - min) / range : 0.5
  }
  return nodes
}

const ALL_NODES = buildDemoNodes()

/** Slice nodes up to the given generation (inclusive). */
export function buildDemoEvolutionData(maxGen: number): IslandGAData {
  const nodes = ALL_NODES.filter((n) => n.generation <= maxGen)
  const islandIds = ["A", "B"]
  return {
    nodes,
    unscoredNodes: [],
    maxGeneration: nodes.length
      ? Math.max(...nodes.map((n) => n.generation))
      : 0,
    islandCount: islandIds.length,
    islandIds,
  }
}

export const DEMO_BEST_CODE = `def solve(distance_matrix):
    """Greedy nearest-neighbor with 2-opt local search.

    Auto-designed by LLM4AD. Score: 0.93 (normalized).
    """
    n = len(distance_matrix)
    visited = [False] * n
    tour = [0]
    visited[0] = True
    for _ in range(n - 1):
        current = tour[-1]
        best, best_d = -1, float("inf")
        for j in range(n):
            if not visited[j] and distance_matrix[current][j] < best_d:
                best, best_d = j, distance_matrix[current][j]
        tour.append(best)
        visited[best] = True
    # 2-opt refinement
    improved = True
    while improved:
        improved = False
        for i in range(1, n - 2):
            for k in range(i + 1, n):
                a, b = tour[i - 1], tour[i]
                c, d = tour[k], tour[(k + 1) % n]
                if (
                    distance_matrix[a][c] + distance_matrix[b][d]
                    < distance_matrix[a][b] + distance_matrix[c][d]
                ):
                    tour[i : k + 1] = tour[i : k + 1][::-1]
                    improved = True
    return tour
`

export const DEMO_LOG_LINES: string[] = [
  "[demo] Loading dataset: tsp_50.json",
  "[demo] Initializing 2 islands with population 8",
  "[demo] Generation 1: best score 0.31",
  "[demo] Generation 4: best score 0.58",
  "[demo] Generation 8: best score 0.81",
  "[demo] Generation 12: best score 0.93 ← convergence",
  "[demo] Run finished in 00:01:24",
]

export const DEMO_AI_BUILD_FILES = [
  { name: "config.yaml", language: "yaml" },
  { name: "evaluator.py", language: "python" },
  { name: "task.py", language: "python" },
]
