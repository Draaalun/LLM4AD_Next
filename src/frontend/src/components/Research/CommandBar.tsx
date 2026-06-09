import {
  Archive,
  BookOpen,
  ChevronRight,
  ChevronsDownUp,
  ChevronsUpDown,
  Code2,
  Dna,
  Download,
  FileText,
  Paperclip,
  Play,
  Send,
  Settings2,
  ShieldCheck,
  Square,
  Zap,
} from "lucide-react"
import type { RefObject } from "react"
import { useState } from "react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

import type { StepState } from "./mock-data"

interface CommandBarProps {
  step: number
  inputValue: string
  onInputChange: (value: string) => void
  onSend: () => void
  inputRef: RefObject<HTMLTextAreaElement | null>
  stepState: StepState | null
  onNext: () => void
  streamingContent?: string | null
  onOpenConfig?: () => void
  onOpenArchive?: () => void
}

const STEP_PLACEHOLDERS = [
  "research.commandBar.placeholder0",
  "research.commandBar.placeholder1",
  "research.commandBar.placeholder2",
  "research.commandBar.placeholder3",
]

const STEP_ICONS = [BookOpen, Code2, Dna, FileText]
const STEP_COLORS = [
  "text-blue-500 bg-blue-500/10 border-blue-500/20",
  "text-violet-500 bg-violet-500/10 border-violet-500/20",
  "text-emerald-500 bg-emerald-500/10 border-emerald-500/20",
  "text-amber-500 bg-amber-500/10 border-amber-500/20",
]

