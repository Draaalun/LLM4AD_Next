import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  Check,
  Copy,
  Download,
  ExternalLink,
  ImageUp,
  Loader2,
  Pencil,
  QrCode,
  RotateCcw,
  Trash2,
} from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { LiveCodesService } from "@/client/sdk.gen"
import type { ContactDisplay, TargetPublic } from "@/client/types.gen"
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
import { Checkbox } from "@/components/ui/checkbox"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { cn, formatDate } from "@/lib/utils"
import { LiveCodeFormDialog } from "./LiveCodeFormDialog"
import { TARGET_STATUS_STYLES } from "./liveCodeStyles"
import { TargetEditDialog } from "./TargetEditDialog"
import { TargetUploadDialog } from "./TargetUploadDialog"

/** Prefix a relative `/api/v1/...` path with the configured API base. */
const apiUrl = (path: string) => `${import.meta.env.VITE_API_URL || ""}${path}`

interface LiveCodeManageSheetProps {
  liveCodeId: string | null
  onOpenChange: (open: boolean) => void
}

export function LiveCodeManageSheet({
  liveCodeId,
  onOpenChange,
}: LiveCodeManageSheetProps) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const open = !!liveCodeId

  const [copied, setCopied] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<TargetPublic | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<TargetPublic | null>(null)

  const { data: detail, isLoading } = useQuery({
    queryKey: ["live-code", liveCodeId],
    queryFn: () => LiveCodesService.getLiveCode({ liveCodeId: liveCodeId! }),
    enabled: open,
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["live-code", liveCodeId] })
    queryClient.invalidateQueries({ queryKey: ["live-codes"] })
    queryClient.invalidateQueries({ queryKey: ["live-qr-contact"] })
  }

  const toggleActive = useMutation({
    mutationFn: (next: boolean) =>
      LiveCodesService.updateLiveCode({
        liveCodeId: liveCodeId!,
        requestBody: { is_active: next },
      }),
    onSuccess: invalidate,
  })

  const setContactDisplay = useMutation({
    mutationFn: (next: ContactDisplay) =>
      LiveCodesService.updateLiveCode({
        liveCodeId: liveCodeId!,
        requestBody: { contact_display: next },
      }),
    onSuccess: invalidate,
  })

  const resetScan = useMutation({
    mutationFn: (targetId: string) =>
      LiveCodesService.resetTargetScan({ liveCodeId: liveCodeId!, targetId }),
    onSuccess: () => {
      toast.success(t("liveCode.manage.resetSuccess"))
      invalidate()
    },
  })

  const deleteTargetMutation = useMutation({
    mutationFn: (targetId: string) =>
      LiveCodesService.deleteTarget({ liveCodeId: liveCodeId!, targetId }),
    onSuccess: () => {
      toast.success(t("liveCode.manage.deleteTargetSuccess"))
      setDeleteTarget(null)
      invalidate()
    },
  })

  const copyUrl = async () => {
    if (!detail) return
    await navigator.clipboard.writeText(detail.public_url)
    setCopied(true)
    toast.success(t("liveCode.manage.copied"))
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onOpenChange(false)}>
      <SheetContent
        side="right"
        className="flex w-full flex-col gap-0 p-0 sm:max-w-xl"
      >
        <SheetHeader className="shrink-0 border-b">
          <SheetTitle className="flex items-center gap-2 pr-8">
            <QrCode className="size-4 shrink-0" />
            <span className="truncate">
              {detail?.name ?? t("liveCode.manage.title")}
            </span>
            {detail && (
              <Badge
                variant="outline"
                className={cn(
                  "ml-auto shrink-0",
                  detail.is_active
                    ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-400"
                    : "border-zinc-200 bg-zinc-50 text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900",
                )}
              >
                {detail.is_active
                  ? t("liveCode.status.active")
                  : t("liveCode.status.inactive")}
              </Badge>
            )}
          </SheetTitle>
          <SheetDescription className="sr-only">
            {t("liveCode.manage.title")}
          </SheetDescription>
        </SheetHeader>

        {isLoading || !detail ? (
          <div className="flex flex-1 items-center justify-center">
            <Loader2 className="size-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="flex-1 space-y-6 overflow-y-auto p-4">
            {/* Permanent QR */}
            <section className="flex flex-col items-center gap-3 rounded-xl border bg-muted/30 p-5">
              <div className="rounded-lg border bg-white p-3 shadow-sm">
                <img
                  src={apiUrl(detail.qrcode_url)}
                  alt={t("liveCode.manage.permanentQr")}
                  className="size-44 object-contain"
                />
              </div>
              <p className="text-center text-xs text-muted-foreground">
                {t("liveCode.manage.permanentQrHint")}
              </p>
              <div className="flex w-full items-center gap-2">
                <div className="flex min-w-0 flex-1 items-center gap-2 rounded-md border bg-background px-3 py-2">
                  <span className="truncate text-xs text-muted-foreground">
                    {detail.public_url}
                  </span>
                </div>
                <Button
                  variant="outline"
                  size="icon"
                  className="size-9 shrink-0"
                  onClick={copyUrl}
                  title={t("liveCode.manage.copy")}
                >
                  {copied ? (
                    <Check className="size-4 text-emerald-600" />
                  ) : (
                    <Copy className="size-4" />
                  )}
                </Button>
                <Button
                  variant="outline"
                  size="icon"
                  className="size-9 shrink-0"
                  asChild
                  title={t("liveCode.manage.open")}
                >
                  <a href={detail.public_url} target="_blank" rel="noreferrer">
                    <ExternalLink className="size-4" />
                  </a>
                </Button>
              </div>
              <Button variant="secondary" className="w-full" asChild>
                <a
                  href={apiUrl(detail.qrcode_url)}
                  download={`live-qr-${detail.slug}.png`}
                >
                  <Download className="mr-2 size-4" />
                  {t("liveCode.manage.downloadQr")}
                </a>
              </Button>
            </section>

            {/* Settings */}
            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">
                  {t("liveCode.manage.settings")}
                </h3>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 gap-1.5 text-xs"
                  onClick={() => setEditOpen(true)}
                >
                  <Pencil className="size-3.5" />
                  {t("liveCode.manage.edit")}
                </Button>
              </div>

              <div className="flex items-start gap-3 rounded-lg border p-3">
                <Checkbox
                  className="mt-0.5"
                  checked={detail.is_active}
                  disabled={toggleActive.isPending}
                  onCheckedChange={(v) => toggleActive.mutate(v === true)}
                />
                <div className="space-y-0.5">
                  <p className="text-sm font-medium">
                    {t("liveCode.manage.activeLabel")}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {t("liveCode.manage.activeHint")}
                  </p>
                </div>
              </div>

              <div className="flex flex-col gap-2 rounded-lg border p-3">
                <div className="space-y-0.5">
                  <p className="text-sm font-medium">
                    {t("liveCode.manage.contactLabel")}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {t("liveCode.manage.contactHint")}
                  </p>
                </div>
                <Select
                  value={detail.contact_display}
                  disabled={setContactDisplay.isPending}
                  onValueChange={(v) =>
                    setContactDisplay.mutate(v as ContactDisplay)
                  }
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">
                      {t("liveCode.manage.contactDisplay.none")}
                    </SelectItem>
                    <SelectItem value="landing">
                      {t("liveCode.manage.contactDisplay.landing")}
                    </SelectItem>
                    <SelectItem value="direct">
                      {t("liveCode.manage.contactDisplay.direct")}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="rounded-lg border p-3">
                <p className="text-xs text-muted-foreground">
                  {t("liveCode.manage.strategyLabel")}
                </p>
                <p className="mt-0.5 text-sm font-medium">
                  {t(`liveCode.strategy.${detail.strategy}`)}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {t(`liveCode.strategy.hint.${detail.strategy}`)}
                </p>
              </div>
            </section>

            <Separator />

            {/* Targets */}
            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold">
                    {t("liveCode.manage.targets")}{" "}
                    <span className="text-muted-foreground">
                      ({detail.valid_target_count}/{detail.target_count})
                    </span>
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    {t("liveCode.manage.targetsHint")}
                  </p>
                </div>
                <Button size="sm" onClick={() => setUploadOpen(true)}>
                  <ImageUp className="mr-1.5 size-4" />
                  {t("liveCode.manage.addTargets")}
                </Button>
              </div>

              {detail.targets && detail.targets.length > 0 ? (
                <ul className="space-y-2">
                  {detail.targets.map((target) => (
                    <TargetRow
                      key={target.id}
                      target={target}
                      onEdit={() => setEditTarget(target)}
                      onReset={() => resetScan.mutate(target.id)}
                      onDelete={() => setDeleteTarget(target)}
                      resetting={
                        resetScan.isPending && resetScan.variables === target.id
                      }
                    />
                  ))}
                </ul>
              ) : (
                <div className="flex flex-col items-center gap-1 rounded-lg border border-dashed py-8 text-center">
                  <p className="text-sm font-medium">
                    {t("liveCode.manage.noTargets")}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {t("liveCode.manage.noTargetsHint")}
                  </p>
                </div>
              )}
            </section>
          </div>
        )}
      </SheetContent>

      {/* Nested dialogs */}
      {detail && (
        <LiveCodeFormDialog
          open={editOpen}
          onOpenChange={setEditOpen}
          liveCode={detail}
        />
      )}
      {liveCodeId && (
        <TargetUploadDialog
          open={uploadOpen}
          onOpenChange={setUploadOpen}
          liveCodeId={liveCodeId}
        />
      )}
      {liveCodeId && (
        <TargetEditDialog
          open={!!editTarget}
          onOpenChange={(o) => !o && setEditTarget(null)}
          liveCodeId={liveCodeId}
          target={editTarget}
        />
      )}

      <AlertDialog
        open={!!deleteTarget}
        onOpenChange={(o) => !o && setDeleteTarget(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t("liveCode.manage.deleteTargetTitle")}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t("liveCode.manage.deleteTargetDescription")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("common.cancel")}</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() =>
                deleteTarget && deleteTargetMutation.mutate(deleteTarget.id)
              }
            >
              {t("common.delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Sheet>
  )
}

