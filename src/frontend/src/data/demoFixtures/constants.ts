// Sentinel ids for the read-only demo project. Hooks/services check these
// before issuing real network calls.
export const DEMO_PROJECT_ID = "__demo_project__"
export const DEMO_TASK_ID = "__demo_task__"

export function isDemoProjectId(id: string | null | undefined): boolean {
  return id === DEMO_PROJECT_ID
}

export function isDemoTaskId(id: string | null | undefined): boolean {
  return id === DEMO_TASK_ID
}
