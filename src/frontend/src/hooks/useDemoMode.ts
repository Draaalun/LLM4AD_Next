import { useSyncExternalStore } from "react"

/**
 * Phases the simulated demo task walks through as the user advances the tour.
 * Each phase decides what fixture data is exposed by the demo-aware hooks.
 */
export type DemoPhase =
  | "uninitialized" // task created, configuration not started
  | "configuring" // user is filling in config / AI Build
  | "building" // AI Build working
  | "running" // evolution producing nodes
  | "completed" // results available

interface DemoState {
  /** Whether the user is currently inside the demo (read-only) project. */
  active: boolean
  /** How far the simulated task has progressed. */
  phase: DemoPhase
  /** Generation index to expose for evolution data (0..MAX). */
  generation: number
}

const STORAGE_KEY = "llm4ad:demoState"
const PHASE_ORDER: DemoPhase[] = [
  "uninitialized",
  "configuring",
  "building",
  "running",
  "completed",
]

const DEFAULT_STATE: DemoState = {
  active: false,
  phase: "uninitialized",
  generation: 0,
}

let state: DemoState = loadState()
const listeners = new Set<() => void>()

function loadState(): DemoState {
  if (typeof window === "undefined") return DEFAULT_STATE
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULT_STATE
    const parsed = JSON.parse(raw) as Partial<DemoState>
    return {
      active: !!parsed.active,
      phase: (parsed.phase as DemoPhase) ?? "uninitialized",
      generation: typeof parsed.generation === "number" ? parsed.generation : 0,
    }
  } catch {
    return DEFAULT_STATE
  }
}

function persist(): void {
  if (typeof window === "undefined") return
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // ignore storage failures (private mode, quota)
  }
}

function emit(): void {
  persist()
  listeners.forEach((l) => {
    l()
  })
}

function subscribe(l: () => void): () => void {
  listeners.add(l)
  return () => listeners.delete(l)
}

function getSnapshot(): DemoState {
  return state
}

export function enterDemo(phase: DemoPhase = "uninitialized"): void {
  state = { active: true, phase, generation: phaseToGeneration(phase) }
  emit()
}

export function exitDemo(): void {
  state = { ...DEFAULT_STATE }
  emit()
}

export function setDemoPhase(phase: DemoPhase): void {
  if (!state.active) return
  state = {
    ...state,
    phase,
    generation: phaseToGeneration(phase),
  }
  emit()
}

/**
 * Override the visible generation count without changing the phase. Used by
 * the running-phase animation to push nodes onto the canvas one generation
 * at a time. No-op when demo mode is inactive or the phase is anything other
 * than `running` (other phases derive their generation from `phaseToGeneration`).
 */
export function setDemoGeneration(generation: number): void {
  if (!state.active) return
  if (state.phase !== "running") return
  state = {
    ...state,
    generation: Math.max(0, generation),
  }
  emit()
}

export function advanceDemoPhase(): void {
  if (!state.active) return
  const idx = PHASE_ORDER.indexOf(state.phase)
  if (idx < 0 || idx >= PHASE_ORDER.length - 1) return
  setDemoPhase(PHASE_ORDER[idx + 1])
}

/** Number of generations to expose for a given phase. */
function phaseToGeneration(phase: DemoPhase): number {
  switch (phase) {
    case "running":
      return 0
    case "completed":
      return 12
    default:
      return 0
  }
}

/** React hook: subscribe to the current demo state. */
export function useDemoState(): DemoState {
  return useSyncExternalStore(subscribe, getSnapshot, () => DEFAULT_STATE)
}

/** Snapshot accessor for non-component code (services, utilities). */
export function getDemoState(): DemoState {
  return state
}
