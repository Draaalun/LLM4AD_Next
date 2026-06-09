import {
  BookOpen,
  Bot,
  ChevronDown,
  ChevronUp,
  Code2,
  Dna,
  Eye,
  FileText,
  RotateCcw,
  Sparkles,
  Terminal,
  User,
} from "lucide-react"
import type { RefObject } from "react"
import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"

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

import CommandBar from "./CommandBar"
import type { ChatMessage, LogEntry, StepState } from "./mock-data"

const LEVEL_COLORS: Record<string, string> = {
  info: "text-blue-400",
  warn: "text-amber-400",
  error: "text-red-400",
  debug: "text-muted-foreground/60",
}

const LEVEL_BG: Record<string, string> = {
  info: "bg-blue-500/10 border-blue-500/20",
  warn: "bg-amber-500/10 border-amber-500/20",
  error: "bg-red-500/10 border-red-500/20",
  debug: "bg-muted/30 border-border/30",
}

const STEP_LABELS = [
  "research.steps.background",
  "research.steps.design",
  "research.steps.evolution",
  "research.steps.paper",
]

interface ChatAreaProps {
  step: number
  messages: ChatMessage[]
  logs: LogEntry[]
  inputValue: string
  onInputChange: (value: string) => void
  onSend: () => void
  inputRef: RefObject<HTMLTextAreaElement | null>
  stepState: StepState | null
  onNext: () => void
  streamingContent?: string | null
  onOpenConfig?: () => void
  onOpenArchive?: () => void
  onRestoreLog?: (logId: string) => void
  onViewLog?: (logId: string) => void
}

