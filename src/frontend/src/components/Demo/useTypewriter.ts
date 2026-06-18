import { useCallback, useEffect, useRef, useState } from "react"

interface UseTypewriterOptions {
  /** Milliseconds between each character. Default 30ms. */
  speed?: number
  /** Fired once the full target string has been typed out. */
  onDone?: () => void
  /** Skip the animation entirely and resolve to the full text immediately. */
  skipImmediately?: boolean
}

interface UseTypewriterResult {
  /** The portion of `target` typed out so far. */
  text: string
  /** True until every character is in place. */
  isTyping: boolean
  /** Snap to the full `target`. Safe to call mid-animation. */
  skip: () => void
}

/**
 * Char-by-char typewriter for the demo composer.
 *
 * Resets and replays whenever `target` changes, so each pre-filled turn in
 * the gather script gets its own animation. Uses `setTimeout` (not rAF) so
 * the effect still advances when the tab is backgrounded — important for
 * the "user clicked away during demo, comes back, finds composer half-typed"
 * edge case.
 *
 * Usage in DemoBuildShell:
 *   const { text, isTyping, skip } = useTypewriter(prefillForCurrentTurn)
 *   <textarea value={text} readOnly onClick={skip} />
 *   <button disabled={isTyping || !text.trim()}>Send</button>
 */
export function useTypewriter(
  target: string,
  opts: UseTypewriterOptions = {},
): UseTypewriterResult {
  const { speed = 30, onDone, skipImmediately = false } = opts
  const [text, setText] = useState(skipImmediately ? target : "")
  const timerRef = useRef<number | null>(null)
  const onDoneRef = useRef(onDone)
  onDoneRef.current = onDone

  const clearTimer = () => {
    if (timerRef.current != null) {
      window.clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }

  // Run / re-run whenever target changes. Each run schedules itself one char
  // at a time; we track progress in a closure-local index so React state
  // updates only happen at character boundaries (no extra renders).
  useEffect(() => {
    clearTimer()
    if (skipImmediately || !target) {
      setText(target ?? "")
      onDoneRef.current?.()
      return
    }
    setText("")
    let i = 0
    const tick = () => {
      i += 1
      setText(target.slice(0, i))
      if (i >= target.length) {
        timerRef.current = null
        onDoneRef.current?.()
        return
      }
      timerRef.current = window.setTimeout(tick, speed)
    }
    timerRef.current = window.setTimeout(tick, speed)
    return clearTimer
  }, [target, speed, skipImmediately])

  const skip = useCallback(() => {
    clearTimer()
    setText(target)
    onDoneRef.current?.()
  }, [target])

  const isTyping = text.length < target.length

  return { text, isTyping, skip }
}