export default function CommandBar({
  step,
  inputValue,
  onInputChange,
  onSend,
  inputRef,
  stepState,
  onNext,
  streamingContent,
  onOpenConfig,
  onOpenArchive,
}: CommandBarProps) {
  const { t } = useTranslation()
  const [isFocused, setIsFocused] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const [execMode, setExecMode] = useState<"auto" | "confirm">("auto")
  const isRunning = stepState?.status === "running"
  const isCompleted = stepState?.status === "completed"

  const StepIcon = STEP_ICONS[step]
  const stepColor = STEP_COLORS[step]
  const stepLabels = [
    t("research.steps.backgroundResearch"),
    t("research.steps.algorithmDesign"),
    t("research.steps.algorithmEvolve"),
    t("research.steps.paperCompilation"),
  ]

  const handleSend = () => {
    onSend()
    setIsExpanded(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="shrink-0 pt-2">
      <div className="max-w-4xl mx-auto">
        {/* Streaming content area */}
        {streamingContent && (
          <div className="mb-2 max-h-[120px] overflow-y-auto rounded-xl border border-border/30 bg-muted/20 px-4 py-3">
            <p className="text-xs leading-relaxed text-foreground/70 whitespace-pre-wrap">
              {streamingContent}
            </p>
          </div>
        )}
        {/* Input area */}
        <div
          className={`relative rounded-2xl bg-card/95 backdrop-blur-md transition-shadow duration-200 ease-out border-2 ${
            isExpanded
              ? "shadow-2xl shadow-primary/15 border-primary/40 ring-1 ring-primary/20"
              : isFocused
                ? "shadow-xl shadow-primary/10 border-primary/35"
                : "shadow-md border-border/30 hover:border-primary/20 hover:shadow-lg"
          }`}
        >
          {/* Step indicator + execution mode bar */}
          <div className="flex items-center justify-between px-4 pt-2.5 pb-1">
            <div
              className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[10px] font-medium ${stepColor}`}
            >
              <StepIcon className="size-3" strokeWidth={2.5} />
              <span>{stepLabels[step]}</span>
            </div>
            <div className="flex items-center gap-0.5 rounded-lg border border-border/30 bg-muted/30 p-0.5">
              <button
                type="button"
                onClick={() => setExecMode("auto")}
                className={`flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium transition-colors ${
                  execMode === "auto"
                    ? "bg-primary/15 text-primary border border-primary/25"
                    : "text-muted-foreground/60 hover:text-foreground/70"
                }`}
              >
                <Zap className="size-2.5" />
                {t("research.commandBar.autoExec")}
              </button>
              <button
                type="button"
                onClick={() => setExecMode("confirm")}
                className={`flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium transition-colors ${
                  execMode === "confirm"
                    ? "bg-amber-500/15 text-amber-600 border border-amber-500/25"
                    : "text-muted-foreground/60 hover:text-foreground/70"
                }`}
              >
                <ShieldCheck className="size-2.5" />
                {t("research.commandBar.confirmExec")}
              </button>
            </div>
          </div>
          <div className="px-4 pt-3 pb-2">
            <Textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => onInputChange(e.target.value)}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              onKeyDown={handleKeyDown}
              placeholder={t(STEP_PLACEHOLDERS[step])}
              rows={isExpanded ? 8 : 2}
              className="resize-none border-0 bg-transparent p-0 text-sm leading-relaxed focus-visible:ring-0 focus-visible:ring-offset-0 shadow-none placeholder:text-muted-foreground/40"
            />
          </div>

          {/* Bottom toolbar */}
          <div className="flex items-center justify-between px-3 pb-3">
            {/* Left: attachment + expand + step controls */}
            <div className="flex items-center gap-2">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className="size-7 text-muted-foreground/50 hover:text-foreground/70 hover:bg-muted/60 transition-colors rounded-lg"
                  >
                    <Paperclip className="size-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  {t("research.commandBar.uploadFile")}
                </TooltipContent>
              </Tooltip>

              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className="size-7 text-muted-foreground/50 hover:text-foreground/70 hover:bg-muted/60 transition-colors rounded-lg"
                    onClick={() => setIsExpanded(!isExpanded)}
                  >
                    {isExpanded ? (
                      <ChevronsDownUp className="size-3.5" />
                    ) : (
                      <ChevronsUpDown className="size-3.5" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  {isExpanded
                    ? t("research.commandBar.collapse")
                    : t("research.commandBar.expand")}
                </TooltipContent>
              </Tooltip>

              <div className="w-px h-4 bg-border/30" />

              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2 gap-1.5 text-xs text-muted-foreground/50 hover:text-foreground/70 hover:bg-muted/60 transition-colors rounded-lg"
                onClick={onOpenConfig}
              >
                <Settings2 className="size-3.5" />
                <span>{t("research.config.title")}</span>
              </Button>

              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2 gap-1.5 text-xs text-muted-foreground/50 hover:text-foreground/70 hover:bg-muted/60 transition-colors rounded-lg"
                onClick={onOpenArchive}
              >
                <Archive className="size-3.5" />
                <span>{t("research.snapshots.tooltip")}</span>
              </Button>
            </div>

            {/* Right: action buttons */}
            <div className="flex items-center gap-2">
              {isCompleted && step < 3 && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-1 h-7 px-3 rounded-lg text-[11px] text-primary hover:bg-primary/8"
                  onClick={onNext}
                >
                  {t("research.actions.next")}
                  <ChevronRight className="size-3" />
                </Button>
              )}

              {step === 3 && isCompleted && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-1.5 h-7 px-3 rounded-lg text-[11px] text-muted-foreground/70 hover:text-foreground"
                >
                  <Download className="size-3" />
                  {t("research.content.downloadPdf")}
                </Button>
              )}

              {isRunning ? (
                <Button
                  size="sm"
                  className="gap-1.5 h-8 px-4 rounded-lg bg-destructive text-destructive-foreground hover:bg-destructive/90 text-[12px] font-medium"
                >
                  <Square className="size-3" />
                  {t("research.actions.stop")}
                </Button>
              ) : (
                <Button
                  size="sm"
                  className="gap-1.5 h-8 px-4 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-[12px] font-medium shadow-md shadow-primary/20"
                  onClick={handleSend}
                >
                  {inputValue.trim() ? (
                    <Send className="size-3" />
                  ) : (
                    <Play className="size-3" />
                  )}
                  {t("research.actions.run")}
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
