import {
  Pause,
  Play,
  Repeat,
  SkipBack,
  SkipForward,
  Square,
} from "lucide-react"
import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"

import type { TaskResponse } from "@/client"
import { useEvolution } from "@/hooks/useEvolution"

interface EvolutionProgressBarProps {
  task: TaskResponse | null
}

const PLAY_INTERVAL_MS = 1500

export default function EvolutionProgressBar({
  task,
}: EvolutionProgressBarProps) {
  const {
    currentGeneration,
    maxGeneration,
    setCurrentGeneration,
    isPlaying,
    setIsPlaying,
  } = useEvolution()
  const { t } = useTranslation()

  const [isAutoPlay, setIsAutoPlay] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [dragPercent, setDragPercent] = useState<number | null>(null)
  const barRef = useRef<HTMLDivElement>(null)

  const getRatio = useCallback((clientX: number) => {
    if (!barRef.current) return null
    const rect = barRef.current.getBoundingClientRect()
    return Math.max(0, Math.min(1, (clientX - rect.left) / rect.width))
  }, [])

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      setIsDragging(true)
      const ratio = getRatio(e.clientX)
      if (ratio == null) return
      setDragPercent(ratio * 100)
      setCurrentGeneration(Math.round(ratio * maxGeneration))
    },
    [getRatio, maxGeneration, setCurrentGeneration],
  )

  useEffect(() => {
    if (!isDragging) return

    const handleMouseMove = (e: MouseEvent) => {
      const ratio = getRatio(e.clientX)
      if (ratio == null) return
      setDragPercent(ratio * 100)
      setCurrentGeneration(Math.round(ratio * maxGeneration))
    }
    const handleMouseUp = (e: MouseEvent) => {
      const ratio = getRatio(e.clientX)
      if (ratio != null) {
        const snapped = Math.round(ratio * maxGeneration)
        setCurrentGeneration(snapped)
      }
      setDragPercent(null)
      setIsDragging(false)
    }

    document.addEventListener("mousemove", handleMouseMove)
    document.addEventListener("mouseup", handleMouseUp)
    return () => {
      document.removeEventListener("mousemove", handleMouseMove)
      document.removeEventListener("mouseup", handleMouseUp)
    }
  }, [isDragging, getRatio, maxGeneration, setCurrentGeneration])

  // Auto-play timer
  useEffect(() => {
    if (!isPlaying) return

    const timer = setInterval(() => {
      if (currentGeneration >= maxGeneration) {
        if (isAutoPlay) {
          setCurrentGeneration(0)
        } else {
          setIsPlaying(false)
        }
      } else {
        setCurrentGeneration(currentGeneration + 1)
      }
    }, PLAY_INTERVAL_MS)

    return () => clearInterval(timer)
  }, [
    isPlaying,
    currentGeneration,
    maxGeneration,
    isAutoPlay,
    setCurrentGeneration,
    setIsPlaying,
  ])

  // Keyboard shortcuts: ←/→ step generation; space toggle play.
  // Only active when a runnable task is loaded and user isn't typing.
  useEffect(() => {
    if (!task || task.status === "uninitialized") return

    const isTypingTarget = (el: EventTarget | null) => {
      if (!(el instanceof HTMLElement)) return false
      const tag = el.tagName
      return (
        tag === "INPUT" ||
        tag === "TEXTAREA" ||
        tag === "SELECT" ||
        el.isContentEditable
      )
    }

    const onKey = (e: KeyboardEvent) => {
      if (e.defaultPrevented || isTypingTarget(e.target)) return
      if (e.ctrlKey || e.metaKey || e.altKey) return

      if (e.key === "ArrowLeft") {
        e.preventDefault()
        setCurrentGeneration(Math.max(0, currentGeneration - 1))
      } else if (e.key === "ArrowRight") {
        e.preventDefault()
        setCurrentGeneration(Math.min(maxGeneration, currentGeneration + 1))
      } else if (e.key === " ") {
        e.preventDefault()
        setIsPlaying(!isPlaying)
      }
    }

    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [
    task,
    currentGeneration,
    maxGeneration,
    isPlaying,
    setCurrentGeneration,
    setIsPlaying,
  ])

  if (!task || task.status === "uninitialized") return null

  const _isRunning: boolean = task.status === "running"
  void _isRunning
  const _isCompleted: boolean = task.status === "completed"
  void _isCompleted
  const snappedPercent =
    maxGeneration > 0 ? (currentGeneration / maxGeneration) * 100 : 0
  const progressPercent = dragPercent ?? snappedPercent

  const stepBack = () =>
    setCurrentGeneration(Math.max(0, currentGeneration - 1))
  const stepForward = () =>
    setCurrentGeneration(Math.min(maxGeneration, currentGeneration + 1))
  const togglePlay = () => setIsPlaying(!isPlaying)
  const stop = () => {
    setIsPlaying(false)
    setCurrentGeneration(0)
  }

  const controls = [
    {
      icon: SkipBack,
      label: t("evolution.progressBar.previousGen"),
      onClick: stepBack,
    },
    {
      icon: isPlaying ? Pause : Play,
      label: isPlaying
        ? t("evolution.progressBar.pause")
        : t("evolution.progressBar.play"),
      onClick: togglePlay,
      primary: true,
    },
    {
      icon: Square,
      label: t("evolution.progressBar.stop"),
      onClick: stop,
    },
    {
      icon: SkipForward,
      label: t("evolution.progressBar.nextGen"),
      onClick: stepForward,
    },
  ]

  return (
    <div className="flex items-center gap-4 px-4 py-3">
      {/* Progress info */}
      <div className="flex items-center gap-3 shrink-0">
        <span className="text-[10px] text-muted-foreground uppercase tracking-widest">
          {t("evolution.progressBar.evolutionGeneration")}
        </span>
        <span className="text-xs font-mono text-primary">
          {currentGeneration} / {maxGeneration}
        </span>
      </div>

      {/* Progress bar */}
      <div
        ref={barRef}
        className={`flex-1 relative h-2 bg-muted rounded-full overflow-hidden border border-border/40 ${isDragging ? "cursor-grabbing" : "cursor-pointer"}`}
        onMouseDown={handleMouseDown}
      >
        <div
          className={`absolute inset-y-0 left-0 rounded-full ${isDragging ? "" : "transition-all duration-300"}`}
          style={{
            width: `${progressPercent}%`,
            background:
              "linear-gradient(90deg, color-mix(in srgb, var(--primary) 40%, transparent), var(--primary))",
            boxShadow:
              "0 0 10px color-mix(in srgb, var(--primary) 50%, transparent), 0 0 20px color-mix(in srgb, var(--primary) 20%, transparent)",
          }}
        />
        {/* Generation tick marks — only when generation count is small enough to be readable */}
        {maxGeneration > 0 &&
          maxGeneration <= 80 &&
          Array.from({ length: maxGeneration + 1 }, (_, i) => (
            <div
              key={i}
              className="absolute top-0 bottom-0 w-px"
              style={{
                left: `${(i / maxGeneration) * 100}%`,
                backgroundColor:
                  i <= currentGeneration
                    ? "color-mix(in srgb, var(--primary) 30%, transparent)"
                    : "color-mix(in srgb, var(--border) 30%, transparent)",
              }}
            />
          ))}
        {/* Animated scan line */}
        {isPlaying && (
          <div
            className="absolute inset-y-0 w-8 animate-pulse"
            style={{
              left: `${progressPercent}%`,
              background:
                "linear-gradient(90deg, transparent, color-mix(in srgb, var(--primary) 40%, transparent), transparent)",
            }}
          />
        )}
      </div>

      {/* Controls */}
      <div className="flex items-center gap-1 shrink-0">
        {controls.map((ctrl) => (
          <button
            key={ctrl.label}
            type="button"
            title={ctrl.label}
            onClick={ctrl.onClick}
            className={`p-2 rounded-md transition-all duration-200 ${
              ctrl.primary
                ? "bg-primary/15 text-primary border border-primary/30 hover:bg-primary/25 shadow-[0_0_8px] shadow-primary/20"
                : "text-muted-foreground hover:text-primary hover:bg-accent/60 border border-transparent hover:border-border/40"
            }`}
          >
            <ctrl.icon className="size-4" />
          </button>
        ))}

        {/* Auto-play divider + toggle */}
        <div className="w-px h-5 bg-border/40 mx-1" />
        <button
          type="button"
          title={
            isAutoPlay
              ? t("evolution.progressBar.disableLoop")
              : t("evolution.progressBar.enableLoop")
          }
          onClick={() => setIsAutoPlay(!isAutoPlay)}
          className={`p-2 rounded-md transition-all duration-200 border ${
            isAutoPlay
              ? "bg-primary/15 text-primary border-primary/30"
              : "text-muted-foreground hover:text-muted-foreground border-transparent hover:border-border/40"
          }`}
        >
          <Repeat className="size-4" />
        </button>
      </div>
    </div>
  )
}
