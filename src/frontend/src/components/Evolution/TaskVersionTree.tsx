import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  Check,
  ChevronDown,
  ChevronRight,
  GitBranch,
  GitCompare,
  Loader2,
  Pencil,
  X,
} from "lucide-react"
import { useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import type {
  PaginatedTaskResponse,
  TaskResponse,
  TaskTreeItem,
  TaskTreeResponse,
} from "@/client"
import { Llm4AdTasksService } from "@/client"
import { getTasksInfiniteQueryKey } from "@/components/Evolution/EvolutionTaskList"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import useCustomToast from "@/hooks/useCustomToast"
import { useEvolution } from "@/hooks/useEvolution"
import { INPUT_LIMITS } from "@/lib/inputLimits"
import { taskKeys } from "@/lib/task-queries"
import VersionCompareDialog from "./VersionCompare/VersionCompareDialog"

// Display mode: "flat" shows all versions in a flat list sorted by create_time,
// "tree" preserves parent-child hierarchy with indentation and expand/collapse.
const VERSION_DISPLAY_MODE: "flat" | "tree" = "flat"

const STATUS_COLORS: Record<string, string> = {
  uninitialized: "#6b7280",
  pending: "#f59e0b",
  running: "#00d4ff",
  completed: "#10b981",
  failed: "#ef4444",
}

function formatTagFallback(createdTime: string): string {
  const d = new Date(createdTime)
  const pad = (n: number) => String(n).padStart(2, "0")
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`
}

interface TreeNode {
  item: TaskTreeItem
  children: TreeNode[]
  depth: number
}

function buildTree(root: TaskTreeItem, children: TaskTreeItem[]): TreeNode {
  const childMap = new Map<string, TaskTreeItem[]>()
  for (const c of children) {
    const pid = c.parent_id ?? root.id
    if (!childMap.has(pid)) childMap.set(pid, [])
    childMap.get(pid)!.push(c)
  }

  function buildNode(item: TaskTreeItem, depth: number): TreeNode {
    const kids = childMap.get(item.id) ?? []
    return {
      item,
      depth,
      children: kids.map((k) => buildNode(k, depth + 1)),
    }
  }

  return buildNode(root, 0)
}

function flattenTree(node: TreeNode): TreeNode[] {
  const result: TreeNode[] = [node]
  for (const child of node.children) {
    result.push(...flattenTree(child))
  }
  return result
}

function getVisibleNodes(node: TreeNode, expandedIds: Set<string>): TreeNode[] {
  const result: TreeNode[] = [node]
  if (expandedIds.has(node.item.id)) {
    for (const child of node.children) {
      result.push(...getVisibleNodes(child, expandedIds))
    }
  }
  return result
}

function getActivePath(node: TreeNode, targetId: string): Set<string> | null {
  if (node.item.id === targetId) return new Set([node.item.id])
  for (const child of node.children) {
    const path = getActivePath(child, targetId)
    if (path) {
      path.add(node.item.id)
      return path
    }
  }
  return null
}

function TagEditor({ item, rootId }: { item: TaskTreeItem; rootId: string }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(item.tag ?? "")
  const inputRef = useRef<HTMLInputElement>(null)

  const mutation = useMutation({
    mutationFn: (tag: string) =>
      Llm4AdTasksService.updateTaskTag({
        taskId: item.id,
        requestBody: { tag: tag || null },
      }),
    onSuccess: () => {
      showSuccessToast(t("evolution.versionTree.tagUpdateSuccess"))
      queryClient.invalidateQueries({ queryKey: taskKeys.tree(rootId) })
      setEditing(false)
    },
  })

  const handleSave = () => {
    mutation.mutate(value.trim())
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSave()
    if (e.key === "Escape") setEditing(false)
  }

  if (editing) {
    return (
      <div
        className="flex items-center gap-1"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          ref={inputRef}
          value={value}
          maxLength={INPUT_LIMITS.name}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t("evolution.versionTree.tagPlaceholder")}
          className="w-full h-5 px-1 text-[11px] bg-background border border-border/60 rounded
            text-foreground outline-none focus:border-primary/50"
        />
        {mutation.isPending ? (
          <Loader2 className="size-3 animate-spin text-muted-foreground shrink-0" />
        ) : (
          <>
            <button
              type="button"
              onClick={handleSave}
              className="p-0.5 rounded hover:bg-primary/20 text-primary shrink-0"
            >
              <Check className="size-3" />
            </button>
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="p-0.5 rounded hover:bg-muted text-muted-foreground shrink-0"
            >
              <X className="size-3" />
            </button>
          </>
        )}
      </div>
    )
  }

  const displayText = item.tag || formatTagFallback(item.created_time)

  return (
    <div className="flex items-center gap-1 min-w-0 flex-1">
      <span className="text-[11px] truncate">{displayText}</span>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation()
          setValue(item.tag ?? "")
          setEditing(true)
        }}
        className="p-0.5 rounded opacity-0 group-hover/item:opacity-100
          hover:bg-muted text-muted-foreground hover:text-primary transition-opacity shrink-0"
        title={t("evolution.versionTree.editTag")}
      >
        <Pencil className="size-2.5" />
      </button>
    </div>
  )
}

export default function TaskVersionTree() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const {
    selectedTask,
    setSelectedTask,
    setSelectedChildTaskId,
    effectiveTaskId,
  } = useEvolution()
  const [open, setOpen] = useState(false)
  const [compareOpen, setCompareOpen] = useState(false)
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  const rootId = selectedTask?.group_id || selectedTask?.id || ""

  const treeQuery = useQuery({
    queryKey: taskKeys.tree(rootId),
    queryFn: () => Llm4AdTasksService.getTaskTree({ taskId: rootId }),
    enabled: !!rootId,
  })

  const tree = useMemo(() => {
    if (!treeQuery.data) return null
    return buildTree(treeQuery.data.root, treeQuery.data.children)
  }, [treeQuery.data])

  const allNodes = useMemo(() => {
    if (!tree) return []
    return flattenTree(tree)
  }, [tree])

  const versionMap = useMemo(() => {
    const sorted = [...allNodes].sort(
      (a, b) =>
        new Date(a.item.created_time).getTime() -
        new Date(b.item.created_time).getTime(),
    )
    const map = new Map<string, number>()
    sorted.forEach((n, i) => map.set(n.item.id, i))
    return map
  }, [allNodes])

  const latestId = useMemo(() => {
    if (allNodes.length === 0) return null
    return [...allNodes].sort(
      (a, b) =>
        new Date(b.item.created_time).getTime() -
        new Date(a.item.created_time).getTime(),
    )[0].item.id
  }, [allNodes])

  const visibleNodes = useMemo(() => {
    if (!tree) return []
    if (VERSION_DISPLAY_MODE === "flat") {
      return [...allNodes].sort(
        (a, b) =>
          new Date(a.item.created_time).getTime() -
          new Date(b.item.created_time).getTime(),
      )
    }
    return getVisibleNodes(tree, expandedIds)
  }, [tree, allNodes, expandedIds])

  const currentDisplay = useMemo(() => {
    const activeId = effectiveTaskId
    const node = allNodes.find((n) => n.item.id === activeId)
    const ver = activeId ? versionMap.get(activeId) : undefined
    const prefix = ver !== undefined ? `v${ver} ` : ""
    if (node)
      return (
        prefix + (node.item.tag || formatTagFallback(node.item.created_time))
      )
    if (selectedTask)
      return selectedTask.tag || formatTagFallback(selectedTask.created_time)
    return ""
  }, [allNodes, versionMap, effectiveTaskId, selectedTask])

  const currentIndex = effectiveTaskId
    ? (versionMap.get(effectiveTaskId) ?? -1)
    : -1

  const handleOpenChange = (isOpen: boolean) => {
    setOpen(isOpen)
    if (isOpen && tree && VERSION_DISPLAY_MODE === "tree") {
      const path =
        getActivePath(tree, effectiveTaskId ?? "") ?? new Set([tree.item.id])
      setExpandedIds(path)
    }
  }

  const toggleExpanded = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleSelect = (node: TreeNode) => {
    if (node.item.id === effectiveTaskId) {
      setOpen(false)
      return
    }
    const childId = node.depth === 0 ? null : node.item.id
    const nextActiveStatus = node.item.status
    setSelectedChildTaskId(childId)
    setOpen(false)

    if (!rootId) return

    // Optimistically reflect the new active version in caches & local state
    // so the left task list status (active_status) updates without re-fetching.
    if (selectedTask && selectedTask.id === rootId) {
      setSelectedTask({
        ...selectedTask,
        active_child_id: childId,
        active_status: nextActiveStatus,
      })
    }

    const projectId = selectedTask?.project_id
    if (projectId) {
      queryClient.setQueryData<{
        pages: PaginatedTaskResponse[]
        pageParams: unknown[]
      }>(getTasksInfiniteQueryKey(projectId), (data) => {
        if (!data) return data
        return {
          ...data,
          pages: data.pages.map((page) => ({
            ...page,
            items: page.items.map((item: TaskResponse) =>
              item.id === rootId
                ? {
                    ...item,
                    active_child_id: childId,
                    active_status: nextActiveStatus,
                  }
                : item,
            ),
          })),
        }
      })
    }

    queryClient.setQueryData<TaskTreeResponse>(taskKeys.tree(rootId), (data) =>
      data
        ? { ...data, root: { ...data.root, active_child_id: childId } }
        : data,
    )

    Llm4AdTasksService.setActiveChild({
      taskId: rootId,
      requestBody: { child_id: childId },
    }).catch(() => {})
  }

  if (!selectedTask) return null

  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
          {t(
            VERSION_DISPLAY_MODE === "flat"
              ? "evolution.versionTree.titleFlat"
              : "evolution.versionTree.title",
          )}
        </span>
        {allNodes.length >= 2 && (
          <button
            type="button"
            onClick={() => setCompareOpen(true)}
            className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-primary
              transition-colors"
          >
            <GitCompare className="size-3" />
            <span>{t("evolution.versionCompare.title")}</span>
          </button>
        )}
      </div>
      <Popover open={open} onOpenChange={handleOpenChange}>
        <PopoverTrigger asChild>
          <button
            type="button"
            className="flex items-center gap-1.5 w-full px-2 py-1.5 rounded
              bg-muted/60 border border-border/40 text-xs
              hover:border-primary/30 hover:bg-accent/60 transition-all"
          >
            <GitBranch className="size-3 text-primary shrink-0" />
            <span className="truncate flex-1 text-left text-foreground/80">
              {currentDisplay}
            </span>
            {allNodes.length > 1 && (
              <span className="text-[10px] text-muted-foreground/60 shrink-0">
                {currentIndex + 1}/{allNodes.length}
              </span>
            )}
            <ChevronDown className="size-3 text-muted-foreground shrink-0" />
          </button>
        </PopoverTrigger>
        <PopoverContent
          align="start"
          className="w-64 p-0 max-h-80 overflow-hidden"
        >
          {treeQuery.isLoading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="size-4 animate-spin text-muted-foreground" />
            </div>
          ) : allNodes.length <= 1 ? (
            <div className="px-3 py-4 text-center">
              <p className="text-xs text-muted-foreground">
                {t("evolution.versionTree.noVersions")}
              </p>
            </div>
          ) : (
            <div className="overflow-y-auto max-h-72 py-1">
              {visibleNodes.map((node) => {
                const isActive = node.item.id === effectiveTaskId
                const isRoot = node.depth === 0
                const statusColor = STATUS_COLORS[node.item.status] ?? "#6b7280"
                const hasChildren = node.children.length > 0
                const isExpanded = expandedIds.has(node.item.id)
                const isFlat = VERSION_DISPLAY_MODE === "flat"
                const cappedDepth = isFlat ? 0 : Math.min(node.depth, 6)
                const version = versionMap.get(node.item.id) ?? 0
                const isLatest = node.item.id === latestId

                return (
                  <div
                    key={node.item.id}
                    className={`group/item flex items-center gap-1.5 pr-3 py-1.5 cursor-pointer
                      transition-colors text-left w-full
                      ${isActive ? "bg-primary/10 border-l-2 border-l-primary" : "border-l-2 border-l-transparent hover:bg-accent/60"}`}
                    style={{ paddingLeft: `${8 + cappedDepth * 16}px` }}
                    title={`${t("evolution.versionTree.lastEditedAt")}: ${new Date(node.item.updated_time).toLocaleString()}`}
                    onClick={() => handleSelect(node)}
                  >
                    {!isFlat &&
                      (hasChildren ? (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            toggleExpanded(node.item.id)
                          }}
                          className="flex items-center justify-center size-3.5 shrink-0
                            text-muted-foreground hover:text-primary transition-colors"
                        >
                          {isExpanded ? (
                            <ChevronDown className="size-3" />
                          ) : (
                            <ChevronRight className="size-3" />
                          )}
                        </button>
                      ) : (
                        <span className="w-3.5 shrink-0" />
                      ))}
                    <span
                      className="size-1.5 rounded-full shrink-0"
                      style={{ backgroundColor: statusColor }}
                    />
                    <span className="text-[9px] font-mono text-muted-foreground/60 shrink-0">
                      v{version}
                    </span>
                    <TagEditor item={node.item} rootId={rootId} />
                    {isLatest && allNodes.length > 1 && (
                      <span
                        className="text-[9px] px-1 py-0.5 rounded border border-emerald-400/40
                        text-emerald-400 bg-emerald-400/10 shrink-0"
                      >
                        {t("evolution.versionTree.latestLabel")}
                      </span>
                    )}
                    {isRoot && (
                      <span
                        className="text-[9px] px-1 py-0.5 rounded border border-border/40
                        text-muted-foreground/60 bg-muted/40 shrink-0"
                      >
                        {t("evolution.versionTree.rootLabel")}
                      </span>
                    )}
                    {isActive && (
                      <span
                        className="text-[9px] px-1 py-0.5 rounded border border-primary/40
                        text-primary bg-primary/10 shrink-0"
                      >
                        {t("evolution.versionTree.currentLabel")}
                      </span>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </PopoverContent>
      </Popover>
      {rootId && (
        <VersionCompareDialog
          rootId={rootId}
          open={compareOpen}
          onOpenChange={setCompareOpen}
        />
      )}
    </div>
  )
}
