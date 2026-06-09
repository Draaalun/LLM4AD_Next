import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, BookOpen, Hand, Info, Wand2 } from "lucide-react"
import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"

import type { FileTreeNode } from "@/client"
import { Llm4AdTasksService } from "@/client"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

import ManualAnnotationTab from "./ManualAnnotationTab"
import RecommendTab from "./RecommendTab"
import SummaryDialog from "./SummaryDialog"

type TabId = "recommend" | "manual"

function hasAnyNodes(nodes: FileTreeNode[]): boolean {
  return nodes.length > 0
}

function hasFileNodes(nodes: FileTreeNode[]): boolean {
  for (const node of nodes) {
    if (node.type === "file") return true
    if (node.children && hasFileNodes(node.children)) return true
  }
  return false
}

interface EvolveAnnotationStepProps {
  taskId: string
  onBack: () => void
  onNext: () => void
  readOnly?: boolean
}

export default function EvolveAnnotationStep({
  taskId,
  onBack,
  onNext,
  readOnly,
}: EvolveAnnotationStepProps) {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState<TabId>("manual")
  const [summaryOpen, setSummaryOpen] = useState(false)

  const { data: treeData } = useQuery({
    queryKey: ["dataTree", taskId],
    queryFn: () => Llm4AdTasksService.getTaskDataTree({ taskId }),
    select: (res) => (res as { tree: FileTreeNode[] }).tree ?? [],
  })

  const hasData = useMemo(() => !!treeData && hasAnyNodes(treeData), [treeData])
  const hasFiles = useMemo(
    () => !!treeData && hasFileNodes(treeData),
    [treeData],
  )

  const tabs: { id: TabId; label: string; icon: typeof BookOpen }[] = [
    {
      id: "recommend",
      label: t("evolution.evolveAnnotation.tabs.recommend"),
      icon: Wand2,
    },
    {
      id: "manual",
      label: t("evolution.evolveAnnotation.tabs.manual"),
      icon: Hand,
    },
  ]

  return (
    <div className="flex flex-col h-full">
      {/* Tab bar */}
      <div className="shrink-0 px-4 py-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1 shrink-0">
            {tabs.map((tab) => {
              const Icon = tab.icon
              const isActive = activeTab === tab.id
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
                    isActive
                      ? "bg-primary/10 border border-primary/30 text-primary"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/50",
                  )}
                >
                  <Icon className="size-3.5" />
                  {tab.label}
                </button>
              )
            })}
          </div>

          {/* Hint message */}
          <div className="flex-1 min-w-0 mx-2">
            {activeTab === "recommend" ? (
              <div className="flex items-center gap-1.5 text-xs text-amber-600 dark:text-amber-400">
                <AlertTriangle className="size-3.5 shrink-0" />
                <span className="truncate">
                  {t("evolution.evolveAnnotation.hintRecommend")}
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-xs text-blue-600 dark:text-blue-400">
                <Info className="size-3.5 shrink-0" />
                <span className="truncate">
                  {t("evolution.evolveAnnotation.hintManual")}
                </span>
              </div>
            )}
          </div>

          <div className="shrink-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSummaryOpen(true)}
              disabled={!hasFiles}
              title={
                !hasFiles
                  ? t("evolution.evolveAnnotation.dataNotReady")
                  : undefined
              }
            >
              <BookOpen className="size-3.5 mr-1.5" />
              {t("evolution.evolveAnnotation.summaryDialog")}
            </Button>
          </div>
        </div>
      </div>

      {/* Content area */}
      <div className="flex-1 min-h-0">
        {!hasData ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-muted-foreground">
              <BookOpen className="size-10 mx-auto mb-3 opacity-40" />
              <p className="text-sm font-medium">
                {t("evolution.evolveAnnotation.noData")}
              </p>
              <p className="text-xs mt-1 opacity-70">
                {t("evolution.evolveAnnotation.noDataHint")}
              </p>
              <Button
                variant="outline"
                size="sm"
                className="mt-3"
                onClick={onBack}
              >
                {t("evolution.evolveAnnotation.goToDataPrep")}
              </Button>
            </div>
          </div>
        ) : (
          <>
            {activeTab === "recommend" && (
              <RecommendTab taskId={taskId} readOnly={readOnly} />
            )}
            {activeTab === "manual" && (
              <ManualAnnotationTab taskId={taskId} readOnly={readOnly} />
            )}
          </>
        )}
      </div>

      {/* Navigation */}
      <div className="shrink-0 py-2">
        <div className="flex justify-center gap-3">
          <Button variant="outline" onClick={onBack}>
            {t("common.previousStep")}
          </Button>
          <Button onClick={onNext}>{t("common.nextStep")}</Button>
        </div>
      </div>

      {/* Summary Analysis Dialog */}
      <SummaryDialog
        taskId={taskId}
        open={summaryOpen}
        onOpenChange={setSummaryOpen}
        readOnly={readOnly}
      />
    </div>
  )
}
