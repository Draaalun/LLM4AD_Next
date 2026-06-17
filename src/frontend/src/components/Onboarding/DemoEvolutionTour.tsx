import { useNavigate } from "@tanstack/react-router"
import { useEffect, useMemo, useRef, useState } from "react"
import { createPortal } from "react-dom"
import { useTranslation } from "react-i18next"
import type { DemoPhase } from "@/hooks/useDemoMode"
import { setDemoPhase, useDemoState } from "@/hooks/useDemoMode"
import { useEvolution } from "@/hooks/useEvolution"

/**
 * Phase-driven walkthrough for the demo project. Unlike the generic
 * OnboardingTour which advances on click, this overlay tracks the demo phase
 * and follows the user as they perform real interactions (create the task,
 * send, run). The Next button is offered as an escape hatch when the user
 * just wants the simulation to keep moving without clicking the underlying
 * controls.
 */

interface Step {
  /** CSS selector for the highlighted element. */
  selector: string
  /** Phase this step belongs to. */
  phase: DemoPhase
  /** i18n key for the title. */
  titleKey: string
  /** i18n key for the body. */
  contentKey: string
  /** Default text if i18n key is missing. */
  titleFallback: string
  /** Default body if i18n key is missing. */
  contentFallback: string
  /** Where to place the tooltip relative to the spotlight. */
  placement?: "top" | "bottom" | "left" | "right"
  /**
   * If true, this step has no underlying button — the user advances by
   * clicking an "I see" button on the tooltip itself. When the step is the
   * LAST one in its phase, clicking the button instead transitions the demo
   * to `manualNextPhase`.
   */
  manualNext?: boolean
  /**
   * When `manualNext` is true and this is the last step in the phase, advance
   * to this phase on click instead of stepping within the current phase.
   */
  manualNextPhase?: DemoPhase
  /**
   * If true, automatically advance to this step the moment its anchor element
   * mounts in the DOM. Use it for steps that are gated by a UI surface
   * appearing (e.g. opening a dialog) rather than by the user clicking a
   * specific button.
   */
  autoAdvanceOnAnchor?: boolean
  /**
   * Optional inner element to highlight with a secondary pulse ring inside
   * the main spotlight — used to point the user at the specific button
   * (e.g. 创建, 发送) within a larger highlighted region (the dialog, the
   * chat panel) without occluding the surrounding context.
   */
  pulseSelector?: string
}

