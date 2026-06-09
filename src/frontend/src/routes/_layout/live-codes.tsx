import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import {
  AlertTriangle,
  MoreVertical,
  Pencil,
  Plus,
  QrCode,
  RefreshCw,
  ScanLine,
  Trash2,
  Users,
} from "lucide-react"
import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { LiveCodesService, UsersService } from "@/client/sdk.gen"
import type { LiveCodePublic } from "@/client/types.gen"
import { PageNumbers } from "@/components/Common/PageNumbers"
import { LiveCodeFormDialog } from "@/components/LiveCode/LiveCodeFormDialog"
import { LiveCodeManageSheet } from "@/components/LiveCode/LiveCodeManageSheet"
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { cn, formatDate } from "@/lib/utils"

export const Route = createFileRoute("/_layout/live-codes")({
  component: LiveCodesPage,
  beforeLoad: async () => {
    // 活码为管理员专属功能，非超级管理员访问直接重定向到项目页。
    const user = await UsersService.readUserMe()
    if (!user.is_superuser) {
      throw redirect({ to: "/projects" })
    }
  },
  head: () => ({
    meta: [{ title: "Group QR - LLM4AD" }],
  }),
})

const DEFAULT_PAGE_SIZE = 12

function LiveCodesPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const [page, setPage] = useState(0)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  const [createOpen, setCreateOpen] = useState(false)
  const [manageId, setManageId] = useState<string | null>(null)
  const [editItem, setEditItem] = useState<LiveCodePublic | null>(null)
  const [deleteItem, setDeleteItem] = useState<LiveCodePublic | null>(null)

  const { data, isLoading, isError, refetch, isRefetching } = useQuery({
    queryKey: ["live-codes", page, pageSize],
    queryFn: () =>
      LiveCodesService.listLiveCodes({
        skip: page * pageSize,
        limit: pageSize,
      }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      LiveCodesService.deleteLiveCode({ liveCodeId: id }),
    onSuccess: () => {
      toast.success(t("liveCode.delete.success"))
      queryClient.invalidateQueries({ queryKey: ["live-codes"] })
      setDeleteItem(null)
    },
  })

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0
  const items = data?.items ?? []

  // The edit dialog reuses the create form; it expects a LiveCodeDetail-shaped
  // object. The list item carries all editable fields, so cast is safe here.
  const editAsDetail = useMemo(
    () => (editItem ? { ...editItem, targets: [] } : null),
    [editItem],
  )

  return (
    <div className="flex h-full flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="max-w-2xl text-sm text-muted-foreground">
          {t("liveCode.subtitle")}
        </p>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="icon"
            onClick={() => refetch()}
            title={t("liveCode.refresh")}
          >
            <RefreshCw
              className={cn("size-4", isRefetching && "animate-spin")}
            />
          </Button>
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="mr-2 size-4" />
            {t("liveCode.create")}
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="min-h-0 flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {["s1", "s2", "s3", "s4", "s5", "s6"].map((k) => (
              <Skeleton key={k} className="h-44 rounded-xl" />
            ))}
          </div>
        ) : isError ? (
          <div className="flex h-64 flex-col items-center justify-center gap-3 text-muted-foreground">
            <p className="text-sm">{t("liveCode.loadError")}</p>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              {t("common.retry")}
            </Button>
          </div>
        ) : items.length === 0 ? (
          <div className="flex h-72 flex-col items-center justify-center gap-3 text-center">
            <div className="flex size-14 items-center justify-center rounded-full bg-muted">
              <QrCode className="size-7 text-muted-foreground" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium">{t("liveCode.empty.title")}</p>
              <p className="max-w-sm text-xs text-muted-foreground">
                {t("liveCode.empty.description")}
              </p>
            </div>
            <Button onClick={() => setCreateOpen(true)}>
              <Plus className="mr-2 size-4" />
              {t("liveCode.create")}
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {items.map((item) => (
              <LiveCodeCard
                key={item.id}
                item={item}
                onManage={() => setManageId(item.id)}
                onEdit={() => setEditItem(item)}
                onDelete={() => setDeleteItem(item)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Pagination - matches the projects page */}
      {!isLoading && items.length > 0 && (
        <div className="flex shrink-0 flex-col items-start justify-between gap-4 pt-3 mt-2 sm:flex-row sm:items-center">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <p className="text-sm text-muted-foreground">
              {t("common.showRange", {
                start: data?.total ? page * pageSize + 1 : 0,
                end: Math.min((page + 1) * pageSize, data?.total ?? 0),
                total: data?.total ?? 0,
              })}
            </p>
            {totalPages > 1 && (
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
                    {[12, 24, 48].map((s) => (
                      <SelectItem key={s} value={`${s}`}>
                        {s}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
          {totalPages > 1 && (
            <div className="flex items-center gap-2">
              <PageNumbers
                currentPage={page}
                totalPages={totalPages}
                onPageChange={setPage}
              />
            </div>
          )}
        </div>
      )}

      {/* Create / Edit */}
      <LiveCodeFormDialog open={createOpen} onOpenChange={setCreateOpen} />
      <LiveCodeFormDialog
        open={!!editItem}
        onOpenChange={(o) => !o && setEditItem(null)}
        liveCode={editAsDetail}
      />

      {/* Manage sheet */}
      <LiveCodeManageSheet
        liveCodeId={manageId}
        onOpenChange={(o) => !o && setManageId(null)}
      />

      {/* Delete confirm */}
      <AlertDialog
        open={!!deleteItem}
        onOpenChange={(o) => !o && setDeleteItem(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("liveCode.delete.title")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("liveCode.delete.description")}
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
    </div>
  )
}

interface LiveCodeCardProps {
  item: LiveCodePublic
  onManage: () => void
  onEdit: () => void
  onDelete: () => void
}

function LiveCodeCard({ item, onManage, onEdit, onDelete }: LiveCodeCardProps) {
  const { t } = useTranslation()
  const noValid = item.valid_target_count === 0

  return (
    <div className="group flex flex-col gap-3 rounded-xl border bg-card p-4 transition-shadow hover:shadow-md">
      {/* Title row */}
      <div className="flex items-start gap-2">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <QrCode className="size-4.5" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold">{item.name}</p>
          <p className="truncate text-xs text-muted-foreground">
            {t(`liveCode.strategy.${item.strategy}`)} ·{" "}
            {t("liveCode.card.createdAt")} {formatDate(item.created_time)}
          </p>
          {(item.creator_name || item.creator_email) && (
            <p className="truncate text-xs text-muted-foreground">
              {t("liveCode.card.createdBy")}：
              {item.creator_name || item.creator_email}
            </p>
          )}
        </div>
        {item.contact_display !== "none" && (
          <Badge
            variant="outline"
            className="shrink-0 border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-900 dark:bg-sky-950 dark:text-sky-400"
          >
            {t("liveCode.card.contactBadge")}
          </Badge>
        )}
        <Badge
          variant="outline"
          className={cn(
            "shrink-0",
            item.is_active
              ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-400"
              : "border-zinc-200 bg-zinc-50 text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900",
          )}
        >
          {item.is_active
            ? t("liveCode.status.active")
            : t("liveCode.status.inactive")}
        </Badge>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2">
        <div className="flex items-center gap-2 rounded-lg bg-muted/40 px-3 py-2">
          <ScanLine className="size-4 text-muted-foreground" />
          <div className="min-w-0">
            <p className="text-sm font-semibold leading-none">
              {item.total_scans}
            </p>
            <p className="mt-1 text-[11px] text-muted-foreground">
              {t("liveCode.card.scans")}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-lg bg-muted/40 px-3 py-2">
          <Users className="size-4 text-muted-foreground" />
          <div className="min-w-0">
            <p className="text-sm font-semibold leading-none">
              {item.valid_target_count}
              <span className="text-muted-foreground">
                /{item.target_count}
              </span>
            </p>
            <p className="mt-1 text-[11px] text-muted-foreground">
              {t("liveCode.card.validTargets")}
            </p>
          </div>
        </div>
      </div>

      {/* No-valid warning */}
      {noValid && (
        <div className="flex items-center gap-1.5 rounded-md bg-amber-50 px-2.5 py-1.5 text-[11px] text-amber-700 dark:bg-amber-950 dark:text-amber-400">
          <AlertTriangle className="size-3.5 shrink-0" />
          {t("liveCode.card.noValidWarning")}
        </div>
      )}

      {/* Actions */}
      <div className="mt-auto flex items-center gap-2">
        <Button
          variant="outline"
          className="flex-1 transition-colors hover:border-primary hover:bg-primary hover:text-primary-foreground dark:hover:bg-primary"
          onClick={onManage}
        >
          {t("liveCode.card.manage")}
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <MoreVertical className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={onEdit}>
              <Pencil className="mr-2 size-4" />
              {t("common.edit")}
            </DropdownMenuItem>
            <DropdownMenuItem variant="destructive" onClick={onDelete}>
              <Trash2 className="mr-2 size-4" />
              {t("common.delete")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  )
}
