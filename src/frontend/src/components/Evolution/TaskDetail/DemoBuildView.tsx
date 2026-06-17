import {
  Bot,
  Check,
  ChevronsUpDown,
  CircleAlert,
  FileCode,
  Layers,
  Loader2,
  Monitor,
  Play,
  Send,
  Sparkles,
  X,
} from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"

import { DEMO_AI_BUILD_FILES } from "@/data/demoFixtures"
import { setDemoPhase, useDemoState } from "@/hooks/useDemoMode"
import { cn } from "@/lib/utils"

/**
 * One scripted exchange. The user sends `userText`, then `aiText` arrives
 * after `aiDelayMs`, and the composer auto-prefills `nextUserText` (or empty
 * if this is the last turn).
 */
interface GatherTurn {
  userText: string
  aiText: string
  /** Delay before the AI reply appears, after the user "sends". */
  aiDelayMs: number
  /** What the composer should auto-fill after the AI replies. */
  nextUserText?: string
}

const GATHER_SCRIPT_ZH: GatherTurn[] = [
  {
    userText:
      "你好，我想设计一个旅行商问题（TSP）的启发式算法，目标是最小化总路径长度。",
    aiText:
      "好的，我先确认两点细节：\n\n1. 距离类型：欧氏距离还是其它（如曼哈顿、网络距离）？\n2. 问题规模：大约多少个城市？",
    aiDelayMs: 700,
    nextUserText: "1. 欧氏距离\n2. 50-100 个城市",
  },
  {
    userText: "1. 欧氏距离\n2. 50-100 个城市",
    aiText:
      "明白。再确认一下评估指标 —— 除了路径长度，是否还需要考虑别的，比如运行时间、可视化输出？",
    aiDelayMs: 650,
    nextUserText: "只看路径长度即可",
  },
  {
    userText: "只看路径长度即可",
    aiText:
      "好的，我已经收集到了所有信息：\n\n• 问题：旅行商问题（TSP）\n• 距离类型：欧氏距离\n• 问题规模：50-100 个城市\n• 评估指标：路径长度\n• 设计思路：贪心最近邻构造 + 2-opt 局部搜索\n• 预计产物：config.yaml、evaluator.py、task.py\n\n确认无误的话，要现在开始构建吗？",
    aiDelayMs: 750,
    nextUserText: "好的，开始构建",
  },
  {
    userText: "好的，开始构建",
    aiText: "收到，开始生成配置和代码……",
    aiDelayMs: 400,
    // No nextUserText — sending this turn flips phase to "building".
  },
]

const GATHER_SCRIPT_EN: GatherTurn[] = [
  {
    userText:
      "Hi, I'd like to design a heuristic for the Travelling Salesman Problem (TSP) to minimize the total tour length.",
    aiText:
      "Got it. Let me confirm two details first:\n\n1. Distance type: Euclidean, or something else (Manhattan, network distance, ...)?\n2. Problem size: roughly how many cities?",
    aiDelayMs: 700,
    nextUserText: "1. Euclidean\n2. 50-100 cities",
  },
  {
    userText: "1. Euclidean\n2. 50-100 cities",
    aiText:
      "Understood. One more on evaluation — besides tour length, do you also care about runtime or any visual output?",
    aiDelayMs: 650,
    nextUserText: "Tour length is the only metric we care about.",
  },
  {
    userText: "Tour length is the only metric we care about.",
    aiText:
      "Great, I've gathered everything I need:\n\n• Problem: Travelling Salesman Problem (TSP)\n• Distance: Euclidean\n• Size: 50-100 cities\n• Metric: tour length\n• Approach: greedy nearest-neighbor construction + 2-opt local search\n• Expected files: config.yaml, evaluator.py, task.py\n\nIf that all looks right, shall we start the build?",
    aiDelayMs: 750,
    nextUserText: "Yes, start the build.",
  },
  {
    userText: "Yes, start the build.",
    aiText: "On it — generating the config and code now...",
    aiDelayMs: 400,
    // No nextUserText — sending this turn flips phase to "building".
  },
]

function gatherScript(language: string): GatherTurn[] {
  return language?.startsWith("zh") ? GATHER_SCRIPT_ZH : GATHER_SCRIPT_EN
}

