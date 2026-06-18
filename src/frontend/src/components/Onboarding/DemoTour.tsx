import { useNavigate } from "@tanstack/react-router"
import { useEffect, useMemo, useRef, useState } from "react"
import { createPortal } from "react-dom"
import { useTranslation } from "react-i18next"

import type { DemoPhase } from "@/hooks/useDemoMode"
import { setDemoPhase, useDemoState } from "@/hooks/useDemoMode"
import { useEvolution } from "@/hooks/useEvolution"

/**
 * Phase-driven walkthrough overlay for `/demo`.
 *
 * Three-layer overlay structure addresses leadership feedback #2 and #3:
 *
 *   z-9998: four invisible click-blocker rectangles surrounding the
 *           spotlight cutout. They absorb every click outside the
 *           highlighted region with `pointer-events: auto` and no
 *           background, so the user is forced to hit the highlighted
 *           target (or the in-tooltip Exit button).
 *   z-9999: a single full-screen SVG with a `<mask>` punching a hole
 *           where the spotlight is. Renders the dimming ring/glow without
 *           any seams between sibling divs and is `pointer-events: none`.
 *   z-10000: tooltip + inner pulse ring. Lives above everything and
 *           catches clicks on the in-tooltip controls (Got it / Back /
 *           Exit demo).
 *
 * Spotlight rect coords are quantized to device pixels via
 * `Math.round(value * dpr) / dpr` so the cutout aligns crisply on any
 * `devicePixelRatio` (HiDPI displays, OS scaling, browser zoom). A
 * `ResizeObserver` on the anchor element keeps the rect synced as
 * downstream layouts settle.
 */

interface Step {
  selector: string
  phase: DemoPhase
  titleKey: string
  contentKey: string
  titleFallback: string
  contentFallback: string
  placement?: "top" | "bottom" | "left" | "right"
  manualNext?: boolean
  manualNextPhase?: DemoPhase
  /** Inner pulse ring on the actionable button inside a wide spotlight. */
  pulseSelector?: string
  /** If true, advance to this step the moment its anchor mounts. */
  autoAdvanceOnAnchor?: boolean
  /** Hide the Back button on this step (e.g. a sub-step that mustn't be undone). */
  hideBack?: boolean
}

const PHASE_ORDER: DemoPhase[] = [
  "uninitialized",
  "configuring",
  "building",
  "running",
  "completed",
]

const STEPS: Step[] = [
  {
    phase: "uninitialized",
    selector: '[data-tour="new-task-btn"]',
    titleKey: "demoTour.create.title",
    contentKey: "demoTour.create.content",
    titleFallback: "Step 1 · Create a task",
    contentFallback:
      'Click "New task" to follow the full guided experience.',
    placement: "right",
  },
  {
    phase: "uninitialized",
    selector: '[data-tour="create-task-dialog"]',
    titleKey: "demoTour.createSubmit.title",
    contentKey: "demoTour.createSubmit.content",
    titleFallback: "Step 1b · Pick a build mode",
    contentFallback:
      'AI Build is selected, name pre-filled — click "Create" to continue.',
    placement: "right",
    autoAdvanceOnAnchor: true,
    pulseSelector: '[data-tour="create-task-submit"]',
    // Going back to step 1 would have to close the dialog the user just
    // opened — not worth supporting.
    hideBack: true,
  },
  {
    phase: "configuring",
    selector: '[data-tour="demo-task-row"]',
    titleKey: "demoTour.taskRow.title",
    contentKey: "demoTour.taskRow.content",
    titleFallback: "Step 2 · Your task appears in the sidebar",
    contentFallback:
      "The task you just created shows up in the left task list. In real projects you'll see every task here — click any row to switch between them.",
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
      'Click "Send" to step through the conversation. The AI gathers your requirements then asks whether to start building.',
    placement: "left",
    pulseSelector: '[data-tour="ai-send"]',
  },
  {
    phase: "building",
    selector: '[data-tour="ai-preview-body"]',
    titleKey: "demoTour.building.title",
    contentKey: "demoTour.building.content",
    titleFallback: "Step 4 · Wait while the build runs",
    contentFallback:
      "The progress bar fills as the agent moves through Gathering → Build → Review. Generated files appear below.",
    placement: "right",
    manualNext: true,
  },
  {
    phase: "building",
    selector: '[data-tour="ai-run"]',
    titleKey: "demoTour.run.title",
    contentKey: "demoTour.run.content",
    titleFallback: "Step 5 · Submit and start the auto-design loop",
    contentFallback:
      'Click "Submit & Run" to kick off evolution — candidates appear generation by generation.',
    placement: "right",
  },
  {
    phase: "running",
    selector: '[data-tour="result-canvas"]',
    titleKey: "demoTour.canvas.title",
    contentKey: "demoTour.canvas.content",
    titleFallback: "Step 6 · Watch the design process unfold",
    contentFallback:
      "Inspect the evolution graph — every node is one algorithm the system designed. Logs stream in alongside.",
    placement: "right",
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
      "Click the IDE tab to read the algorithm LLM4AD_Next evolved.",
    placement: "bottom",
  },
  {
    phase: "completed",
    selector: '[data-tour="demo-ide-code"]',
    titleKey: "demoTour.ideCode.title",
    contentKey: "demoTour.ideCode.content",
    titleFallback: "Step 8 · Skim the generated code",
    contentFallback:
      "This is the algorithm — greedy nearest-neighbor with 2-opt refinement. Skim through it, then click Got it to wrap up.",
    placement: "left",
    manualNext: true,
  },
  {
    phase: "completed",
    // Final step — no anchor, tooltip lands centered. The exit affordance
    // lives in the tooltip itself per leadership #9.
    selector: "",
    titleKey: "demoTour.exit.title",
    contentKey: "demoTour.exit.content",
    titleFallback: "You're ready",
    contentFallback:
      "Head back to the project list, configure an LLM provider, and create your first real project.",
    placement: "bottom",
    manualNext: true,
  },
]

