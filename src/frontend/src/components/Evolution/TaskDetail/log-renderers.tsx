import type { LogEntry } from "@/hooks/useTaskLogs"

export const LEVEL_STYLES: Record<string, string> = {
  TRACE: "text-gray-500",
  DEBUG: "text-blue-600 dark:text-blue-400",
  INFO: "text-green-600 dark:text-green-400",
  WARNING: "text-yellow-600 dark:text-yellow-400",
  ERROR: "text-red-600 dark:text-red-400",
  CRITICAL: "text-red-700 dark:text-red-500 font-bold",
}

// Message-body tint per level — softer than the LEVEL label so a wall of logs
// remains readable, but each line's severity is recognizable at a glance.
export const LEVEL_MESSAGE_STYLES: Record<string, string> = {
  TRACE: "text-gray-500 dark:text-gray-500",
  DEBUG: "text-sky-700/85 dark:text-sky-300/85",
  INFO: "text-gray-800 dark:text-gray-200",
  WARNING: "text-yellow-700 dark:text-yellow-300",
  ERROR: "text-red-700 dark:text-red-300",
  CRITICAL: "text-red-800 dark:text-red-200 font-medium",
}

const DEFAULT_MESSAGE_CLS = "text-gray-800 dark:text-gray-200"

export const SYSTEM_STYLES: Record<string, string> = {
  connected:
    "bg-green-500/15 text-green-700 dark:text-green-400 border-l-2 border-green-600 dark:border-green-500 px-3 py-1.5 my-1 rounded-r text-xs",
  done: "bg-blue-500/15 text-blue-700 dark:text-blue-400 border-l-2 border-blue-600 dark:border-blue-500 px-3 py-1.5 my-1 rounded-r text-xs",
  timeout:
    "bg-yellow-500/15 text-yellow-700 dark:text-yellow-400 border-l-2 border-yellow-600 dark:border-yellow-500 px-3 py-1.5 my-1 rounded-r text-xs",
  error:
    "bg-red-500/15 text-red-700 dark:text-red-400 border-l-2 border-red-600 dark:border-red-500 px-3 py-1.5 my-1 rounded-r text-xs",
  system:
    "bg-purple-500/15 text-purple-700 dark:text-purple-300 border-l-2 border-purple-600 dark:border-purple-500 px-3 py-1.5 my-1 rounded-r text-xs font-semibold",
  end: "bg-blue-500/15 text-blue-700 dark:text-blue-400 border-l-2 border-blue-600 dark:border-blue-500 px-3 py-1.5 my-1 rounded-r text-xs",
}

export const SYSTEM_ICONS: Record<string, string> = {
  connected: "●",
  done: "■",
  timeout: "⏱",
  error: "✕",
  system: "ℹ",
  end: "■",
}

export function formatLogTime(raw: unknown): string {
  if (typeof raw !== "string") return ""
  try {
    const d = new Date(raw)
    const opts: Intl.DateTimeFormatOptions = {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
      timeZone: "Asia/Shanghai",
    }
    const base = d.toLocaleString("zh-CN", opts)
    const ms = String(d.getMilliseconds()).padStart(3, "0")
    return `${base}.${ms}`
  } catch {
    return String(raw)
  }
}

export function renderSystemEntry(entry: LogEntry) {
  const event = String(entry.event ?? "")
  const cls = SYSTEM_STYLES[event] ?? SYSTEM_STYLES.connected
  const icon = SYSTEM_ICONS[event] ?? "●"
  const status = entry.status ? ` [${entry.status}]` : ""
  const msg = (entry.message ?? entry.error_message ?? "") as string
  const ts = entry.timestamp ?? entry.ts
  const time = formatLogTime(ts)

  const fullText = `${time ? `[${time}] ` : ""}${msg}${status}`

  return (
    <div
      className={`${cls} whitespace-pre overflow-hidden text-ellipsis min-w-[300px] w-fit`}
      title={fullText}
    >
      {time && (
        <span className="text-inherit opacity-70 select-none">[{time}] </span>
      )}
      <span className="font-bold mr-1">{icon}</span>
      {msg}
      {status && <span className="font-mono font-bold ml-1">{status}</span>}
    </div>
  )
}