interface ChatMessage {
  role: "user" | "ai" | "system"
  text: string
}

/**
 * The welcome message the real backend injects on every AI Build session
 * (`_WELCOME_TEXT` in `chat_tune_service.py`). Mirroring it here keeps the
 * demo's first-frame UX consistent with what users will see on real tasks.
 */
function welcomeMessage(language: string): ChatMessage {
  const lang = language?.startsWith("zh") ? "zh" : "en"
  if (lang === "zh") {
    return {
      role: "system",
      text:
        "👋 欢迎使用 LLM4AD AI 助手\n\n" +
        "我将帮助你配置任务参数，让算法设计更加高效。你可以：\n" +
        "• 直接描述你的需求，我来帮你生成配置\n" +
        "• 随时对现有配置提出修改建议",
    }
  }
  return {
    role: "system",
    text:
      "👋 Welcome to the LLM4AD AI Assistant\n\n" +
      "I'll help you configure task parameters for efficient algorithm design. You can:\n" +
      "• Describe your needs and I'll generate a configuration\n" +
      "• Ask for modifications to the current config at any time",
  }
}

type StageState = "not_started" | "running" | "completed"

interface StageRow {
  key: "gathering" | "build" | "review"
  state: StageState
}

/**
 * Stand-in for the real ChatTuneView (AI Build panel). Mirrors the real
 * layout — header (✨ AI title + mode switch + ✕), preview column on the
 * left (progress + 3-stage checklist + files + Run button), chat column on
 * the right — and replays a scripted requirements-gathering conversation
 * driven by the user clicking Send. Once the user sends the final "开始构建"
 * turn the panel flips into build mode (progress bar + file reveal).
 */
