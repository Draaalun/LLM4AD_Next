import type { QueryClient } from "@tanstack/react-query"

export const taskKeys = {
  allTasks: ["listTasks"] as const,
  tasks: (projectId: string) => ["listTasks", projectId] as const,
  detail: (taskId: string) => ["getTask", taskId] as const,
  logs: (taskId: string) => ["taskLogs", taskId] as const,
  logsList: (
    taskId: string,
    logType: string,
    searchQuery: string,
    levels: string[],
  ) =>
    [
      "taskLogs",
      taskId,
      "list",
      logType,
      searchQuery,
      [...levels].sort().join(","),
    ] as const,
  report: (taskId: string, reportType: string) =>
    ["report", taskId, reportType] as const,
  tree: (taskId: string) => ["taskTree", taskId] as const,
  stats: (taskId: string) => ["taskStats", taskId] as const,
}

export function resetTaskCaches(
  queryClient: QueryClient,
  taskId: string,
  projectId?: string,
) {
  queryClient.removeQueries({ queryKey: taskKeys.logs(taskId) })
  queryClient.invalidateQueries({ queryKey: taskKeys.detail(taskId) })
  queryClient.invalidateQueries({ queryKey: taskKeys.allTasks })
  if (projectId) {
    queryClient.invalidateQueries({ queryKey: taskKeys.tasks(projectId) })
  }
}