const STEPS: Step[] = [
  {
    phase: "uninitialized",
    selector: '[data-tour="new-task-btn"]',
    titleKey: "demoTour.create.title",
    contentKey: "demoTour.create.content",
    titleFallback: "Step 1 · Open the new-task dialog",
    contentFallback:
      "Click 新建任务 to open the create-task dialog. We'll walk through choosing AI build and naming the task next.",
    placement: "bottom",
  },
  {
    phase: "uninitialized",
    selector: '[data-tour="create-task-dialog"]',
    titleKey: "demoTour.createSubmit.title",
    contentKey: "demoTour.createSubmit.content",
    titleFallback: "Step 1b · Pick AI build and create",
    contentFallback:
      "AI 构建 is already selected for this demo. The task name is pre-filled — click 创建 to start the simulated AI-build session.",
    placement: "right",
    autoAdvanceOnAnchor: true,
    // Inner pulse ring on the 创建 button so the user knows to click it.
    pulseSelector: '[data-tour="create-task-submit"]',
  },
  {
    phase: "configuring",
    selector: '[data-tour="demo-task-row"]',
    titleKey: "demoTour.taskRow.title",
    contentKey: "demoTour.taskRow.content",
    titleFallback: "Step 2 · Your task is in the sidebar",
    contentFallback:
      "The task you just created shows up in the left task list. Real projects can have many tasks here — click any row to switch between them.",
    placement: "right",
    manualNext: true,
  },
  {
    phase: "configuring",
    selector: '[data-tour="ai-chat-panel"]',
    titleKey: "demoTour.send.title",
    contentKey: "demoTour.send.content",
    titleFallback: "Step 3 · Chat with the AI",
    contentFallback:
      "The AI greets you in the composer. Click 发送 to send each turn — the AI will gather requirements, then ask if you want to start building. The build kicks off after you send 「开始构建」.",
    placement: "left",
    // Pulse the Send button so the user knows what to click without occluding
    // the surrounding chat history.
    pulseSelector: '[data-tour="ai-send"]',
  },
  {
    phase: "building",
    selector: '[data-tour="ai-preview-body"]',
    titleKey: "demoTour.building.title",
    contentKey: "demoTour.building.content",
    titleFallback: "Step 3 · Watch the AI work",
    contentFallback:
      "The left panel shows the build pipeline: 配置进度 fills as the AI moves through 需求分析 → 开始构建 → 审阅. Generated files appear in 文件列表 below.",
    placement: "right",
    manualNext: true,
  },
  {
    phase: "building",
    selector: '[data-tour="ai-run"]',
    titleKey: "demoTour.run.title",
    contentKey: "demoTour.run.content",
    titleFallback: "Step 4 · Submit the run",
    contentFallback:
      "Build is done. Click 提交运行 at the bottom of the left panel to start the evolution loop — candidates appear one generation at a time.",
    placement: "top",
  },
  {
    phase: "running",
    selector: '[data-tour="result-canvas"]',
    titleKey: "demoTour.canvas.title",
    contentKey: "demoTour.canvas.content",
    titleFallback: "Step 5 · The evolution graph",
    contentFallback:
      "Each node is one candidate. Edges connect a candidate to its parents; color encodes the score. Watch as the graph fills in.",
    placement: "right",
    // No real button to click here either — let the user dismiss when ready.
    manualNext: true,
    manualNextPhase: "completed",
  },
  {
    phase: "completed",
    selector: '[data-tour="demo-best-summary"]',
    titleKey: "demoTour.ide.title",
    contentKey: "demoTour.ide.content",
    titleFallback: "Step 7 · Read the final algorithm",
    contentFallback:
      "Click the IDE tab to read the algorithm LLM4AD synthesized — in a real run this is the code you'd copy into your project.",
    // bottom keeps the tooltip clear of the IDE button itself.
    placement: "bottom",
    // No "Got it" here — the user has to actually click the IDE tab to
    // proceed. The activeTab listener jumps the tour to the next sub-step on
    // the transition into "ide".
  },
  {
    phase: "completed",
    selector: '[data-tour="demo-ide-code"]',
    titleKey: "demoTour.ideCode.title",
    contentKey: "demoTour.ideCode.content",
    titleFallback: "Step 8 · Read the generated code",
    contentFallback:
      "This is the algorithm LLM4AD evolved — a greedy nearest-neighbor with 2-opt refinement. Skim through it, then click 了解 to wrap up.",
    placement: "left",
    manualNext: true,
  },
  {
    phase: "completed",
    selector: '[data-tour="demo-exit"]',
    titleKey: "demoTour.exit.title",
    contentKey: "demoTour.exit.content",
    titleFallback: "You're ready",
    contentFallback:
      "Head back to the project list, configure an LLM provider, and create your first real project. The walkthrough is always one click away from your user menu.",
    placement: "bottom",
  },
]

const PHASE_ORDER: DemoPhase[] = [
  "uninitialized",
  "configuring",
  "building",
  "running",
  "completed",
]

const PADDING = 6
const TOOLTIP_WIDTH = 340
const TOOLTIP_GAP = 12
const VIEWPORT_MARGIN = 12

interface Rect {
  top: number
  left: number
  width: number
  height: number
}

function getRect(el: Element): Rect {
  const r = el.getBoundingClientRect()
  return { top: r.top, left: r.left, width: r.width, height: r.height }
}