export default function DemoBuildView() {
  const { t, i18n } = useTranslation()
  const demoState = useDemoState()
  // Pick the conversation script for the active language. Computed inline
  // (not state) so a mid-demo language switch updates the next prompt the
  // user sees. Past chat history stays as-is — re-localizing already-sent
  // messages would be jarring.
  const SCRIPT = gatherScript(i18n.language)

  // Scripted gathering turn the user is currently on. 0..SCRIPT.length
  // — when it equals length the gathering phase is exhausted and the panel
  // moves into building.
  const [gatherStep, setGatherStep] = useState(0)
  // Visible chat history. Seeded with the same welcome system message the
  // real backend injects on every AI Build session.
  const [messages, setMessages] = useState<ChatMessage[]>(() => [
    welcomeMessage(i18n.language),
  ])
  // True while the AI's reply is being typed out — disables the Send button
  // so the user can't double-fire while a reply is in flight.
  const [chatBusy, setChatBusy] = useState(false)
  // Scroll anchor for the chat history — a ref to the bottom-most element so
  // we can pin the view to the latest message as the conversation grows.
  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  // What's currently in the composer textarea. Auto-filled with the next
  // scripted user line; cleared while the AI is busy.
  const [composer, setComposer] = useState(SCRIPT[0].userText)

  // Build animation timing (only relevant when phase === "building").
  const [phaseEnteredAt, setPhaseEnteredAt] = useState<number>(() => Date.now())
  const [, setTick] = useState(0)
  const timerRef = useRef<number | null>(null)

  // When the demo phase changes, reset the build animation clock and clean
  // up any pending typing timer.
  useEffect(() => {
    setPhaseEnteredAt(Date.now())
    if (timerRef.current) {
      window.clearTimeout(timerRef.current)
      timerRef.current = null
    }
    // configuring restart: rewind the gathering script too. building/running/
    // completed don't need to reset the script — the user has already gone
    // through it.
    if (demoState.phase === "configuring") {
      setGatherStep(0)
      setMessages([welcomeMessage(i18n.language)])
      setChatBusy(false)
      setComposer(SCRIPT[0].userText)
    }
  }, [demoState.phase])

  // Drive a 100ms tick during the build animation so progress / file reveal
  // / chat lines refresh in flight.
  useEffect(() => {
    if (demoState.phase !== "building") return
    const id = window.setInterval(() => setTick((n) => n + 1), 100)
    return () => window.clearInterval(id)
  }, [demoState.phase])

  // Auto-pin the chat scroll to the bottom whenever new content arrives —
  // either a new message lands, the AI starts/stops typing, or the build
  // phase appends its synthetic status message.
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: "end", behavior: "smooth" })
  }, [messages.length, chatBusy, demoState.phase])

  // Cleanup any pending typing timer on unmount.
  useEffect(() => {
    return () => {
      if (timerRef.current) window.clearTimeout(timerRef.current)
    }
  }, [])

  const elapsed = Date.now() - phaseEnteredAt
  const isConfiguring = demoState.phase === "configuring"
  const isBuilding = demoState.phase === "building"
  const buildDone = isBuilding && elapsed >= 2400

  // Stage rows for the preview panel — mirrors the live BUILD_STEPS state.
  const stages: StageRow[] = (() => {
    if (isConfiguring) {
      // Within configuring, gathering keeps "running" until the script is
      // exhausted. (We never sit on configuring after the script is done —
      // sending the last turn flips us into building — but be defensive.)
      return [
        {
          key: "gathering",
          state: gatherStep >= SCRIPT.length ? "completed" : "running",
        },
        { key: "build", state: "not_started" },
        { key: "review", state: "not_started" },
      ]
    }
    if (!isBuilding) {
      return [
        { key: "gathering", state: "completed" },
        { key: "build", state: "completed" },
        { key: "review", state: "completed" },
      ]
    }
    if (buildDone) {
      return [
        { key: "gathering", state: "completed" },
        { key: "build", state: "completed" },
        { key: "review", state: "completed" },
      ]
    }
    if (elapsed < 1200) {
      return [
        { key: "gathering", state: "completed" },
        { key: "build", state: "running" },
        { key: "review", state: "not_started" },
      ]
    }
    return [
      { key: "gathering", state: "completed" },
      { key: "build", state: "completed" },
      { key: "review", state: "running" },
    ]
  })()

  const completedCount = stages.filter((s) => s.state === "completed").length
  const total = stages.length
  const progressPct = (completedCount / total) * 100
  const filesVisible = isBuilding ? Math.min(3, Math.floor(elapsed / 700) + 1) : 0

  // Send the current composer text. Pushes the user message, schedules the
  // AI reply, and either pre-fills the next scripted user turn or — when the
  // last turn fires — flips the demo into the building phase.
  const handleSend = () => {
    if (!isConfiguring || chatBusy) return
    if (gatherStep >= SCRIPT.length) return
    const turn = SCRIPT[gatherStep]
    const userText = composer.trim() || turn.userText
    setMessages((m) => [...m, { role: "user", text: userText }])
    setComposer("")
    setChatBusy(true)
    timerRef.current = window.setTimeout(() => {
      setMessages((m) => [...m, { role: "ai", text: turn.aiText }])
      setChatBusy(false)
      const nextStep = gatherStep + 1
      setGatherStep(nextStep)
      if (turn.nextUserText) {
        setComposer(turn.nextUserText)
      } else {
        // Last turn — flip into the build animation.
        setComposer("")
        setDemoPhase("building")
      }
    }, turn.aiDelayMs)
  }

  const handleRun = () => {
    if (!buildDone) return
    setDemoPhase("running")
  }

  const STAGE_LABELS: Record<StageRow["key"], string> = {
    gathering: t("evolution.chatTune.buildSteps.gathering", {
      defaultValue: "需求分析",
    }),
    build: t("evolution.chatTune.buildSteps.build", {
      defaultValue: "开始构建",
    }),
    review: t("evolution.chatTune.buildSteps.review", { defaultValue: "审阅" }),
  }

  // While building, append a synthetic AI bubble so the chat doesn't go
  // silent during the 2.4s animation.
  const buildPhaseMessages: ChatMessage[] = isBuilding
    ? buildDone
      ? [
          {
            role: "ai",
            text: t("demoBuild.buildDoneMessage", {
              defaultValue:
                "构建完成，三个文件已生成。请在左侧审阅后点击「提交运行」启动进化。",
            }),
          },
        ]
      : [
          {
            role: "ai",
            text: t("demoBuild.buildingMessage", {
              defaultValue: "正在生成 config.yaml、evaluator.py、task.py……",
            }),
          },
        ]
    : []
  const visibleMessages = [...messages, ...buildPhaseMessages]

  return (
    <div className="h-full flex flex-col">
      {/* Header — mirrors ChatTuneView header */}
      <div className="shrink-0 flex items-center justify-between px-1 pb-2 border-b mb-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <span
            className="flex items-center justify-center size-7 rounded-lg shrink-0 shadow-[0_0_12px] shadow-primary/30"
            style={{
              background:
                "linear-gradient(135deg, color-mix(in srgb, var(--primary) 25%, transparent), color-mix(in srgb, #6366f1 25%, transparent))",
              border:
                "1px solid color-mix(in srgb, var(--primary) 40%, transparent)",
            }}
          >
            <Sparkles className="size-3.5 text-primary" />
          </span>
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-semibold leading-tight truncate text-foreground">
              {t("evolution.chatTune.headerTitle", {
                defaultValue: "AI 构建",
              })}
            </span>
            <span className="text-[11px] text-muted-foreground leading-tight truncate">
              {t("evolution.chatTune.headerHint", {
                defaultValue: "用对话方式让 AI 帮你完成需求分析与配置构建",
              })}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Mode switch — visual only in demo, AI is selected */}
          <div
            role="tablist"
            className="inline-flex items-center gap-0.5 p-0.5 rounded-md border border-primary/40 bg-primary/5 shadow-sm"
          >
            <button
              type="button"
              role="tab"
              aria-selected="true"
              className="flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-primary text-primary-foreground shadow-sm"
            >
              <Sparkles className="size-3.5" />
              <span>
                {t("evolution.chatTune.modeAi", { defaultValue: "AI 构建" })}
              </span>
            </button>
            <button
              type="button"
              role="tab"
              aria-selected="false"
              disabled
              className="flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium text-muted-foreground/60 cursor-not-allowed"
            >
              <Layers className="size-3.5" />
              <span>
                {t("evolution.chatTune.modeManual", {
                  defaultValue: "手动配置",
                })}
              </span>
            </button>
          </div>
          {/* Close icon — visual only */}
          <button
            type="button"
            disabled
            className="p-1.5 rounded-md text-muted-foreground/40 cursor-not-allowed"
          >
            <X className="size-4" />
          </button>
        </div>
      </div>

      {/* Body: preview (left, 1/3) + chat (right, 2/3) */}
      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)] gap-4">
        {/* Preview column */}
        <div
          data-tour="ai-preview"
          className="min-h-0 flex flex-col rounded-xl border border-border/60 bg-card/70 overflow-hidden"
        >
          {/* Build status: progress + stages + files. Tour spotlights this
              block during the building phase so the highlight doesn't bleed
              into the Run footer below. */}
          <div
            data-tour="ai-preview-body"
            className="flex-1 min-h-0 flex flex-col"
          >
          {/* Progress bar */}
          <div className="shrink-0 px-4 py-3 border-b border-border/50 bg-muted/30">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {t("evolution.chatTune.preview.progress", {
                  defaultValue: "配置进度",
                })}
              </span>
              <span className="text-xs font-semibold text-foreground">
                {completedCount} / {total}
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full bg-linear-to-r from-primary to-emerald-400 transition-[width] duration-300"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>

          {/* Stage checklist */}
          <div className="shrink-0 px-4 py-3 border-b border-border/50">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              {t("evolution.chatTune.preview.stages", {
                defaultValue: "阶段",
              })}
            </p>
            <ul className="space-y-1">
              {stages.map(({ key, state }) => {
                const isActive = state === "running"
                return (
                  <li
                    key={key}
                    className={cn(
                      "flex items-center gap-2 px-2 py-1.5 rounded-md text-sm transition-colors",
                      isActive
                        ? "bg-primary/10 text-primary"
                        : state === "completed"
                          ? "text-foreground"
                          : "text-muted-foreground",
                    )}
                  >
                    <span className="shrink-0 size-4 flex items-center justify-center">
                      {state === "completed" ? (
                        <Check className="size-3.5 text-emerald-500" />
                      ) : isActive ? (
                        <Loader2 className="size-3.5 animate-spin" />
                      ) : (
                        <span className="size-2 rounded-full bg-muted-foreground/30" />
                      )}
                    </span>
                    <span className="flex-1 truncate">{STAGE_LABELS[key]}</span>
                    {isActive && (
                      <span className="text-[10px] uppercase tracking-wider opacity-70">
                        {t("evolution.chatTune.buildStepRunning", {
                          defaultValue: "进行中",
                        })}
                      </span>
                    )}
                  </li>
                )
              })}
            </ul>
          </div>

          {/* Files */}
          <div className="flex-1 min-h-0 overflow-y-auto px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              {t("evolution.chatTune.preview.files", {
                defaultValue: "文件列表",
              })}
            </p>
            {filesVisible === 0 ? (
              <div className="text-xs text-muted-foreground/60 italic">
                {t("demoBuild.noFilesYet", {
                  defaultValue: "AI 完成构建后，生成的文件会在这里出现",
                })}
              </div>
            ) : (
              <div className="space-y-1.5">
                {DEMO_AI_BUILD_FILES.map((file, idx) => {
                  const visible = idx < filesVisible
                  return (
                    <div
                      key={file.name}
                      className={cn(
                        "flex items-center gap-2 px-2 py-1.5 rounded-md border text-sm transition-all duration-300",
                        visible
                          ? "border-primary/30 bg-primary/5 opacity-100 translate-y-0"
                          : "border-border/30 bg-transparent opacity-0 translate-y-1 pointer-events-none",
                      )}
                    >
                      <FileCode className="size-3.5 text-primary shrink-0" />
                      <span className="font-mono text-xs truncate flex-1">
                        {file.name}
                      </span>
                      <span className="text-[10px] uppercase tracking-wider text-muted-foreground shrink-0">
                        {file.language}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
          </div>

          {/* Run button — bottom border-t */}
          <div
            data-tour="ai-run"
            className="shrink-0 px-3 py-2.5 border-t border-border/50 space-y-2"
          >
            {!buildDone && (
              <div className="flex items-center gap-1.5 px-2 py-1.5 rounded-md text-[11px] bg-muted/60 border border-border/50 text-muted-foreground">
                <CircleAlert className="size-3 shrink-0" />
                <span>
                  {t("evolution.chatTune.runHintNeedBuild", {
                    defaultValue: "完成 AI 构建后即可提交运行",
                  })}
                </span>
              </div>
            )}
            <button
              type="button"
              onClick={handleRun}
              disabled={!buildDone}
              className={cn(
                "w-full inline-flex items-center justify-center gap-1.5 h-9 px-4 rounded-md text-sm font-medium transition-all",
                buildDone
                  ? "bg-primary text-primary-foreground shadow-md hover:shadow-lg"
                  : "bg-primary/30 text-primary-foreground/60 cursor-not-allowed",
              )}
            >
              <Play className="size-3.5" />
              {t("evolution.confirmStep.submitRun", {
                defaultValue: "提交运行",
              })}
            </button>
          </div>
        </div>

        {/* Chat column */}
        <div
          data-tour="ai-chat-panel"
          className="min-h-0 flex flex-col rounded-xl border border-border/60 bg-card/70 overflow-hidden"
        >
          {/* Messages */}
          <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-3">
            {visibleMessages.map((msg, idx) => {
              if (msg.role === "system") {
                return (
                  <div
                    key={idx}
                    className="flex gap-2 animate-in fade-in slide-in-from-bottom-1 duration-200"
                  >
                    <div className="shrink-0 flex items-center justify-center size-7 rounded-lg bg-muted border border-border/50">
                      <Monitor className="size-3.5 text-muted-foreground" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="rounded-2xl rounded-tl-sm border border-dashed border-muted-foreground/30 bg-muted/40 px-3.5 py-2 text-sm leading-relaxed text-muted-foreground whitespace-pre-wrap">
                        {msg.text}
                      </div>
                    </div>
                    <div className="shrink-0 size-7 invisible" />
                  </div>
                )
              }
              const isUser = msg.role === "user"
              return (
                <div
                  key={idx}
                  className="flex gap-2 animate-in fade-in slide-in-from-bottom-1 duration-200"
                >
                  {/* AI avatar (left) — placeholder for user to keep alignment */}
                  <div
                    className={cn(
                      "shrink-0 size-7 rounded-lg",
                      isUser && "invisible",
                    )}
                  >
                    {!isUser && (
                      <div className="size-full flex items-center justify-center bg-primary/10 border border-primary/20 rounded-lg">
                        <Bot className="size-3.5 text-primary" />
                      </div>
                    )}
                  </div>
                  <div className="min-w-0 flex-1 flex flex-col gap-2">
                    <div
                      className={cn(
                        "rounded-2xl px-3.5 py-2 text-sm leading-relaxed shadow-sm min-w-0 [overflow-wrap:anywhere]",
                        isUser
                          ? "bg-primary text-primary-foreground rounded-tr-sm whitespace-pre-wrap self-end max-w-[85%]"
                          : "bg-gradient-to-br from-muted to-muted/60 border border-border/50 text-foreground rounded-tl-sm whitespace-pre-wrap min-h-[44px] flex flex-col justify-center max-w-[90%]",
                      )}
                    >
                      {msg.text}
                    </div>
                  </div>
                </div>
              )
            })}
            {chatBusy && (
              <div className="flex gap-2 animate-in fade-in slide-in-from-bottom-1 duration-200">
                <div className="shrink-0 size-7 rounded-lg flex items-center justify-center bg-primary/10 border border-primary/20">
                  <Bot className="size-3.5 text-primary" />
                </div>
                <div className="rounded-2xl rounded-tl-sm bg-gradient-to-br from-muted to-muted/60 border border-border/50 px-3.5 py-2.5">
                  <span className="inline-flex gap-1">
                    <span className="size-1.5 rounded-full bg-current animate-bounce" />
                    <span
                      className="size-1.5 rounded-full bg-current animate-bounce"
                      style={{ animationDelay: "0.15s" }}
                    />
                    <span
                      className="size-1.5 rounded-full bg-current animate-bounce"
                      style={{ animationDelay: "0.3s" }}
                    />
                  </span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Composer — mirrors the real textarea + send button */}
          <div className="shrink-0 px-3 pb-3 pt-2">
            <div
              data-tour="ai-composer"
              className={cn(
                "relative rounded-2xl border-2 backdrop-blur-md transition-all duration-200",
                isConfiguring && !chatBusy
                  ? "shadow-lg shadow-primary/8 border-primary/20 bg-card/95"
                  : "border-border/20 bg-card/80 opacity-60",
              )}
            >
              <div className="px-4 pt-3 pb-1">
                <textarea
                  value={composer}
                  onChange={(e) => setComposer(e.target.value)}
                  placeholder={
                    chatBusy
                      ? t("evolution.chatTune.composerGenerating", {
                          defaultValue: "AI 正在回复，请稍候...",
                        })
                      : t("evolution.chatTune.composerActive", {
                          defaultValue: "用对话告诉 AI 你的需求...",
                        })
                  }
                  className="w-full resize-none border-0 bg-transparent text-sm leading-relaxed placeholder:text-muted-foreground/60 focus:outline-none min-h-[40px]"
                  disabled={!isConfiguring || chatBusy}
                />
              </div>
              <div className="flex items-center justify-between px-3 pb-2.5">
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    disabled
                    className="size-7 flex items-center justify-center rounded-lg text-muted-foreground/50 cursor-not-allowed"
                  >
                    <ChevronsUpDown className="size-3.5" />
                  </button>
                </div>
                <button
                  type="button"
                  data-tour="ai-send"
                  onClick={handleSend}
                  disabled={!isConfiguring || chatBusy || !composer.trim()}
                  className={cn(
                    "inline-flex items-center gap-1.5 h-8 px-4 rounded-xl text-xs font-medium transition-all duration-200",
                    isConfiguring && !chatBusy && composer.trim()
                      ? "bg-primary text-primary-foreground shadow-md shadow-primary/25 hover:shadow-lg"
                      : "bg-primary/10 text-primary/40 cursor-not-allowed",
                  )}
                >
                  <Send className="size-3.5" />
                  <span>
                    {t("evolution.chatTune.send", { defaultValue: "发送" })}
                  </span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
