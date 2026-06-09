import { type ClassValue, clsx } from "clsx"
import type { KeyboardEvent } from "react"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Shared Enter-key behavior for chat composer textareas.
 *
 * - Plain Enter: send the message.
 * - Shift+Enter: insert a newline (handled natively by the browser).
 * - Ctrl / Alt / Cmd + Enter: insert a newline at the caret. The browser does
 *   not produce a newline for these modifier combos, so it is inserted manually
 *   and the caret is restored just after it.
 *
 * @param e - The textarea keydown event.
 * @param value - Current textarea value (controlled state).
 * @param setValue - Setter for the controlled value.
 * @param onSend - Called when a plain Enter should submit.
 */
export function handleComposerEnter(
  e: KeyboardEvent<HTMLTextAreaElement>,
  value: string,
  setValue: (next: string) => void,
  onSend: () => void,
): void {
  if (e.key !== "Enter") return
  // Shift+Enter: let the browser insert the newline.
  if (e.shiftKey) return

  if (e.ctrlKey || e.altKey || e.metaKey) {
    e.preventDefault()
    const el = e.currentTarget
    const start = el.selectionStart ?? value.length
    const end = el.selectionEnd ?? value.length
    setValue(`${value.slice(0, start)}\n${value.slice(end)}`)
    // Restore the caret right after the inserted newline once React has
    // re-rendered the controlled textarea.
    requestAnimationFrame(() => {
      el.selectionStart = start + 1
      el.selectionEnd = start + 1
    })
    return
  }

  // Plain Enter: submit.
  e.preventDefault()
  onSend()
}

/**
 * Format a numeric score for display, keeping up to `maxDecimals` decimal
 * places while stripping trailing zeros (and a dangling decimal point).
 *
 * Uses `toFixed` then trims the tail with a regex so very small values keep
 * their decimal notation instead of switching to scientific notation
 * (e.g. `0.00000001` stays `"0.00000001"`, not `"1e-8"`).
 *
 * @param value - The score to format.
 * @param maxDecimals - Maximum number of decimal places to keep (default 8).
 * @returns The formatted string, e.g. `0.5` for `0.50000000`, `12` for `12`.
 */
export function formatScore(value: number, maxDecimals = 8): string {
  return value.toFixed(maxDecimals).replace(/\.?0+$/, "")
}

export function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZone: "Asia/Shanghai",
  })
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Shanghai",
  })
}
