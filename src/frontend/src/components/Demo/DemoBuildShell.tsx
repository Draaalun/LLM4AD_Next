import {
  Bot,
  ChevronsUpDown,
  CircleAlert,
  FolderOpen,
  Layers,
  Monitor,
  Play,
  Send,
  Sparkles,
  X,
} from "lucide-react"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"

import { useTypewriter } from "@/components/Demo/useTypewriter"
import FileTreeView from "@/components/Evolution/TaskDetail/steps/FileTreeView"
import { DEMO_AI_BUILD_FILES, DEMO_FILE_TREE } from "@/data/demoFixtures"
import { setDemoPhase, useDemoState } from "@/hooks/useDemoMode"
import { cn } from "@/lib/utils"

/**
 * Center pane during the AI Build phases (configuring → building).
 *
 * Keeps the visual structure of the real `ChatTuneView` (header with mode
 * switcher, ✨ left preview / right chat split, composer at the bottom) but
 * swaps every API-bound subsystem for fixture data:
 *   - file tree → real `FileTreeView` fed `DEMO_FILE_TREE`
 *   - composer → bound to `useTypewriter` so each turn types out char-by-char
 *   - submit → flips demo phase, no `runTask` call
 *
 * The chat history is preserved across phase transitions (configuring →
 * building → running) so the user always sees the conversation that led to
 * the current state.
 */

interface ScriptedTurn {
  userText: string
  aiText: string
  /** Delay before the AI reply lands after the user "sends". */
  aiDelayMs: number
  /** Pre-fill for the next user turn. Last turn omits this and flips phase. */
  nextUserText?: string
}

const GATHER_SCRIPT_ZH: ScriptedTurn[] = [
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
  },
]

const GATHER_SCRIPT_EN: ScriptedTurn[] = [
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
  },
]

interface ChatMessage {
  role: "user" | "ai" | "system"
  text: string
}