export default function ChatArea({
  step,
  messages,
  logs,
  inputValue,
  onInputChange,
  onSend,
  inputRef,
  stepState,
  onNext,
  streamingContent,
  onOpenConfig,
  onOpenArchive,
  onRestoreLog,
  onViewLog,
}: ChatAreaProps) {
  const { t } = useTranslation()
  const msgEndRef = useRef<HTMLDivElement>(null)
  const [logsExpanded, setLogsExpanded] = useState(false)
  const [restoreConfirmId, setRestoreConfirmId] = useState<string | null>(null)

  useEffect(() => {
    msgEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [])

  const hasMessages = messages.length > 0

  return (
    <div className="flex-1 h-full flex flex-col min-w-0 relative overflow-hidden">
      {/* Background: subtle centered radial gradient */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute inset-0 bg-gradient-to-b from-primary/[0.03] via-transparent to-primary/[0.02]" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[90%] h-[70%] bg-radial-[ellipse_at_center] from-primary/[0.06] via-blue-500/[0.03] to-transparent rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-0 right-0 h-1/3 bg-gradient-to-t from-violet-500/[0.03] to-transparent" />
        {/* Dot grid pattern */}
        <div className="absolute inset-0 opacity-[0.015] bg-[radial-gradient(circle_at_1px_1px,currentColor_1px,transparent_0)] bg-[size:28px_28px]" />
      </div>

      {/* Content wrapper: fills available height */}
      <div className="relative flex-1 flex flex-col min-h-0">
        {/* Messages area */}
        <div className="overflow-y-auto relative flex-1 min-h-0">
          {!hasMessages ? (
            <WelcomeState step={step} />
          ) : (
            <div className="max-w-4xl mx-auto px-6 py-6 pb-4 space-y-4">
              {messages.map((msg, idx) => {
                const prevMsg = idx > 0 ? messages[idx - 1] : null
                const showStepDivider = !prevMsg || prevMsg.step !== msg.step
                return (
                  <div key={msg.id}>
                    {showStepDivider && <StepDivider step={msg.step} />}
                    <MessageBubble message={msg} />
                  </div>
                )
              })}
              <div ref={msgEndRef} />
            </div>
          )}
        </div>

        {/* Logs area - between messages and input */}
        {logs.length > 0 && (
          <div
            className={`shrink-0 relative border-t border-border/20 flex flex-col ${logsExpanded ? "max-h-[200px]" : ""} transition-all duration-300`}
          >
            <button
              onClick={() => setLogsExpanded((v) => !v)}
              className="w-full flex items-center gap-2 px-4 py-1.5 text-xs text-muted-foreground hover:text-foreground/70 hover:bg-muted/30 transition-colors shrink-0"
            >
              <Terminal className="size-3" />
              <span>{t("research.chat.logs")}</span>
              <span className="px-1.5 py-px rounded-full bg-muted/50 text-[9px] font-bold tabular-nums">
                {logs.length}
              </span>
              {logsExpanded ? (
                <ChevronDown className="size-3 ml-auto" />
              ) : (
                <ChevronUp className="size-3 ml-auto" />
              )}
            </button>
            {logsExpanded && (
              <div className="flex-1 min-h-0 overflow-y-auto px-4 pb-2 font-mono text-[11px] space-y-0.5">
                {logs.map((log, idx) => {
                  const isRestorable =
                    onRestoreLog && idx >= Math.max(0, logs.length - 10)
                  return (
                    <div
                      key={log.id}
                      className="group flex items-start gap-2 py-1 px-2 rounded-lg hover:bg-muted/30 transition-colors"
                    >
                      <span className="text-muted-foreground/40 shrink-0 tabular-nums text-[10px] pt-0.5">
                        {new Date(log.timestamp).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })}
                      </span>
                      <span
                        className={`shrink-0 px-1.5 py-px rounded text-[9px] uppercase font-bold border ${LEVEL_COLORS[log.level]} ${LEVEL_BG[log.level]}`}
                      >
                        {log.level}
                      </span>
                      <span className="text-foreground/60 break-all leading-relaxed flex-1">
                        {log.message}
                      </span>
                      {isRestorable && (
                        <div className="shrink-0 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={() => onViewLog?.(log.id)}
                            className="flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-muted/60 text-muted-foreground/40 hover:text-foreground/70 text-[11px]"
                          >
                            <Eye className="size-3" />
                            <span className="font-sans">
                              {t("research.chat.viewLog")}
                            </span>
                          </button>
                          <button
                            onClick={() => setRestoreConfirmId(log.id)}
                            className="flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-primary/10 text-muted-foreground/40 hover:text-primary text-[11px]"
                          >
                            <RotateCcw className="size-3" />
                            <span className="font-sans">
                              {t("research.chat.restoreToHere")}
                            </span>
                          </button>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input - at bottom of flex column */}
      <div className="shrink-0 max-w-4xl mx-auto w-full px-4 pb-4 pt-2">
        <CommandBar
          step={step}
          inputValue={inputValue}
          onInputChange={onInputChange}
          onSend={onSend}
          inputRef={inputRef}
          stepState={stepState}
          onNext={onNext}
          streamingContent={streamingContent}
          onOpenConfig={onOpenConfig}
          onOpenArchive={onOpenArchive}
        />
      </div>

      {/* Restore confirmation dialog */}
      <AlertDialog
        open={!!restoreConfirmId}
        onOpenChange={(open) => !open && setRestoreConfirmId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t("research.chat.restoreConfirmTitle")}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t("research.chat.restoreConfirmDesc")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("common.cancel")}</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (restoreConfirmId && onRestoreLog) {
                  onRestoreLog(restoreConfirmId)
                }
                setRestoreConfirmId(null)
              }}
            >
              {t("research.chat.restoreConfirm")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

function WelcomeState({ step }: { step: number }) {
  const { t } = useTranslation()
  return (
    <div className="h-full flex flex-col items-center justify-center px-6">
      <div className="size-16 rounded-3xl bg-gradient-to-br from-primary/20 via-primary/10 to-violet-500/10 flex items-center justify-center mb-5 border border-primary/15 shadow-lg shadow-primary/5">
        <Sparkles className="size-7 text-primary/70" />
      </div>
      <h2 className="text-lg font-semibold text-foreground/80 mb-2">
        {t("research.chat.welcome")}
      </h2>
      <p className="text-sm text-muted-foreground/60 text-center max-w-md leading-relaxed">
        {t("research.chat.welcomeHint")}
      </p>
      <div className="mt-6 px-3 py-1.5 rounded-full bg-muted/40 border border-border/30 text-xs text-muted-foreground/50">
        {t(STEP_LABELS[step])}
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user"
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`size-8 rounded-full flex items-center justify-center shrink-0 shadow-sm mt-1 ${
          isUser
            ? "bg-gradient-to-br from-primary/20 to-blue-500/20 text-primary border border-primary/20"
            : "bg-gradient-to-br from-emerald-500/15 to-teal-500/15 text-emerald-600 border border-emerald-500/20"
        }`}
      >
        {isUser ? <User className="size-4" /> : <Bot className="size-4" />}
      </div>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "bg-primary/8 text-foreground border border-primary/15 rounded-tr-md shadow-sm"
            : "bg-gradient-to-br from-background/90 to-muted/30 text-foreground/85 border border-border/40 rounded-tl-md shadow-md backdrop-blur-sm"
        }`}
      >
        <div
          className={
            isUser ? "" : "prose prose-sm max-w-none dark:prose-invert"
          }
        >
          {message.content}
        </div>
        <div
          className={`mt-2 text-[10px] tabular-nums ${isUser ? "text-primary/40 text-right" : "text-muted-foreground/40"}`}
        >
          {new Date(message.timestamp).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
      </div>
    </div>
  )
}

const STEP_DIVIDER_ICONS = [BookOpen, Code2, Dna, FileText]
const STEP_DIVIDER_COLORS = [
  "text-blue-500 bg-blue-500/10 border-blue-500/20",
  "text-violet-500 bg-violet-500/10 border-violet-500/20",
  "text-emerald-500 bg-emerald-500/10 border-emerald-500/20",
  "text-amber-500 bg-amber-500/10 border-amber-500/20",
]

function StepDivider({ step }: { step: number }) {
  const { t } = useTranslation()
  const Icon = STEP_DIVIDER_ICONS[step] ?? BookOpen
  const colorClass = STEP_DIVIDER_COLORS[step] ?? STEP_DIVIDER_COLORS[0]
  const labels = [
    t("research.steps.backgroundResearch"),
    t("research.steps.algorithmDesign"),
    t("research.steps.algorithmEvolve"),
    t("research.steps.paperCompilation"),
  ]

  return (
    <div className="flex items-center gap-3 py-2">
      <div className="flex-1 h-px bg-border/30" />
      <div
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[10px] font-medium ${colorClass}`}
      >
        <Icon className="size-3" strokeWidth={2.5} />
        <span>{labels[step]}</span>
      </div>
      <div className="flex-1 h-px bg-border/30" />
    </div>
  )
}
