import { useQuery, useQueryClient } from "@tanstack/react-query"
import {
  AlertCircle,
  BookOpen,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Loader2,
  RefreshCw,
  Sparkles,
} from "lucide-react"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"

import { Llm4AdReportsService } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useProviders } from "@/hooks/useProviders"

import type { AdviseResult, SummaryResult } from "./types"

function parseModels(raw: string | null | undefined): string[] {
  if (!raw) return []
  return raw
    .split(";")
    .map((s) => s.trim())
    .filter(Boolean)
}

interface SummaryDialogProps {
  taskId: string
  open: boolean
  onOpenChange: (open: boolean) => void
  readOnly?: boolean
}

export default function SummaryDialog({
  taskId,
  open,
  onOpenChange,
  readOnly,
}: SummaryDialogProps) {
  const { t, i18n } = useTranslation()
  const queryClient = useQueryClient()
  const [providerId, setProviderId] = useState<string>("default")
  const [modelName, setModelName] = useState<string>("")
  const [goal, setGoal] = useState<string>("")
  const [isPolling, setIsPolling] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [currentIndex, setCurrentIndex] = useState(0)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const providersQuery = useProviders()
  const providers = providersQuery.data?.items ?? []

  const selectedProvider = providers.find((p) => p.id === providerId)
  const availableModels = useMemo(
    () => (selectedProvider ? parseModels(selectedProvider.model) : []),
    [selectedProvider],
  )

  const adviseQuery = useQuery({
    queryKey: ["advise", taskId],
    queryFn: () => Llm4AdReportsService.getAdvise({ taskId }),
    enabled: open && !!taskId,
    staleTime: 10_000,
  })

  const result = adviseQuery.data as AdviseResult<SummaryResult> | undefined
  const status = result?.status ?? null
  const results = result?.data?.results ?? []
  const data = results.length > 0 ? (results[currentIndex] ?? null) : null
  const error = result?.error ?? null

  const startPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current)
    setIsPolling(true)
    pollRef.current = setInterval(() => {
      queryClient.invalidateQueries({ queryKey: ["advise", taskId] })
    }, 3000)
  }, [taskId, queryClient])

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
    setIsPolling(false)
  }, [])

  useEffect(() => {
    if (open && taskId) {
      adviseQuery.refetch()
    }
  }, [open, taskId, adviseQuery.refetch])

  useEffect(() => {
    if (status === "generating" && open && !isPolling) {
      startPolling()
    } else if ((status !== "generating" || !open) && isPolling) {
      stopPolling()
    }
  }, [status, open, isPolling, startPolling, stopPolling])

  useEffect(() => {
    if (!open) stopPolling()
  }, [open, stopPolling])

  const handleProviderChange = useCallback(
    (id: string) => {
      setProviderId(id)
      if (!id || id === "default" || id === "mock") {
        setModelName("")
      } else {
        const p = providers.find((pr) => pr.id === id)
        const models = p ? parseModels(p.model) : []
        setModelName(models.length === 1 ? models[0] : "")
      }
    },
    [providers],
  )

  const handleGenerate = async () => {
    setIsSubmitting(true)
    setCurrentIndex(0)
    try {
      await Llm4AdReportsService.generateAdvise({
        taskId,
        requestBody: {
          goal: goal.trim(),
          language: i18n.language.startsWith("zh") ? "zh" : "en",
          provider_id: providerId === "default" ? null : providerId,
          model_name: modelName || null,
        },
      })
      startPolling()
      queryClient.invalidateQueries({ queryKey: ["advise", taskId] })
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      toast.error(msg)
    } finally {
      setIsSubmitting(false)
    }
  }

  const isGenerating = status === "generating"
  const hasResult = status === "completed" && results.length > 0 && data
  const hasFailed = status === "failed"
  const isEmpty = !status

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <BookOpen className="size-5 text-primary" />
            {t("evolution.evolveAnnotation.summaryDialog")}
          </DialogTitle>
        </DialogHeader>

        {/* Config toolbar */}
        <div className="shrink-0 space-y-2 border-b pb-3">
          <div className="grid grid-cols-2 gap-2">
            <Select
              value={providerId || undefined}
              onValueChange={handleProviderChange}
            >
              <SelectTrigger className="w-full text-xs h-8">
                <SelectValue
                  placeholder={t("evolution.evolveAnnotation.selectProvider")}
                />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="default">
                  <div className="flex items-center gap-1.5">
                    <Badge
                      variant="secondary"
                      className="text-[9px] font-medium px-1 py-0 bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/30"
                    >
                      DEFAULT
                    </Badge>
                    <span className="text-muted-foreground">
                      {t("evolution.evolveAnnotation.defaultProvider")}
                    </span>
                  </div>
                </SelectItem>
                <SelectItem value="mock">
                  <div className="flex items-center gap-1.5">
                    <Badge
                      variant="secondary"
                      className="text-[9px] font-medium px-1 py-0 bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30"
                    >
                      MOCK
                    </Badge>
                    <span className="text-muted-foreground">
                      {t("evolution.evolveAnnotation.mockProvider")}
                    </span>
                  </div>
                </SelectItem>
                {providers.length > 0 && <SelectSeparator />}
                {providers.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    <div className="flex items-center gap-1.5">
                      <span>{p.name}</span>
                      <Badge
                        variant="outline"
                        className="text-[9px] font-normal"
                      >
                        {p.type}
                      </Badge>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <ModelInput
              value={
                !providerId || providerId === "default" || providerId === "mock"
                  ? ""
                  : modelName
              }
              onChange={setModelName}
              suggestions={availableModels}
              disabled={
                !providerId || providerId === "default" || providerId === "mock"
              }
              placeholder={
                !providerId || providerId === "default" || providerId === "mock"
                  ? t("evolution.evolveAnnotation.defaultModel")
                  : t("evolution.evolveAnnotation.inputModel")
              }
            />
          </div>

          <div className="flex items-center gap-2">
            <Input
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder={t("evolution.evolveAnnotation.goalPlaceholder")}
              className="flex-1 h-8 text-xs"
            />
            <Button
              size="sm"
              className="h-8 shrink-0"
              onClick={handleGenerate}
              disabled={isGenerating || isSubmitting || readOnly}
            >
              {isGenerating || isSubmitting ? (
                <Loader2 className="size-3.5 mr-1.5 animate-spin" />
              ) : hasResult || hasFailed ? (
                <RefreshCw className="size-3.5 mr-1.5" />
              ) : (
                <Sparkles className="size-3.5 mr-1.5" />
              )}
              {isGenerating || isSubmitting
                ? t("evolution.evolveAnnotation.generating")
                : hasResult || hasFailed
                  ? t("evolution.evolveAnnotation.regenerate")
                  : t("evolution.evolveAnnotation.generate")}
            </Button>
          </div>
        </div>

        {/* Content area */}
        <div className="flex-1 min-h-0 overflow-y-auto">
          {isGenerating && (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <Loader2 className="size-8 animate-spin text-primary mx-auto mb-3" />
                <p className="text-sm text-muted-foreground">
                  {t("evolution.evolveAnnotation.analyzingHint")}
                </p>
              </div>
            </div>
          )}

          {!isGenerating && isEmpty && (
            <div className="flex items-center justify-center py-12">
              <div className="text-center text-muted-foreground">
                <Sparkles className="size-10 mx-auto mb-3 opacity-40" />
                <p className="text-sm font-medium">
                  {t("evolution.evolveAnnotation.summaryEmpty")}
                </p>
                <p className="text-xs mt-1 opacity-70">
                  {t("evolution.evolveAnnotation.summaryEmptyHint")}
                </p>
              </div>
            </div>
          )}

          {!isGenerating && hasFailed && (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <AlertCircle className="size-10 mx-auto mb-3 text-destructive opacity-60" />
                <p className="text-sm font-medium text-destructive">
                  {t("evolution.evolveAnnotation.summaryFailed")}
                </p>
                <p className="text-xs mt-2 text-muted-foreground max-w-md whitespace-pre-wrap">
                  {error}
                </p>
              </div>
            </div>
          )}

          {!isGenerating && hasResult && data && (
            <div className="space-y-3 py-2">
              {results.length > 1 && (
                <div className="flex items-center justify-between">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 px-2 text-xs"
                    disabled={currentIndex <= 0}
                    onClick={() => setCurrentIndex((i) => i - 1)}
                  >
                    <ChevronLeft className="size-3.5 mr-1" />
                    {t("evolution.evolveAnnotation.prevBlock")}
                  </Button>
                  <span className="text-xs text-muted-foreground">
                    {t("evolution.evolveAnnotation.resultIndex", {
                      current: currentIndex + 1,
                      total: results.length,
                    })}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 px-2 text-xs"
                    disabled={currentIndex >= results.length - 1}
                    onClick={() => setCurrentIndex((i) => i + 1)}
                  >
                    {t("evolution.evolveAnnotation.nextBlock")}
                    <ChevronRight className="size-3.5 ml-1" />
                  </Button>
                </div>
              )}
              {/* Block summary */}
              <Card className="p-3">
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1.5">
                  {t("evolution.evolveAnnotation.rationale")}
                </h4>
                <p className="text-sm leading-relaxed">{data.rationale}</p>
              </Card>

              {/* Feasibility & Significance */}
              <div className="grid grid-cols-2 gap-3">
                <Card className="p-3">
                  <div className="flex items-center gap-2 mb-1.5">
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                      {t("evolution.evolveAnnotation.feasibility")}
                    </h4>
                    <FeasibilityBadge value={data.feasibility} />
                  </div>
                  <p className="text-xs leading-relaxed text-foreground/80">
                    {data.feasibility_reason}
                  </p>
                </Card>
                <Card className="p-3">
                  <div className="flex items-center gap-2 mb-1.5">
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                      {t("evolution.evolveAnnotation.significanceLabel")}
                    </h4>
                    <SignificanceBadge value={data.significance} />
                  </div>
                  <p className="text-xs leading-relaxed text-foreground/80">
                    {data.significance_reason}
                  </p>
                </Card>
              </div>

              {/* Block summary text */}
              {data.block_summary && (
                <Card className="p-3">
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1.5">
                    {t("evolution.evolveAnnotation.blockSummary")}
                  </h4>
                  <p className="text-sm leading-relaxed">
                    {data.block_summary}
                  </p>
                </Card>
              )}

              {/* Concerns */}
              {data.concerns.length > 0 && (
                <Card className="p-3">
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                    {t("evolution.evolveAnnotation.concerns")}
                  </h4>
                  <ul className="space-y-1.5">
                    {data.concerns.map((item, i) => (
                      <li
                        key={i}
                        className="text-xs flex items-start gap-2 text-foreground/80"
                      >
                        <AlertCircle className="size-3 shrink-0 mt-0.5 text-amber-500" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </Card>
              )}

              {/* Suggestions */}
              {data.suggestions.length > 0 && (
                <Card className="p-3">
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                    {t("evolution.evolveAnnotation.suggestions")}
                  </h4>
                  <ul className="space-y-1.5">
                    {data.suggestions.map((item, i) => (
                      <li
                        key={i}
                        className="text-xs flex items-start gap-2 text-foreground/80"
                      >
                        <Sparkles className="size-3 shrink-0 mt-0.5 text-primary" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </Card>
              )}

              {/* Block ref */}
              {data.block_ref && (
                <Card className="p-3">
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1.5">
                    {t("evolution.evolveAnnotation.blockRef")}
                  </h4>
                  <p className="text-xs font-mono text-foreground/80">
                    {data.block_ref.file_path} (L{data.block_ref.line_start}-
                    {data.block_ref.line_end})
                  </p>
                </Card>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

function FeasibilityBadge({ value }: { value: string }) {
  const { t } = useTranslation()
  const colors: Record<string, string> = {
    yes: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
    partial:
      "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
    no: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
  }
  return (
    <Badge
      variant="secondary"
      className={`text-[10px] px-1.5 py-0 ${colors[value] ?? ""}`}
    >
      {t(`evolution.evolveAnnotation.feasibilityValue.${value}`)}
    </Badge>
  )
}

function SignificanceBadge({ value }: { value: string }) {
  const { t } = useTranslation()
  const colors: Record<string, string> = {
    high: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
    medium:
      "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
    low: "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-300",
  }
  return (
    <Badge
      variant="secondary"
      className={`text-[10px] px-1.5 py-0 ${colors[value] ?? ""}`}
    >
      {t(`evolution.evolveAnnotation.significance.${value}`)}
    </Badge>
  )
}

function ModelInput({
  value,
  onChange,
  suggestions,
  disabled,
  placeholder,
}: {
  value: string
  onChange: (v: string) => void
  suggestions: string[]
  disabled: boolean
  placeholder: string
}) {
  const [open, setOpen] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false)
      }
    }
    document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [])

  return (
    <div ref={containerRef} className="relative">
      <Input
        ref={inputRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => !disabled && suggestions.length > 0 && setOpen(true)}
        disabled={disabled}
        readOnly={disabled}
        placeholder={placeholder}
        className="h-8 text-xs pr-7"
      />
      {!disabled && (
        <button
          type="button"
          className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          onClick={() => {
            setOpen(!open)
            inputRef.current?.focus()
          }}
        >
          <ChevronDown className="size-3.5" />
        </button>
      )}
      {open && suggestions.length > 0 && (
        <div className="absolute z-50 top-full mt-1 left-0 w-full max-h-48 overflow-y-auto rounded-md border bg-popover p-1 shadow-md">
          {suggestions.map((model) => (
            <button
              key={model}
              type="button"
              className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-xs hover:bg-accent"
              onClick={() => {
                onChange(model)
                setOpen(false)
              }}
            >
              <Check
                className={`size-3 ${value === model ? "opacity-100" : "opacity-0"}`}
              />
              {model}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