function placeTooltip(
  rect: Rect,
  preferred: Step["placement"],
  tooltipHeight: number,
): { top: number; left: number } {
  const vw = window.innerWidth
  const vh = window.innerHeight
  let top = 0
  let left = 0
  switch (preferred ?? "bottom") {
    case "top":
      top = rect.top - TOOLTIP_GAP - tooltipHeight
      left = rect.left + rect.width / 2 - TOOLTIP_WIDTH / 2
      break
    case "bottom":
      top = rect.top + rect.height + TOOLTIP_GAP
      left = rect.left + rect.width / 2 - TOOLTIP_WIDTH / 2
      break
    case "left":
      top = rect.top + rect.height / 2 - tooltipHeight / 2
      left = rect.left - TOOLTIP_GAP - TOOLTIP_WIDTH
      break
    case "right":
      top = rect.top + rect.height / 2 - tooltipHeight / 2
      left = rect.left + rect.width + TOOLTIP_GAP
      break
  }
  left = Math.max(
    VIEWPORT_MARGIN,
    Math.min(left, vw - TOOLTIP_WIDTH - VIEWPORT_MARGIN),
  )
  top = Math.max(
    VIEWPORT_MARGIN,
    Math.min(top, vh - tooltipHeight - VIEWPORT_MARGIN),
  )
  return { top, left }
}

