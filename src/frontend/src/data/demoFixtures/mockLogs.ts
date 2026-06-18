import type { LogEntry } from "@/hooks/useTaskLogs"

/**
 * Mock log entries surfaced through the demo's `LogsPanel`.
 *
 * Shape mirrors what the real backend streams via SSE — log-renderers.tsx
 * reads `level / message / timestamp / module / function / line` directly off
 * each entry, so feeding fixtures with the same fields makes the demo logs
 * look pixel-identical to a real run.
 *
 * Story arc: load dataset → init islands → step through generations → done.
 *
 * Wired via the demo short-circuit inside `useTaskLogs` — the hook returns a
 * slice of this array based on the current demo phase, so the panel "fills
 * up" as the user advances the walkthrough.
 */
export const DEMO_LOG_ENTRIES: LogEntry[] = [
  {
    _kind: "log",
    type: "log",
    timestamp: "2026-06-17T11:18:09.035000+00:00",
    level: "DEBUG",
    message: "Global settings file not found at /root/.llm4ad/settings.yaml",
    module: "llm4ad.config.settings",
    function: "load_global_settings",
    line: 98,
  },
  {
    _kind: "log",
    type: "log",
    timestamp: "2026-06-17T11:18:09.214000+00:00",
    level: "INFO",
    message: "Loading dataset: tsp_50.json (50 cities, Euclidean distance)",
    module: "llm4ad.evaluator.dataset",
    function: "load_dataset",
    line: 142,
  },
  {
    _kind: "log",
    type: "log",
    timestamp: "2026-06-17T11:18:09.531000+00:00",
    level: "INFO",
    message: "Initializing 2 islands with population 8 each",
    module: "llm4ad.evolution.islands",
    function: "initialize",
    line: 67,
  },
  {
    _kind: "log",
    type: "log",
    timestamp: "2026-06-17T11:18:10.812000+00:00",
    level: "INFO",
    message:
      "Generation 1: best score 0.31, mean score 0.18 (16 candidates evaluated)",
    module: "llm4ad.evolution.runner",
    function: "step_generation",
    line: 215,
  },
  {
    _kind: "log",
    type: "log",
    timestamp: "2026-06-17T11:18:14.226000+00:00",
    level: "INFO",
    message:
      "Generation 4: best score 0.58 (+0.27 over baseline) — 2-opt swap accepted",
    module: "llm4ad.evolution.runner",
    function: "step_generation",
    line: 215,
  },
  {
    _kind: "log",
    type: "log",
    timestamp: "2026-06-17T11:18:18.094000+00:00",
    level: "DEBUG",
    message: "Cross-island migration: best individual A-7 → island B",
    module: "llm4ad.evolution.islands",
    function: "migrate",
    line: 188,
  },
  {
    _kind: "log",
    type: "log",
    timestamp: "2026-06-17T11:18:21.473000+00:00",
    level: "INFO",
    message: "Generation 8: best score 0.81, convergence detected on island A",
    module: "llm4ad.evolution.runner",
    function: "step_generation",
    line: 215,
  },
  {
    _kind: "log",
    type: "log",
    timestamp: "2026-06-17T11:18:25.117000+00:00",
    level: "INFO",
    message: "Generation 12: best score 0.93 — convergence reached",
    module: "llm4ad.evolution.runner",
    function: "step_generation",
    line: 215,
  },
  {
    _kind: "log",
    type: "log",
    timestamp: "2026-06-17T11:18:25.341000+00:00",
    level: "INFO",
    message: "Run finished. Best individual: gen12_A (score 0.93)",
    module: "llm4ad.evolution.runner",
    function: "finalize",
    line: 312,
  },
  {
    _kind: "log",
    type: "log",
    timestamp: "2026-06-17T11:18:25.404000+00:00",
    level: "INFO",
    message: "Total wall time: 00:01:24, total candidates evaluated: 192",
    module: "llm4ad.evolution.runner",
    function: "finalize",
    line: 318,
  },
]

/**
 * How many entries to expose for a given demo phase. Drives the "logs fill
 * up as the run progresses" effect inside `useTaskLogs`.
 */
export function visibleLogCount(phase: string): number {
  switch (phase) {
    case "completed":
      return DEMO_LOG_ENTRIES.length
    case "running":
      // Show everything up to and including the "Generation 12 done" line so
      // the user perceives the animation as following the live progress.
      return Math.min(DEMO_LOG_ENTRIES.length, 8)
    case "building":
      return 3
    case "configuring":
      return 1
    default:
      return 0
  }
}
