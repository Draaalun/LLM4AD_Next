import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"
import { format } from "date-fns"
import { Eye, MessageSquarePlus, Pencil, RotateCcw, Trash2 } from "lucide-react"
import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { FeedbackService } from "@/client/sdk.gen"
import type {
  FeedbackAdmin,
  FeedbackPriority,
  FeedbackPublic,
  FeedbackStatus,
  FeedbackType,
} from "@/client/types.gen"
import { DataTable } from "@/components/Common/DataTable"
import { PageNumbers } from "@/components/Common/PageNumbers"
import { FeedbackDetailDialog } from "@/components/Feedback/FeedbackDetailDialog"
import { FeedbackEditDialog } from "@/components/Feedback/FeedbackEditDialog"
import { FeedbackStatistics } from "@/components/Feedback/FeedbackStatistics"
import { FeedbackSubmitDialog } from "@/components/Feedback/FeedbackSubmitDialog"
import {
  PRIORITY_STYLES,
  STATUS_STYLES,
  TYPE_STYLES,
} from "@/components/Feedback/feedbackStyles"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/feedback")({
  component: FeedbackPage,
  head: () => ({
    meta: [{ title: "Feedback - LLM4AD" }],
  }),
})

const ALL = "__all__"
const DEFAULT_PAGE_SIZE = 10

const hasActiveFilter = (type: string, status: string, priority: string) =>
  type !== ALL || status !== ALL || priority !== ALL