interface Rect {
  top: number
  left: number
  width: number
  height: number
}

const CUTOUT_PADDING = 6
const TOOLTIP_WIDTH = 360
const TOOLTIP_GAP = 14
const VIEWPORT_MARGIN = 12

function quantizeToDevicePixels(value: number, dpr: number): number {
  if (!Number.isFinite(dpr) || dpr <= 0) return Math.round(value)
  return Math.round(value * dpr) / dpr
}

function getRect(el: Element): Rect {
  const r = el.getBoundingClientRect()
  const dpr = typeof window !== "undefined" ? window.devicePixelRatio : 1
  return {
    top: quantizeToDevicePixels(r.top, dpr),
    left: quantizeToDevicePixels(r.left, dpr),
    width: quantizeToDevicePixels(r.width, dpr),
    height: quantizeToDevicePixels(r.height, dpr),
  }
}

function placeTooltip(
  rect: Rect | null,
  preferred: Step["placement"],
  tooltipHeight: number,
): { top: number; left: number } {
  const vw = window.innerWidth
  const vh = window.innerHeight
  if (!rect) {
    // Centered fallback for the final step (no anchor).
    return {
      top: Math.max(VIEWPORT_MARGIN, (vh - tooltipHeight) / 2),
      left: Math.max(VIEWPORT_MARGIN, (vw - TOOLTIP_WIDTH) / 2),
    }
  }
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

export default function DemoTour() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const demoState = useDemoState()
  const { activeTab } = useEvolution()
  const [subStepIdx, setSubStepIdx] = useState(0)
  const [rect, setRect] = useState<Rect | null>(null)
  const [pulseRect, setPulseRect] = useState<Rect | null>(null)
  const [tooltipHeight, setTooltipHeight] = useState(200)
  const [tooltipPos, setTooltipPos] = useState<{ top: number; left: number }>({
    top: 0,
    left: 0,
  })
  const tooltipRef = useRef<HTMLDivElement | null>(null)

  // Reset sub-step when phase changes; clear stale rects so the overlay
  // doesn't paint against an unmounted target while the new anchor is
  // still settling.
  // biome-ignore lint/correctness/useExhaustiveDependencies: only re-fire on phase change
  useEffect(() => {
    setSubStepIdx(0)
    setRect(null)
    setPulseRect(null)
  }, [demoState.phase])

  // IDE tab listener: completed-phase step 7 advances to step 8 the moment
  // the user actually opens the IDE tab. Tracks previous activeTab so
  // hitting Back to step 7 doesn't immediately bounce forward again.
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

  const currentStep = useMemo(() => {
    const matching = STEPS.filter((s) => s.phase === demoState.phase)
    const idx = Math.min(subStepIdx, matching.length - 1)
    return matching[idx] ?? null
  }, [demoState.phase, subStepIdx])

  // Locate the current spotlight target. Uses ResizeObserver on the anchor
  // for tight sync as layouts settle, plus resize/scroll fallbacks. Also
  // re-measures at 150 / 350 / 650ms after first hit to catch the final
  // bounds of elements mounting inside an animating container (Radix
  // Dialog's zoom-in transform was the symptom that exposed this).
  useEffect(() => {
    if (!currentStep) return
    setRect(null)
    if (!currentStep.selector) {
      // Final step has no anchor.
      return
    }
    let cancelled = false
    let attempts = 0
    let observer: ResizeObserver | null = null
    let observedEl: Element | null = null
    const settleTimers: number[] = []

    const measure = (el: Element) => {
      const r = getRect(el)
      if (r.width > 0 && r.height > 0 && !cancelled) {
        setRect(r)
      }
    }
    const scheduleSettle = (el: Element) => {
      for (const delay of [150, 350, 650]) {
        settleTimers.push(
          window.setTimeout(() => {
            if (!cancelled && document.contains(el)) measure(el)
          }, delay),
        )
      }
    }
    const tick = () => {
      if (cancelled) return
      const el = document.querySelector(currentStep.selector)
      if (el) {
        measure(el)
        scheduleSettle(el)
        if (observer == null) {
          observer = new ResizeObserver(() => {
            if (observedEl) measure(observedEl)
          })
          observedEl = el
          observer.observe(el)
        }
        return
      }
      attempts += 1
      if (attempts < 40) window.setTimeout(tick, 100)
    }
    tick()

    const onUpdate = () => {
      const el = document.querySelector(currentStep.selector)
      if (el) measure(el)
      else if (!cancelled) setRect(null)
    }
    window.addEventListener("resize", onUpdate)
    window.addEventListener("scroll", onUpdate, true)
    return () => {
      cancelled = true
      for (const id of settleTimers) window.clearTimeout(id)
      observer?.disconnect()
      window.removeEventListener("resize", onUpdate)
      window.removeEventListener("scroll", onUpdate, true)
    }
  }, [currentStep])

  // Track the optional inner pulse target.
  //
  // Re-measure on a short schedule (150 / 350 / 650ms) after the first hit
  // so we catch the final position of elements that mount inside an
  // animating container (e.g. Radix Dialog's `data-[state=open]:zoom-in-95`
  // transform — getBoundingClientRect at frame 0 returns the pre-animation
  // bounds, which is what made the 1b pulse ring land off-target).
  useEffect(() => {
    setPulseRect(null)
    if (!currentStep?.pulseSelector) return
    const sel = currentStep.pulseSelector
    let cancelled = false
    let attempts = 0
    let observer: ResizeObserver | null = null
    let observedEl: Element | null = null
    const settleTimers: number[] = []

    const measure = (el: Element) => {
      const r = getRect(el)
      if (r.width > 0 && r.height > 0 && !cancelled) setPulseRect(r)
    }
    const scheduleSettle = (el: Element) => {
      for (const delay of [150, 350, 650]) {
        settleTimers.push(
          window.setTimeout(() => {
            if (!cancelled && document.contains(el)) measure(el)
          }, delay),
        )
      }
    }
    const tick = () => {
      if (cancelled) return
      const el = document.querySelector(sel)
      if (el) {
        measure(el)
        scheduleSettle(el)
        if (observer == null) {
          observer = new ResizeObserver(() => {
            if (observedEl) measure(observedEl)
          })
          observedEl = el
          observer.observe(el)
        }
        return
      }
      attempts += 1
      if (attempts < 40) window.setTimeout(tick, 100)
    }
    tick()

    const onUpdate = () => {
      const el = document.querySelector(sel)
      if (el) measure(el)
      else if (!cancelled) setPulseRect(null)
    }
    window.addEventListener("resize", onUpdate)
    window.addEventListener("scroll", onUpdate, true)
    return () => {
      cancelled = true
      for (const id of settleTimers) window.clearTimeout(id)
      observer?.disconnect()
      window.removeEventListener("resize", onUpdate)
      window.removeEventListener("scroll", onUpdate, true)
    }
  }, [currentStep])

  // Auto-advance to the next sub-step when its anchor appears in the DOM.
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

  // Reposition the tooltip whenever the spotlight or the tooltip itself
  // changes size.
  useEffect(() => {
    if (!currentStep) return
    setTooltipPos(placeTooltip(rect, currentStep.placement, tooltipHeight))
  }, [rect, currentStep, tooltipHeight])

  // Measure tooltip height after render so the clamp keeps it on-screen.
  useEffect(() => {
    if (!tooltipRef.current) return
    const h = tooltipRef.current.getBoundingClientRect().height
    if (h > 0 && Math.abs(h - tooltipHeight) > 1) setTooltipHeight(h)
  })

  if (!currentStep) return null
  // For anchored steps without a settled rect, suspend rendering so we
  // never paint against an unmounted target. The final step has no anchor
  // and renders even with `rect === null`.
  if (currentStep.selector && !rect) return null

  const phaseIdx = PHASE_ORDER.indexOf(demoState.phase)
  const matching = STEPS.filter((s) => s.phase === demoState.phase)
  const isLastStepInPhase = subStepIdx >= matching.length - 1
  // Total step number for the "{n} / {total}" badge — count steps across
  // all phases so the user sees overall progress, not per-phase.
  const totalSteps = STEPS.length
  const stepNumber = STEPS.indexOf(currentStep) + 1
  const isFinalStep = stepNumber === totalSteps

  const canGoBack =
    !currentStep.hideBack &&
    (subStepIdx > 0 || phaseIdx > 0)

  const handleAdvance = () => {
    if (isLastStepInPhase) {
      if (currentStep.manualNextPhase) {
        setDemoPhase(currentStep.manualNextPhase)
        return
      }
      // Final step — exit on the manualNext button.
      if (isFinalStep) {
        navigate({ to: "/projects" })
        return
      }
    }
    setSubStepIdx((i) => i + 1)
  }

  const handleBack = () => {
    if (subStepIdx > 0) {
      setSubStepIdx((i) => i - 1)
      return
    }
    if (phaseIdx <= 0) return
    const prevPhase = PHASE_ORDER[phaseIdx - 1]
    const prevSteps = STEPS.filter((s) => s.phase === prevPhase)
    // Find the last "user-facing" step in the previous phase. autoAdvance
    // steps (e.g. step 1b which only mounts when its anchor dialog appears)
    // would immediately advance again or sit on a missing anchor — skip them.
    let targetIdx = prevSteps.length - 1
    while (targetIdx > 0 && prevSteps[targetIdx]?.autoAdvanceOnAnchor) {
      targetIdx -= 1
    }
    setDemoPhase(prevPhase)
    const finalIdx = targetIdx
    window.setTimeout(() => setSubStepIdx(finalIdx), 0)
  }

  const handleExit = () => {
    navigate({ to: "/projects" })
  }

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

  // The cutout rectangle (with padding) — used by both the SVG mask
  // visual and the four invisible click-blocker rectangles.
  const cutout = rect
    ? {
        top: rect.top - CUTOUT_PADDING,
        left: rect.left - CUTOUT_PADDING,
        width: rect.width + CUTOUT_PADDING * 2,
        height: rect.height + CUTOUT_PADDING * 2,
      }
    : null

  const vw = typeof window !== "undefined" ? window.innerWidth : 1920
  const vh = typeof window !== "undefined" ? window.innerHeight : 1080

  return createPortal(
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9998,
        pointerEvents: "none",
      }}
    >
      {/* z-9998: invisible click-blocker rectangles surrounding the cutout.
          Pure event sinks — no background, no visual. They sit underneath
          the visual mask so the dimmed area looks seamless. When there is
          no cutout (final step), a single full-screen blocker is rendered. */}
      {cutout ? (
        <>
          <div
            style={{
              position: "fixed",
              top: 0,
              left: 0,
              right: 0,
              height: Math.max(0, cutout.top),
              pointerEvents: "auto",
            }}
            onClickCapture={(e) => e.stopPropagation()}
            onMouseDownCapture={(e) => e.stopPropagation()}
            aria-hidden="true"
          />
          <div
            style={{
              position: "fixed",
              top: cutout.top + cutout.height,
              left: 0,
              right: 0,
              bottom: 0,
              pointerEvents: "auto",
            }}
            onClickCapture={(e) => e.stopPropagation()}
            onMouseDownCapture={(e) => e.stopPropagation()}
            aria-hidden="true"
          />
          <div
            style={{
              position: "fixed",
              top: cutout.top,
              left: 0,
              width: Math.max(0, cutout.left),
              height: cutout.height,
              pointerEvents: "auto",
            }}
            onClickCapture={(e) => e.stopPropagation()}
            onMouseDownCapture={(e) => e.stopPropagation()}
            aria-hidden="true"
          />
          <div
            style={{
              position: "fixed",
              top: cutout.top,
              left: cutout.left + cutout.width,
              right: 0,
              height: cutout.height,
              pointerEvents: "auto",
            }}
            onClickCapture={(e) => e.stopPropagation()}
            onMouseDownCapture={(e) => e.stopPropagation()}
            aria-hidden="true"
          />
        </>
      ) : (
        <div
          style={{
            position: "fixed",
            inset: 0,
            pointerEvents: "auto",
          }}
          onClickCapture={(e) => e.stopPropagation()}
          onMouseDownCapture={(e) => e.stopPropagation()}
          aria-hidden="true"
        />
      )}

      {/* z-9999: SVG-mask visual. One element, one path — no sub-pixel seams. */}
      <svg
        style={{
          position: "fixed",
          inset: 0,
          width: vw,
          height: vh,
          zIndex: 1,
          pointerEvents: "none",
        }}
        aria-hidden="true"
      >
        <title>Demo tour overlay</title>
        <defs>
          <mask id="demo-tour-mask">
            <rect width="100%" height="100%" fill="white" />
            {cutout && (
              <rect
                x={cutout.left}
                y={cutout.top}
                width={cutout.width}
                height={cutout.height}
                rx={8}
                ry={8}
                fill="black"
              />
            )}
          </mask>
        </defs>
        <rect
          width="100%"
          height="100%"
          fill={overlayBg}
          mask="url(#demo-tour-mask)"
        />
        {cutout && (
          <rect
            x={cutout.left}
            y={cutout.top}
            width={cutout.width}
            height={cutout.height}
            rx={8}
            ry={8}
            fill="none"
            stroke={ringColor}
            strokeWidth={2}
            style={{
              filter: `drop-shadow(0 0 12px ${ringGlow})`,
            }}
          />
        )}
      </svg>

      {/* Inner pulse ring (purely decorative, no pointer events). */}
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
            zIndex: 2,
          }}
        />
      )}

      {/* z-10000: tooltip card. Lives above everything.

          stopPropagation on pointer events is critical when the spotlight
          target is a Radix dialog: without it, clicking anywhere on the
          tooltip would trigger the dialog's onPointerDownOutside handler
          and close the dialog mid-walkthrough. */}
      <div
        ref={tooltipRef}
        role="dialog"
        aria-modal="false"
        onPointerDown={(e) => e.stopPropagation()}
        onMouseDown={(e) => e.stopPropagation()}
        onClick={(e) => e.stopPropagation()}
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
          zIndex: 10,
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
            {t(currentStep.titleKey, { defaultValue: currentStep.titleFallback })}
          </div>
          <div style={{ fontSize: 11, opacity: 0.6 }}>
            {stepNumber} / {totalSteps}
          </div>
        </div>
        <div style={{ marginBottom: 14, opacity: 0.92, whiteSpace: "pre-wrap" }}>
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
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <button
              type="button"
              onClick={handleExit}
              style={{
                fontSize: 11,
                color: "var(--muted-foreground)",
                background: "transparent",
                border: "none",
                cursor: "pointer",
                padding: "5px 8px",
                textDecoration: "underline",
              }}
            >
              {t("demoTour.exitDemo", { defaultValue: "Exit demo" })}
            </button>
            {currentStep.manualNext && (
              <button
                type="button"
                onClick={handleAdvance}
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
                {isFinalStep
                  ? t("demoTour.finishExit", { defaultValue: "Exit demo" })
                  : t("demoTour.gotIt", { defaultValue: "Got it" })}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body,
  )
}
