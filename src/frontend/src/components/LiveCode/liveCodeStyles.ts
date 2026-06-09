/**
 * Shared visual styles for the live-code feature.
 *
 * Tailwind classes for the real group-code status badge, keyed by the
 * backend `status` string (`valid` / `disabled` / `expired` / `full`).
 */
export const TARGET_STATUS_STYLES: Record<string, string> = {
  valid:
    "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-400",
  disabled:
    "border-zinc-200 bg-zinc-50 text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400",
  expired:
    "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-400",
  full: "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-400",
}

/** All selectable rotation strategies, in display order. */
export const STRATEGIES = ["sequential", "round_robin", "random"] as const