export default function DemoEvolutionTour() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const demoState = useDemoState()
  const { activeTab } = useEvolution()
  // Within a phase that has multiple steps (building has 2), track which one
  // is active. Reset whenever the phase changes.
  const [subStepIdx, setSubStepIdx] = useState(0)
  const [rect, setRect] = useState<Rect | null>(null)
  // Optional inner pulse ring rect (e.g. the Send button inside the chat
  // panel) — kept separate from the main spotlight rect so the two can move
  // independently as the underlying layout shifts.
  const [pulseRect, setPulseRect] = useState<Rect | null>(null)
  const [tooltipHeight, setTooltipHeight] = useState(180)
  const [tooltipPos, setTooltipPos] = useState<{ top: number; left: number }>({
    top: 0,
    left: 0,
  })
  const tooltipRef = useRef<HTMLDivElement | null>(null)

  // Reset sub-step index whenever the demo phase changes — every phase opens
  // on its first matching step. Also flush the spotlight rect so we don't
  // briefly render against an anchor that just unmounted (e.g. the create-task
  // dialog after the user clicked 创建).
  // biome-ignore lint/correctness/useExhaustiveDependencies: only re-fire on phase change
  useEffect(() => {
    setSubStepIdx(0)
    setRect(null)
    setPulseRect(null)
  }, [demoState.phase])

  // The IDE step has no "Got it" button — it advances when the user actually
  // clicks the IDE tab. Track previous activeTab so we only fire on the
  // transition into "ide", otherwise hitting Back to the IDE step would
  // immediately bounce forward again because activeTab is still "ide".
  const prevTabRef = useRef<string | null>(null)
  useEffect(() => {
    const prev = prevTabRef.current
    prevTabRef.current = activeTab
    if (demoState.phase !== "completed") return
    if (subStepIdx !== 0) return
    if (prev !== "ide" && activeTab === "ide") {
      setSubStepIdx(1)
    }
  }, [demoState.phase, subStepIdx, activeTab])

  // Auto-advance to the next sub-step when its anchor appears in the DOM —
  // but only when that step opted in via `autoAdvanceOnAnchor`. This is how
  // opening the New Task dialog hops the tour onto its create-task-submit
  // anchor without requiring a manual click.
  useEffect(() => {
    const matching = STEPS.filter((s) => s.phase === demoState.phase)
    const next = matching[subStepIdx + 1]
    if (!next?.autoAdvanceOnAnchor) return
    let cancelled = false
    const tick = () => {
      if (cancelled) return
      const el = document.querySelector(next.selector) as HTMLElement | null
      if (el) {
        const r = el.getBoundingClientRect()
        if (r.width > 0 && r.height > 0) {
          setSubStepIdx((i) => i + 1)
          return
        }
      }
      window.setTimeout(tick, 200)
    }
    const id = window.setTimeout(tick, 200)
    return () => {
      cancelled = true
      window.clearTimeout(id)
    }
  }, [demoState.phase, subStepIdx])

  const currentStep = useMemo(() => {
    const matching = STEPS.filter((s) => s.phase === demoState.phase)
    const idx = Math.min(subStepIdx, matching.length - 1)
    return matching[idx] ?? null
  }, [demoState.phase, subStepIdx])

  // Locate the highlighted element. Retry a few times because some anchors
  // mount only after a phase transition (e.g. result-canvas after running).
  useEffect(() => {
    if (!currentStep) return
    // Clear the previous spotlight rect immediately so the overlay doesn't
    // render against a stale (or zero-sized post-unmount) bounding box while
    // the new anchor is still mounting — that's what produced the "tooltip
    // glued to the top-left corner" symptom when the user used Skip ahead.
    setRect(null)
    let cancelled = false
    let attempts = 0
    const tick = () => {
      if (cancelled) return
      const el = document.querySelector(currentStep.selector)
      if (el) {
        const r = getRect(el)
        // Reject zero-sized rects — the element exists but is detached or
        // not laid out yet. Keep retrying until it has real geometry.
        if (r.width > 0 && r.height > 0) {
          setRect(r)
          return
        }
      }
      attempts += 1
      if (attempts < 40) window.setTimeout(tick, 100)
    }
    tick()
    const onUpdate = () => {
      const el = document.querySelector(currentStep.selector)
      if (!el) return
      const r = getRect(el)
      if (r.width > 0 && r.height > 0) setRect(r)
    }
    // Poll for anchor disappearance — dialogs that close don't fire scroll/
    // resize, but their anchor is gone afterwards. If the element vanishes,
    // clear the rect so the stale spotlight doesn't linger over empty space.
    const presenceCheck = window.setInterval(() => {
      const el = document.querySelector(currentStep.selector)
      if (!el) {
        setRect(null)
        return
      }
      const r = getRect(el)
      if (r.width === 0 || r.height === 0) setRect(null)
    }, 250)
    window.addEventListener("resize", onUpdate)
    window.addEventListener("scroll", onUpdate, true)
    return () => {
      cancelled = true
      window.clearInterval(presenceCheck)
      window.removeEventListener("resize", onUpdate)
      window.removeEventListener("scroll", onUpdate, true)
    }
  }, [currentStep])

  // Track the optional inner pulse target. Mirrors the main locator but for
  // pulseSelector — runs independently so the inner ring can settle even
  // after the outer rect is already on-screen.
  useEffect(() => {
    setPulseRect(null)
    if (!currentStep?.pulseSelector) return
    const sel = currentStep.pulseSelector
    let cancelled = false
    let attempts = 0
    const tick = () => {
      if (cancelled) return
      const el = document.querySelector(sel)
      if (el) {
        const r = getRect(el)
        if (r.width > 0 && r.height > 0) {
          setPulseRect(r)
          return
        }
      }
      attempts += 1
      if (attempts < 40) window.setTimeout(tick, 100)
    }
    tick()
    const onUpdate = () => {
      const el = document.querySelector(sel)
      if (!el) return
      const r = getRect(el)
      if (r.width > 0 && r.height > 0) setPulseRect(r)
    }
    window.addEventListener("resize", onUpdate)
    window.addEventListener("scroll", onUpdate, true)
    return () => {
      cancelled = true
      window.removeEventListener("resize", onUpdate)
      window.removeEventListener("scroll", onUpdate, true)
    }
  }, [currentStep])

  // Recompute tooltip position whenever the spotlight rect or tooltip size
  // changes (the latter happens once on first paint after measurement).
  useEffect(() => {
    if (!rect || !currentStep) return
    setTooltipPos(placeTooltip(rect, currentStep.placement, tooltipHeight))
  }, [rect, currentStep, tooltipHeight])

  // Measure tooltip height after render so the clamp keeps it on-screen.
  useEffect(() => {
    if (!tooltipRef.current) return
    const h = tooltipRef.current.getBoundingClientRect().height
    if (h > 0 && Math.abs(h - tooltipHeight) > 1) setTooltipHeight(h)
  })

  if (!currentStep || !rect) return null

  const handleExit = () => {
    // Route away from the demo URL — the evolution layout's cleanup effect
    // calls exitDemo() on unmount, which clears the demo state in one place
    // instead of trying to keep two sources of truth in sync.
    navigate({ to: "/projects" })
  }

  const handleBack = () => {
    // Walk back inside the current phase first; if we're already on the
    // phase's first step, drop to the previous phase and land on its last
    // step so the user sees the panel that pushed them forward.
    if (subStepIdx > 0) {
      setSubStepIdx((i) => i - 1)
      return
    }
    const phaseIdx = PHASE_ORDER.indexOf(demoState.phase)
    if (phaseIdx <= 0) return
    const prevPhase = PHASE_ORDER[phaseIdx - 1]
    const prevSteps = STEPS.filter((s) => s.phase === prevPhase)
    setDemoPhase(prevPhase)
    // The phase-change effect resets subStepIdx to 0; schedule the last-index
    // jump on the next tick so it doesn't get clobbered.
    window.setTimeout(() => setSubStepIdx(prevSteps.length - 1), 0)
  }

  // First step of the very first phase has nothing to go back to.
  const canGoBack =
    subStepIdx > 0 || PHASE_ORDER.indexOf(demoState.phase) > 0

  // Spotlight visuals
  const isDark =
    typeof document !== "undefined" &&
    document.documentElement.classList.contains("dark")
  const overlayBg = "rgba(0, 8, 24, 0.55)"
  const ringColor = isDark
    ? "rgba(0, 212, 255, 0.85)"
    : "rgba(37, 99, 235, 0.9)"
  const ringGlow = isDark
    ? "rgba(0, 212, 255, 0.45)"
    : "rgba(37, 99, 235, 0.35)"
  const tooltipBorder = isDark
    ? "rgba(0, 212, 255, 0.35)"
    : "rgba(37, 99, 235, 0.25)"
  const cutout = {
    top: rect.top - PADDING,
    left: rect.left - PADDING,
    width: rect.width + PADDING * 2,
    height: rect.height + PADDING * 2,
  }

  const totalSteps = STEPS.length
  const stepNumber = STEPS.indexOf(currentStep) + 1

  return createPortal(
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        pointerEvents: "none",
      }}
    >
      {/* Four overlay rectangles around the spotlight cutout. They allow
          clicks to pass through over the highlighted element so the user can
          actually press the underlying button. */}
      <div
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          height: Math.max(0, cutout.top),
          background: overlayBg,
        }}
      />
      <div
        style={{
          position: "fixed",
          top: cutout.top + cutout.height,
          left: 0,
          right: 0,
          bottom: 0,
          background: overlayBg,
        }}
      />
      <div
        style={{
          position: "fixed",
          top: cutout.top,
          left: 0,
          width: Math.max(0, cutout.left),
          height: cutout.height,
          background: overlayBg,
        }}
      />
      <div
        style={{
          position: "fixed",
          top: cutout.top,
          left: cutout.left + cutout.width,
          right: 0,
          height: cutout.height,
          background: overlayBg,
        }}
      />

      {/* Highlight ring (purely decorative, doesn't block clicks). */}
      <div
        style={{
          position: "fixed",
          top: cutout.top,
          left: cutout.left,
          width: cutout.width,
          height: cutout.height,
          borderRadius: 8,
          boxShadow: `0 0 0 2px ${ringColor}, 0 0 24px 4px ${ringGlow}`,
          pointerEvents: "none",
          transition: "all 0.2s ease",
        }}
      />

      {/* Inner pulse ring on the actionable button inside the spotlight, if
          the step opted into double-spotlight mode. Pure CSS animation —
          purely decorative, doesn't block clicks on the real button. */}
      {pulseRect && (
        <div
          style={{
            position: "fixed",
            top: pulseRect.top - 4,
            left: pulseRect.left - 4,
            width: pulseRect.width + 8,
            height: pulseRect.height + 8,
            borderRadius: 10,
            border: `2px solid ${ringColor}`,
            boxShadow: `0 0 0 4px ${ringGlow}, 0 0 18px 6px ${ringGlow}`,
            pointerEvents: "none",
            animation: "demoPulseRing 1.4s ease-in-out infinite",
            zIndex: 1,
          }}
        />
      )}

      {/* Tooltip card */}
      <div
        ref={tooltipRef}
        role="dialog"
        aria-modal="false"
        style={{
          position: "fixed",
          top: tooltipPos.top,
          left: tooltipPos.left,
          width: TOOLTIP_WIDTH,
          background: "var(--popover)",
          color: "var(--popover-foreground)",
          border: `1px solid ${tooltipBorder}`,
          borderRadius: 10,
          padding: 16,
          boxShadow: isDark
            ? "0 12px 32px rgba(0, 0, 0, 0.45), 0 0 16px rgba(0, 212, 255, 0.15)"
            : "0 12px 32px rgba(15, 23, 42, 0.18), 0 0 16px rgba(37, 99, 235, 0.08)",
          pointerEvents: "auto",
          fontSize: 13,
          lineHeight: 1.55,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 6,
          }}
        >
          <div style={{ fontSize: 14, fontWeight: 600 }}>
            {t(currentStep.titleKey, {
              defaultValue: currentStep.titleFallback,
            })}
          </div>
          <div style={{ fontSize: 11, opacity: 0.6 }}>
            {stepNumber} / {totalSteps}
          </div>
        </div>
        <div style={{ marginBottom: 14, opacity: 0.92 }}>
          {t(currentStep.contentKey, {
            defaultValue: currentStep.contentFallback,
          })}
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 8,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <button
              type="button"
              onClick={handleExit}
              style={{
                fontSize: 11,
                color: "var(--muted-foreground)",
                background: "transparent",
                border: "none",
                cursor: "pointer",
                padding: 0,
                textDecoration: "underline",
              }}
            >
              {t("demoTour.exitDemo", { defaultValue: "Exit demo" })}
            </button>
            {canGoBack && (
              <button
                type="button"
                onClick={handleBack}
                style={{
                  fontSize: 12,
                  padding: "5px 12px",
                  borderRadius: 6,
                  border: "1px solid var(--border)",
                  background: "transparent",
                  color: "var(--foreground)",
                  cursor: "pointer",
                }}
              >
                {t("demoTour.back", { defaultValue: "Back" })}
              </button>
            )}
          </div>
          {currentStep.manualNext && (
            <button
              type="button"
              onClick={() => {
                const matching = STEPS.filter(
                  (s) => s.phase === demoState.phase,
                )
                if (subStepIdx < matching.length - 1) {
                  setSubStepIdx((i) => i + 1)
                } else if (currentStep.manualNextPhase) {
                  setDemoPhase(currentStep.manualNextPhase)
                }
              }}
              style={{
                fontSize: 12,
                padding: "5px 14px",
                borderRadius: 6,
                border: "1px solid var(--primary)",
                background: "var(--primary)",
                color: "var(--primary-foreground)",
                cursor: "pointer",
                fontWeight: 500,
              }}
            >
              {t("demoTour.gotIt", { defaultValue: "Got it" })}
            </button>
          )}
        </div>
      </div>
    </div>,
    document.body,
  )
}