function TruncatedCell({
  text,
  maxLen = 30,
}: {
  text: string | null
  maxLen?: number
}) {
  if (!text) return <span className="text-muted-foreground">-</span>
  if (text.length <= maxLen) return <span>{text}</span>
  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="cursor-default">{text.slice(0, maxLen)}...</span>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-sm whitespace-pre-wrap">
          {text}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

function FeedbackPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const isAdmin = !!user?.is_superuser

  const [filterType, setFilterType] = useState<string>(ALL)
  const [filterStatus, setFilterStatus] = useState<string>(ALL)
  const [filterPriority, setFilterPriority] = useState<string>(ALL)
  const [page, setPage] = useState(0)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)

  const [detailOpen, setDetailOpen] = useState(false)
  const [detailItem, setDetailItem] = useState<FeedbackAdmin | null>(null)
  const [editOpen, setEditOpen] = useState(false)
  const [editItem, setEditItem] = useState<FeedbackAdmin | null>(null)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleteItem, setDeleteItem] = useState<FeedbackPublic | null>(null)
  const [submitOpen, setSubmitOpen] = useState(false)

  const queryParams = useMemo(() => {
    const p: Record<string, any> = {
      skip: page * pageSize,
      limit: pageSize,
    }
    if (filterType !== ALL) p.type = filterType
    if (filterStatus !== ALL) p.status = filterStatus
    if (filterPriority !== ALL) p.priority = filterPriority
    return p
  }, [page, pageSize, filterType, filterStatus, filterPriority])

  const { data } = useQuery({
    queryKey: ["feedback", queryParams],
    queryFn: () => FeedbackService.listFeedbacks(queryParams),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      FeedbackService.deleteFeedback({ feedbackId: id }),
    onSuccess: () => {
      toast.success(t("feedback.list.deleteSuccess"))
      queryClient.invalidateQueries({ queryKey: ["feedback"] })
      queryClient.invalidateQueries({ queryKey: ["feedback-statistics"] })
      setDeleteOpen(false)
    },
  })

  const columns = useMemo<ColumnDef<FeedbackPublic, any>[]>(() => {
    const cols: ColumnDef<FeedbackPublic, any>[] = [
      {
        id: "index",
        header: "#",
        cell: ({ row }) => (
          <span className="text-xs text-muted-foreground">
            {page * pageSize + row.index + 1}
          </span>
        ),
        size: 50,
      },
      {
        accessorKey: "type",
        header: t("feedback.list.columns.type"),
        cell: ({ row }) => (
          <Badge
            variant="outline"
            className={`text-xs ${TYPE_STYLES[row.original.type ?? "other"]}`}
          >
            {t(`feedback.submit.typeOptions.${row.original.type ?? "other"}`)}
          </Badge>
        ),
        size: 100,
      },
      {
        accessorKey: "title",
        header: t("feedback.list.columns.title"),
        cell: ({ row }) => (
          <TruncatedCell text={row.original.title} maxLen={25} />
        ),
      },
      {
        accessorKey: "status",
        header: t("feedback.list.columns.status"),
        cell: ({ row }) => (
          <Badge
            variant="outline"
            className={`text-xs ${STATUS_STYLES[row.original.status]}`}
          >
            {t(`feedback.list.status.${row.original.status}`)}
          </Badge>
        ),
        size: 90,
      },
      {
        accessorKey: "priority",
        header: t("feedback.list.columns.priority"),
        cell: ({ row }) => (
          <Badge
            variant="outline"
            className={`text-xs ${PRIORITY_STYLES[row.original.priority]}`}
          >
            {t(`feedback.list.priority.${row.original.priority}`)}
          </Badge>
        ),
        size: 80,
      },
      {
        accessorKey: "contact_email",
        header: t("feedback.list.columns.contactEmail"),
        cell: ({ row }) => (
          <TruncatedCell
            text={row.original.contact_email ?? null}
            maxLen={20}
          />
        ),
      },
      {
        accessorKey: "admin_reply",
        header: t("feedback.list.columns.adminReply"),
        cell: ({ row }) => (
          <TruncatedCell text={row.original.admin_reply} maxLen={20} />
        ),
      },
      {
        accessorKey: "created_time",
        header: t("feedback.list.columns.createdTime"),
        cell: ({ row }) => (
          <span className="text-xs text-muted-foreground whitespace-nowrap">
            {format(new Date(row.original.created_time), "yyyy-MM-dd HH:mm")}
          </span>
        ),
        size: 140,
      },
    ]

    if (isAdmin) {
      cols.splice(5, 0, {
        accessorKey: "user_email",
        header: t("feedback.list.columns.userEmail"),
        cell: ({ row }) => (
          <TruncatedCell text={row.original.user_email ?? null} maxLen={20} />
        ),
      })
      cols.splice(6, 0, {
        accessorKey: "user_full_name",
        header: t("feedback.list.columns.userName"),
        cell: ({ row }) => (
          <TruncatedCell
            text={row.original.user_full_name ?? null}
            maxLen={10}
          />
        ),
        size: 80,
      })
    }

    cols.push({
      id: "actions",
      header: "",
      meta: { sticky: "right" },
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="size-7"
            onClick={async () => {
              const detail = await FeedbackService.getFeedback({
                feedbackId: row.original.id,
              })
              setDetailItem(detail)
              setDetailOpen(true)
            }}
          >
            <Eye className="size-3.5" />
          </Button>
          {isAdmin && (
            <>
              <Button
                variant="ghost"
                size="icon"
                className="size-7"
                onClick={async () => {
                  const detail = await FeedbackService.getFeedback({
                    feedbackId: row.original.id,
                  })
                  setEditItem(detail)
                  setEditOpen(true)
                }}
              >
                <Pencil className="size-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="size-7 text-destructive hover:text-destructive"
                onClick={() => {
                  setDeleteItem(row.original)
                  setDeleteOpen(true)
                }}
              >
                <Trash2 className="size-3.5" />
              </Button>
            </>
          )}
        </div>
      ),
      size: isAdmin ? 100 : 40,
    })

    return cols
  }, [t, isAdmin, page, pageSize])

  const TYPES: FeedbackType[] = [
    "bug",
    "feature",
    "improvement",
    "question",
    "other",
  ]
  const STATUSES: FeedbackStatus[] = [
    "pending",
    "in_progress",
    "resolved",
    "closed",
    "rejected",
  ]
  const PRIORITIES: FeedbackPriority[] = ["low", "medium", "high", "urgent"]

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0

  return (
    <div className="flex flex-col gap-6 h-full">
      {/* Toolbar */}
      <div className="shrink-0 flex items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">
          {t("feedback.subtitle")}
        </p>
        <Button onClick={() => setSubmitOpen(true)}>
          <MessageSquarePlus className="mr-2" />
          {t("feedback.fab.submitFeedback")}
        </Button>
      </div>

      {/* Admin statistics */}
      {isAdmin && (
        <div className="shrink-0">
          <FeedbackStatistics />
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 shrink-0">
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-muted-foreground">
            {t("feedback.list.columns.type")}:
          </span>
          <Select
            value={filterType}
            onValueChange={(v) => {
              setFilterType(v)
              setPage(0)
            }}
          >
            <SelectTrigger className="w-[140px] h-8 text-xs">
              <SelectValue placeholder={t("feedback.list.filterType")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>
                {t("feedback.list.filterAll")}
              </SelectItem>
              {TYPES.map((tp) => (
                <SelectItem key={tp} value={tp}>
                  {t(`feedback.submit.typeOptions.${tp}`)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-xs text-muted-foreground">
            {t("feedback.list.columns.status")}:
          </span>
          <Select
            value={filterStatus}
            onValueChange={(v) => {
              setFilterStatus(v)
              setPage(0)
            }}
          >
            <SelectTrigger className="w-[140px] h-8 text-xs">
              <SelectValue placeholder={t("feedback.list.filterStatus")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>
                {t("feedback.list.filterAll")}
              </SelectItem>
              {STATUSES.map((s) => (
                <SelectItem key={s} value={s}>
                  {t(`feedback.list.status.${s}`)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-xs text-muted-foreground">
            {t("feedback.list.columns.priority")}:
          </span>
          <Select
            value={filterPriority}
            onValueChange={(v) => {
              setFilterPriority(v)
              setPage(0)
            }}
          >
            <SelectTrigger className="w-[140px] h-8 text-xs">
              <SelectValue placeholder={t("feedback.list.filterPriority")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>
                {t("feedback.list.filterAll")}
              </SelectItem>
              {PRIORITIES.map((p) => (
                <SelectItem key={p} value={p}>
                  {t(`feedback.list.priority.${p}`)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {hasActiveFilter(filterType, filterStatus, filterPriority) && (
          <Button
            variant="ghost"
            size="sm"
            className="h-8 gap-1.5 text-xs text-muted-foreground"
            onClick={() => {
              setFilterType(ALL)
              setFilterStatus(ALL)
              setFilterPriority(ALL)
              setPage(0)
            }}
          >
            <RotateCcw className="size-3" />
            {t("common.reset")}
          </Button>
        )}
      </div>

      {/* Table */}
      <div className="flex flex-col gap-4 min-h-0 flex-1">
        <div className="flex-1 min-h-0 overflow-y-auto">
          <DataTable
            columns={columns}
            data={data?.items ?? []}
            manualPagination
          />
        </div>

        {/* Server-side pagination */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shrink-0 pb-2">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <div className="text-sm text-muted-foreground">
              {t("common.showRange", {
                start: data?.total ? page * pageSize + 1 : 0,
                end: Math.min((page + 1) * pageSize, data?.total ?? 0),
                total: data?.total ?? 0,
              })}
            </div>
            <div className="flex items-center gap-x-2">
              <p className="text-sm text-muted-foreground">
                {t("common.perPage")}
              </p>
              <Select
                value={`${pageSize}`}
                onValueChange={(v) => {
                  setPageSize(Number(v))
                  setPage(0)
                }}
              >
                <SelectTrigger className="h-8 w-[70px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent side="top">
                  {[10, 20, 50].map((s) => (
                    <SelectItem key={s} value={`${s}`}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <PageNumbers
            currentPage={page}
            totalPages={totalPages}
            onPageChange={setPage}
          />
        </div>
      </div>

      {/* Dialogs */}
      <FeedbackDetailDialog
        open={detailOpen}
        onOpenChange={setDetailOpen}
        feedback={detailItem}
        isAdmin={isAdmin}
      />
      <FeedbackEditDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        feedback={editItem}
      />
      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("common.delete")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("feedback.list.deleteConfirm")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("common.cancel")}</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deleteItem && deleteMutation.mutate(deleteItem.id)}
            >
              {t("common.delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      <FeedbackSubmitDialog open={submitOpen} onOpenChange={setSubmitOpen} />
    </div>
  )
}