function welcomeMessage(language: string): ChatMessage {
  if (language?.startsWith("zh")) {
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

export default function DemoBuildShell() {
  const { t, i18n } = useTranslation()
  const demoState = useDemoState()
  const SCRIPT = i18n.language?.startsWith("zh")
    ? GATHER_SCRIPT_ZH
    : GATHER_SCRIPT_EN

  const [gatherStep, setGatherStep] = useState(0)
  const [messages, setMessages] = useState<ChatMessage[]>(() => [
    welcomeMessage(i18n.language),
  ])
  const [chatBusy, setChatBusy] = useState(false)
  const [phaseEnteredAt, setPhaseEnteredAt] = useState<number>(() => Date.now())
  const [, setTick] = useState(0)
  const replyTimerRef = useRef<number | null>(null)
  const messagesEndRef = useRef<HTMLDivElement | null>(null)

  // Reset the build animation clock + the gather script when phase changes.
  useEffect(() => {
    setPhaseEnteredAt(Date.now())
    if (replyTimerRef.current) {
      window.clearTimeout(replyTimerRef.current)
      replyTimerRef.current = null
    }
    if (demoState.phase === "configuring") {
      setGatherStep(0)
      setMessages([welcomeMessage(i18n.language)])
      setChatBusy(false)
    }
  }, [demoState.phase, i18n.language])

  // 100ms tick during the build animation so progress / files refresh.
  useEffect(() => {
    if (demoState.phase !== "building") return
    const id = window.setInterval(() => setTick((n) => n + 1), 100)
    return () => window.clearInterval(id)
  }, [demoState.phase])

  // Auto-scroll the chat to the bottom whenever new content arrives.
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: "end", behavior: "smooth" })
  }, [messages.length, chatBusy, demoState.phase])

  // Cleanup pending reply timer on unmount.
  useEffect(
    () => () => {
      if (replyTimerRef.current) window.clearTimeout(replyTimerRef.current)
    },
    [],
  )

  const elapsed = Date.now() - phaseEnteredAt
  const isConfiguring = demoState.phase === "configuring"
  const isBuilding = demoState.phase === "building"
  const buildDone = isBuilding && elapsed >= 2400

  const stages: StageRow[] = useMemo(() => {
    if (isConfiguring) {
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
  }, [SCRIPT.length, buildDone, elapsed, gatherStep, isBuilding, isConfiguring])

  const completedCount = stages.filter((s) => s.state === "completed").length
  const total = stages.length
  const progressPct = (completedCount / total) * 100
  const filesVisible = isBuilding ? Math.min(3, Math.floor(elapsed / 700) + 1) : 0

  // Composer state — bound to the typewriter for the current turn's prefill.
  // When chatBusy is true the composer isn't typing (the AI is); when
  // gatherStep >= SCRIPT.length there's nothing left to prefill either.
  const currentPrefill =
    chatBusy || gatherStep >= SCRIPT.length
      ? ""
      : (SCRIPT[gatherStep]?.userText ?? "")
  const typewriter = useTypewriter(currentPrefill)

  const handleSend = useCallback(() => {
    if (!isConfiguring || chatBusy) return
    if (gatherStep >= SCRIPT.length) return
    if (typewriter.isTyping) return
    if (!typewriter.text.trim()) return

    const turn = SCRIPT[gatherStep]
    const userText = typewriter.text.trim() || turn.userText
    setMessages((m) => [...m, { role: "user", text: userText }])
    setChatBusy(true)
    replyTimerRef.current = window.setTimeout(() => {
      setMessages((m) => [...m, { role: "ai", text: turn.aiText }])
      setChatBusy(false)
      const nextStep = gatherStep + 1
      setGatherStep(nextStep)
      if (!turn.nextUserText) {
        // Last turn — flip into the build animation phase.
        setDemoPhase("building")
      }
    }, turn.aiDelayMs)
  }, [SCRIPT, chatBusy, gatherStep, isConfiguring, typewriter])

  const handleRun = useCallback(() => {
    if (!buildDone) return
    setDemoPhase("running")
  }, [buildDone])

  const STAGE_LABELS: Record<StageRow["key"], string> = {
    gathering: t("evolution.chatTune.buildSteps.gathering", {
      defaultValue: "Gathering",
    }),
    build: t("evolution.chatTune.buildSteps.build", { defaultValue: "Build" }),
    review: t("evolution.chatTune.buildSteps.review", {
      defaultValue: "Review",
    }),
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
                "Build complete — three files are ready. Review them on the left, then click Submit & Run to kick off the evolution.",
            }),
          },
        ]
      : [
          {
            role: "ai",
            text: t("demoBuild.buildingMessage", {
              defaultValue: "Generating config.yaml, evaluator.py, task.py...",
            }),
          },
        ]
    : []
  const visibleMessages = [...messages, ...buildPhaseMessages]

  // FileTreeView consumes the `tree` prop directly — no internal fetching.
  // We expose a no-op selection handler since the user can't open files in
  // the demo.
  const noopSelect = useCallback(() => {}, [])
  // Reference unused fixture to keep the import alive (display elsewhere).
  void DEMO_AI_BUILD_FILES

  return (
    <div className="h-full flex flex-col">
      {/* Header — mirrors the real ChatTuneView header */}
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
                defaultValue: "AI Assistant",
              })}
            </span>
            <span className="text-[11px] text-muted-foreground leading-tight truncate">
              {t("evolution.chatTune.headerHint", {
                defaultValue:
                  "Configure parameters quickly through conversation",
              })}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
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
                {t("evolution.chatTune.modeAi", { defaultValue: "AI Build" })}
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
                  defaultValue: "Manual Build",
                })}
              </span>
            </button>
          </div>
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
          <div
            data-tour="ai-preview-body"
            className="flex-1 min-h-0 flex flex-col"
          >
            <div className="shrink-0 px-4 py-3 border-b border-border/50 bg-muted/30">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {t("evolution.chatTune.preview.progress", {
                    defaultValue: "Progress",
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

            <div className="shrink-0 px-4 py-3 border-b border-border/50">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                {t("evolution.chatTune.preview.stages", {
                  defaultValue: "Stages",
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
                          <span className="size-2 rounded-full bg-emerald-500" />
                        ) : isActive ? (
                          <span className="size-2 rounded-full bg-primary animate-pulse" />
                        ) : (
                          <span className="size-2 rounded-full bg-muted-foreground/30" />
                        )}
                      </span>
                      <span className="flex-1 truncate">{STAGE_LABELS[key]}</span>
                      {isActive && (
                        <span className="text-[10px] uppercase tracking-wider opacity-70">
                          {t("evolution.chatTune.buildStepRunning", {
                            defaultValue: "Running",
                          })}
                        </span>
                      )}
                    </li>
                  )
                })}
              </ul>
            </div>

            <div className="flex-1 min-h-0 overflow-y-auto px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2 flex items-center gap-1.5">
                <FolderOpen className="size-3.5" />
                {t("evolution.chatTune.preview.files", {
                  defaultValue: "Files",
                })}
              </p>
              {filesVisible === 0 ? (
                <div className="text-xs text-muted-foreground/60 italic">
                  {t("demoBuild.noFilesYet", {
                    defaultValue:
                      "Generated files will appear here once the AI finishes building.",
                  })}
                </div>
              ) : (
                <FileTreeView
                  tree={DEMO_FILE_TREE.slice(0, filesVisible >= 2 ? 2 : 1)}
                  selectedPath={null}
                  onSelectFile={noopSelect}
                />
              )}
            </div>
          </div>

          <div
            data-tour="ai-run"
            className="shrink-0 px-3 py-2.5 border-t border-border/50 space-y-2"
          >
            {!buildDone && (
              <div className="flex items-center gap-1.5 px-2 py-1.5 rounded-md text-[11px] bg-muted/60 border border-border/50 text-muted-foreground">
                <CircleAlert className="size-3 shrink-0" />
                <span>
                  {t("evolution.chatTune.runHintNeedBuild", {
                    defaultValue: "Submit run after the AI build completes",
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
                defaultValue: "Submit & Run",
              })}
            </button>
          </div>
        </div>

        {/* Chat column */}
        <div
          data-tour="ai-chat-panel"
          className="min-h-0 flex flex-col rounded-xl border border-border/60 bg-card/70 overflow-hidden"
        >
          <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-3">
            {visibleMessages.map((msg, idx) => {
              if (msg.role === "system") {
                return (
                  <div
                    // biome-ignore lint/suspicious/noArrayIndexKey: chat is append-only and immutable
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
                  </div>
                )
              }
              const isUser = msg.role === "user"
              return (
                <div
                  // biome-ignore lint/suspicious/noArrayIndexKey: chat is append-only and immutable
                  key={idx}
                  className="flex gap-2 animate-in fade-in slide-in-from-bottom-1 duration-200"
                >
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

          {/* Composer */}
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
                  value={typewriter.text}
                  readOnly
                  onClick={typewriter.skip}
                  placeholder={
                    chatBusy
                      ? t("evolution.chatTune.composerGenerating", {
                          defaultValue: "AI is generating a response...",
                        })
                      : t("evolution.chatTune.composerActive", {
                          defaultValue:
                            "Tell AI your needs through conversation...",
                        })
                  }
                  className="w-full resize-none border-0 bg-transparent text-sm leading-relaxed placeholder:text-muted-foreground/60 focus:outline-none min-h-[40px] cursor-default"
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
                  disabled={
                    !isConfiguring ||
                    chatBusy ||
                    typewriter.isTyping ||
                    !typewriter.text.trim()
                  }
                  className={cn(
                    "inline-flex items-center gap-1.5 h-8 px-4 rounded-xl text-xs font-medium transition-all duration-200",
                    isConfiguring &&
                      !chatBusy &&
                      !typewriter.isTyping &&
                      typewriter.text.trim()
                      ? "bg-primary text-primary-foreground shadow-md shadow-primary/25 hover:shadow-lg"
                      : "bg-primary/10 text-primary/40 cursor-not-allowed",
                  )}
                >
                  <Send className="size-3.5" />
                  <span>
                    {t("evolution.chatTune.send", { defaultValue: "Send" })}
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
