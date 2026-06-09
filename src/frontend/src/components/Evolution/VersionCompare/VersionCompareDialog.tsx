import { useQuery } from "@tanstack/react-query"
import { Loader2 } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { Group, Panel, Separator } from "react-resizable-panels"
import type { TaskTreeItem } from "@/client"
import { Llm4AdTasksService } from "@/client"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import useCustomToast from "@/hooks/useCustomToast"
import { useEvolution } from "@/hooks/useEvolution"
import { taskKeys } from "@/lib/task-queries"
import { cn } from "@/lib/utils"
import ParamsDiff from "./ParamsDiff"
import ScoreCompare from "./ScoreCompare"
import VersionTreeD3 from "./VersionTreeD3"

type CompareTab = "params" | "score"

const MAX_SELECTED = 6

interface VersionCompareDialogProps {
  rootId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function VersionCompareDialog({
  rootId,
  open,
  onOpenChange,
}: VersionCompareDialogProps) {
  const { t } = useTranslation()
  const { effectiveTaskId } = useEvolution()
  const { showErrorToast } = useCustomToast()

  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [tab, setTab] = useState<CompareTab>("params")

  const treeQuery = useQuery({
    queryKey: taskKeys.tree(rootId),
    queryFn: () => Llm4AdTasksService.getTaskTree({ taskId: rootId }),
    enabled: !!rootId && open,
  })

  const allItems = useMemo<TaskTreeItem[]>(() => {
    if (!treeQuery.data) return []
    return [treeQuery.data.root, ...treeQuery.data.children]
  }, [treeQuery.data])

  const versionMap = useMemo(() => {
    const sorted = [...allItems].sort(
      (a, b) =>
        new Date(a.created_time).getTime() - new Date(b.created_time).getTime(),
    )
    const map = new Map<string, number>()
    sorted.forEach((it, i) => {
      map.set(it.id, i)
    })
    return map
  }, [allItems])

  const latestId = useMemo(() => {
    if (allItems.length === 0) return null
    return [...allItems].sort(
      (a, b) =>
        new Date(b.created_time).getTime() - new Date(a.created_time).getTime(),
    )[0].id
  }, [allItems])

  const lastModifiedId = useMemo(() => {
    if (allItems.length === 0) return null
    return [...allItems].sort(
      (a, b) =>
        new Date(b.updated_time).getTime() - new Date(a.updated_time).getTime(),
    )[0].id
  }, [allItems])

  // When dialog opens or data first loads, seed selection with current task.
  useEffect(() => {
    if (!open) return
    if (allItems.length === 0) return
    setSelectedIds((prev) => {
      const valid = prev.filter((id) => allItems.some((i) => i.id === id))
      if (valid.length > 0) return valid
      const seed = effectiveTaskId
        ? allItems.find((i) => i.id === effectiveTaskId)
        : null
      return seed ? [seed.id] : [allItems[0].id]
    })
  }, [open, allItems, effectiveTaskId])

  const handleSelect = (id: string, isMulti: boolean) => {
    setSelectedIds((prev) => {
      if (!isMulti) {
        return [id]
      }
      if (prev.includes(id)) {
        if (prev.length === 1) return prev
        return prev.filter((x) => x !== id)
      }
      if (prev.length >= MAX_SELECTED) {
        showErrorToast(t("evolution.versionCompare.maxSelected"))
        return prev
      }
      return [...prev, id]
    })
  }

  const selectedItems = useMemo(
    () => allItems.filter((it) => selectedIds.includes(it.id)),
    [allItems, selectedIds],
  )

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className={cn(
          "!max-w-none w-screen h-screen rounded-none p-0 gap-0 border-0",
          "top-0 left-0 translate-x-0 translate-y-0",
          "flex flex-col",
        )}
        onPointerDownOutside={(e) => {
          const target = e.target as HTMLElement | null
          if (target?.closest("[data-separator]")) {
            e.preventDefault()
          }
        }}
        onInteractOutside={(e) => {
          const target = e.target as HTMLElement | null
          if (target?.closest("[data-separator]")) {
            e.preventDefault()
          }
        }}
      >
        <div className="flex items-center gap-3 px-4 py-2.5 border-b border-border/40 shrink-0">
          <DialogTitle className="text-base font-semibold">
            {t("evolution.versionCompare.title")}
          </DialogTitle>
          <span className="text-xs text-muted-foreground">
            {t("evolution.versionCompare.selectedCount", {
              count: selectedIds.length,
            })}
          </span>
        </div>

        {treeQuery.isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="size-5 animate-spin text-muted-foreground" />
          </div>
        ) : !treeQuery.data || allItems.length === 0 ? (
          <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
            {t("evolution.versionTree.noVersions")}
          </div>
        ) : (
          <div className="flex-1 min-h-0">
            <Group orientation="vertical" className="w-full h-full">
              <Panel defaultSize="42%" minSize="20%">
                <div className="w-full h-full p-3">
                  <VersionTreeD3
                    root={treeQuery.data.root}
                    branches={treeQuery.data.children}
                    selectedIds={selectedIds}
                    currentId={effectiveTaskId}
                    latestId={latestId}
                    lastModifiedId={lastModifiedId}
                    versionMap={versionMap}
                    onSelect={handleSelect}
                  />
                </div>
              </Panel>
              <Separator className="h-1.5 bg-background hover:bg-primary/10 data-[separator=active]:bg-primary/15">
                <div className="h-px w-12 mx-auto bg-border" />
              </Separator>
              <Panel defaultSize="58%" minSize="25%">
                <div className="w-full h-full flex flex-col p-3 gap-2">
                  <div className="inline-flex rounded border border-border/60 overflow-hidden self-start text-xs">
                    <button
                      type="button"
                      onClick={() => setTab("params")}
                      className={cn(
                        "px-3 py-1 transition-colors",
                        tab === "params"
                          ? "bg-primary/15 text-primary"
                          : "hover:bg-accent/60 text-muted-foreground",
                      )}
                    >
                      {t("evolution.versionCompare.tabParams")}
                    </button>
                    <button
                      type="button"
                      onClick={() => setTab("score")}
                      className={cn(
                        "px-3 py-1 transition-colors border-l border-border/60",
                        tab === "score"
                          ? "bg-primary/15 text-primary"
                          : "hover:bg-accent/60 text-muted-foreground",
                      )}
                    >
                      {t("evolution.versionCompare.tabScore")}
                    </button>
                  </div>
                  <div className="flex-1 min-h-0">
                    {tab === "params" ? (
                      <ParamsDiff
                        selectedItems={selectedItems}
                        versionMap={versionMap}
                      />
                    ) : (
                      <ScoreCompare
                        selectedItems={selectedItems}
                        versionMap={versionMap}
                      />
                    )}
                  </div>
                </div>
              </Panel>
            </Group>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
