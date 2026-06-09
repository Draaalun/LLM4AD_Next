import { useCallback, useRef, useState } from "react"
import type { ChatTuneActiveStage, ChatTuneStageStatus } from "@/client"
import { authFetch } from "@/utils/auth"

/**
 * Mid-turn stage update pushed by the backend. All status fields are optional
 * — only the ones that changed are guaranteed to be present, so consumers
 * should merge against their last known snapshot.
 */
export interface ChatTuneStageUpdate {
  stage?: ChatTuneActiveStage
  status?: ChatTuneStageStatus
  active_stage?: ChatTuneActiveStage | null
  gathering_status?: ChatTuneStageStatus
  build_status?: ChatTuneStageStatus
  review_status?: ChatTuneStageStatus
}

export interface ChatTuneStreamCallbacks {
  onChunk: (content: string) => void
  onPayload: (payload: Record<string, unknown>) => void
  onStageUpdate?: (update: ChatTuneStageUpdate) => void
  onDone: () => void
  onCancelled: () => void
  onError: (error: string) => void
}

export function useChatTuneStream() {
  const [isStreaming, setIsStreaming] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  const disconnect = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setIsStreaming(false)
  }, [])

  const connect = useCallback(
    (taskId: string, turnId: string, callbacks: ChatTuneStreamCallbacks) => {
      disconnect()

      const abort = new AbortController()
      abortRef.current = abort
      setIsStreaming(true)

      const baseUrl = import.meta.env.VITE_API_URL || ""
      const url = `${baseUrl}/api/v1/llm4ad/tasks/${taskId}/chat-tune/turns/${turnId}/stream`

      ;(async () => {
        try {
          const resp = await authFetch(url, { signal: abort.signal })
          if (!resp.ok) {
            callbacks.onError(`HTTP ${resp.status}`)
            setIsStreaming(false)
            return
          }

          const reader = resp.body!.getReader()
          const decoder = new TextDecoder()
          let buffer = ""
          let currentEvent = ""
          let currentData = ""

          while (true) {
            const { done, value } = await reader.read()
            if (done) break

            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split("\n")
            buffer = lines.pop() ?? ""

            for (const line of lines) {
              if (line.startsWith("event:")) {
                currentEvent = line.slice(6).trim()
              } else if (line.startsWith("data:")) {
                currentData = line.slice(5).trim()
              } else if (line.trim() === "") {
                processSSEEvent(currentEvent, currentData, callbacks, () => {
                  setIsStreaming(false)
                })
                currentEvent = ""
                currentData = ""
              }
            }
          }
        } catch (err: unknown) {
          if ((err as Error).name === "AbortError") return
          callbacks.onError(
            (err as Error).message || "Stream connection failed",
          )
          setIsStreaming(false)
        }
      })()
    },
    [disconnect],
  )

  return { connect, disconnect, isStreaming }
}

function processSSEEvent(
  event: string,
  data: string,
  callbacks: ChatTuneStreamCallbacks,
  markDone: () => void,
) {
  switch (event) {
    case "connected":
    case "heartbeat":
      return

    case "timeout":
      callbacks.onError("idle_timeout")
      markDone()
      return

    case "done":
      markDone()
      return
  }

  if (!data) return

  try {
    const parsed = JSON.parse(data)
    switch (parsed.type) {
      case "chunk":
        if (parsed.content) callbacks.onChunk(parsed.content)
        break
      case "payload":
        if (parsed.data) callbacks.onPayload(parsed.data)
        break
      case "stage_update":
        callbacks.onStageUpdate?.(parsed as ChatTuneStageUpdate)
        break
      case "done":
        callbacks.onDone()
        markDone()
        break
      case "cancelled":
        callbacks.onCancelled()
        markDone()
        break
      case "error":
        callbacks.onError(parsed.error || "Unknown error")
        markDone()
        break
    }
  } catch {
    // skip malformed JSON
  }
}