export function renderLogEntry(entry: LogEntry) {
  const ts = entry.timestamp ?? entry.ts
  const level = String(entry.level ?? "").toUpperCase()
  const message = (entry.message ?? entry.msg ?? "") as string
  const mod = entry.module as string | undefined
  const fn = entry.function as string | undefined
  const line = entry.line as number | undefined

  const levelCls = LEVEL_STYLES[level] ?? "text-gray-500 dark:text-gray-400"
  const messageCls = LEVEL_MESSAGE_STYLES[level] ?? DEFAULT_MESSAGE_CLS
  const time = formatLogTime(ts)

  let location = ""
  if (mod || fn) {
    const parts = [mod, fn].filter(Boolean).join(".")
    location = line != null ? `${parts}:${line}` : parts
  }

  return (
    <div className="leading-5 whitespace-pre hover:bg-black/[0.03] dark:hover:bg-white/[0.03]">
      {time && <span className="text-gray-500 select-none">[{time}] </span>}
      {level && <span className={`${levelCls} select-none`}>{level}</span>}
      <span className={messageCls}> {message}</span>
      {location && (
        <span className="text-gray-500 dark:text-gray-600 ml-2 text-[10px]">
          {location}
        </span>
      )}
    </div>
  )
}

export function renderFallbackEntry(entry: LogEntry) {
  const type = String(entry.type ?? "")
  const ts = entry.timestamp ?? entry.ts
  const time = formatLogTime(ts)

  if (type === "error") {
    const errMsg = (entry.error_message ?? entry.message ?? "") as string
    return (
      <div className="leading-5 whitespace-pre">
        {time && <span className="text-gray-500 select-none">[{time}] </span>}
        <span className="text-red-600 dark:text-red-400 select-none">
          ERROR
        </span>
        <span className="text-red-700 dark:text-red-300"> {errMsg}</span>
      </div>
    )
  }

  if (type === "print") {
    const stream = entry.stream === "stderr" ? "STDERR" : "STDOUT"
    const isStderr = entry.stream === "stderr"
    const streamCls = isStderr
      ? "text-yellow-600 dark:text-yellow-400"
      : "text-gray-500 dark:text-gray-400"
    const messageCls = isStderr
      ? "text-yellow-700 dark:text-yellow-300"
      : "text-gray-700 dark:text-gray-300"
    return (
      <div className="leading-5 whitespace-pre">
        {time && <span className="text-gray-500 select-none">[{time}] </span>}
        <span className={`${streamCls} select-none`}>{stream}</span>
        <span className={messageCls}> {entry.message as string}</span>
      </div>
    )
  }

  return (
    <div className="leading-5 whitespace-pre text-gray-600 dark:text-gray-400">
      {JSON.stringify(entry)}
    </div>
  )
}

export function renderEntry(entry: LogEntry) {
  if (entry._kind === "system") return renderSystemEntry(entry)
  if (entry._kind === "log" || entry.type === "log")
    return renderLogEntry(entry)
  return renderFallbackEntry(entry)
}

/* ─────────────── Log level filtering (shared) ─────────────── */

export type LogLevel = "INFO" | "WARNING" | "ERROR"
export const LOG_LEVELS: LogLevel[] = ["INFO", "WARNING", "ERROR"]

export function matchesLogLevels(
  entry: LogEntry,
  selected: Set<LogLevel>,
): boolean {
  if (selected.size === 0) return true
  if (entry._kind === "system") {
    const evt = String(entry.event ?? "")
    if (evt === "error") return selected.has("ERROR")
    return selected.has("INFO")
  }
  const level = String(entry.level ?? "").toUpperCase()
  if (selected.has("ERROR") && (level === "ERROR" || level === "CRITICAL"))
    return true
  if (selected.has("WARNING") && (level === "WARNING" || level === "WARN"))
    return true
  if (
    selected.has("INFO") &&
    level !== "DEBUG" &&
    level !== "TRACE" &&
    level !== "WARNING" &&
    level !== "WARN" &&
    level !== "ERROR" &&
    level !== "CRITICAL"
  )
    return true
  return false
}