interface TargetRowProps {
  target: TargetPublic
  onEdit: () => void
  onReset: () => void
  onDelete: () => void
  resetting: boolean
}

function TargetRow({
  target,
  onEdit,
  onReset,
  onDelete,
  resetting,
}: TargetRowProps) {
  const { t } = useTranslation()

  const expiryText = () => {
    if (!target.expires_at) return t("liveCode.manage.neverExpire")
    const date = formatDate(target.expires_at)
    return target.status === "expired"
      ? t("liveCode.manage.expiredAt", { date })
      : t("liveCode.manage.expiresAt", { date })
  }

  const scanText =
    target.scan_limit != null
      ? t("liveCode.manage.scanProgressLimited", {
          count: target.scan_count,
          limit: target.scan_limit,
        })
      : t("liveCode.manage.scanProgress", { count: target.scan_count })

  const progress =
    target.scan_limit != null && target.scan_limit > 0
      ? Math.min(100, (target.scan_count / target.scan_limit) * 100)
      : null

  return (
    <li
      className={cn(
        "flex items-center gap-3 rounded-lg border p-2.5",
        !target.is_valid && "bg-muted/30",
      )}
    >
      <img
        src={apiUrl(target.image_url)}
        alt={target.label ?? ""}
        className="size-14 shrink-0 rounded-md border object-cover"
      />
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium">
            {target.label || `#${target.sort_order}`}
          </span>
          <Badge
            variant="outline"
            className={cn("text-[10px]", TARGET_STATUS_STYLES[target.status])}
          >
            {t(`liveCode.targetStatus.${target.status}`)}
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground">{expiryText()}</p>
        <div className="flex items-center gap-2">
          {progress != null && (
            <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
              <div
                className={cn(
                  "h-full rounded-full",
                  progress >= 100 ? "bg-rose-500" : "bg-emerald-500",
                )}
                style={{ width: `${progress}%` }}
              />
            </div>
          )}
          <span className="text-xs text-muted-foreground">{scanText}</span>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-0.5">
        <Button
          variant="ghost"
          size="icon"
          className="size-7"
          onClick={onEdit}
          title={t("liveCode.manage.editTarget")}
        >
          <Pencil className="size-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="size-7"
          onClick={onReset}
          disabled={resetting}
          title={t("liveCode.manage.reset")}
        >
          {resetting ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : (
            <RotateCcw className="size-3.5" />
          )}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="size-7 text-destructive hover:text-destructive"
          onClick={onDelete}
          title={t("liveCode.manage.deleteTarget")}
        >
          <Trash2 className="size-3.5" />
        </Button>
      </div>
    </li>
  )
}
