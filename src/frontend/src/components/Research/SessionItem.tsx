import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { FlaskConical, GripVertical, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"

import type { ResearchSession } from "./mock-data"

export default function SessionItem({
  session,
  isActive,
  overlay,
  onSelect,
  onDelete,
}: {
  session: ResearchSession
  isActive: boolean
  overlay?: boolean
  onSelect?: (id: string) => void
  onDelete?: (id: string) => void
}) {
  const { t } = useTranslation()
  const {
    attributes,
    listeners,
    setNodeRef,
    setActivatorNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: session.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  if (overlay) {
    return (
      <div className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg bg-background border border-primary/25 shadow-xl shadow-primary/10">
        <div className="size-7 rounded-lg flex items-center justify-center bg-primary/12 text-primary shrink-0">
          <FlaskConical className="size-3.5" />
        </div>
        <span className="text-[12px] font-medium truncate text-foreground/80">
          {session.title || t("research.title")}
        </span>
      </div>
    )
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`group relative flex items-center gap-2 px-2.5 py-2 rounded-lg cursor-pointer active:cursor-grabbing transition-all duration-200 w-full touch-none ${
        isDragging ? "opacity-30 scale-95" : ""
      } ${isActive ? "bg-primary/8 dark:bg-primary/12" : "hover:bg-muted/60"}`}
      onClick={() => onSelect?.(session.id)}
    >
      {isActive && (
        <div className="absolute left-0 top-2 bottom-2 w-[2.5px] rounded-full bg-gradient-to-b from-primary to-blue-500" />
      )}

      <div
        ref={setActivatorNodeRef}
        className="shrink-0 opacity-0 group-hover:opacity-50 hover:!opacity-100 cursor-grab active:cursor-grabbing transition-opacity p-0.5 -ml-0.5"
      >
        <GripVertical className="size-3.5 text-muted-foreground" />
      </div>

      <div
        className={`size-7 rounded-lg flex items-center justify-center shrink-0 transition-colors ${
          isActive
            ? "bg-primary/12 text-primary"
            : "bg-muted/70 text-muted-foreground/50 group-hover:text-muted-foreground/70"
        }`}
      >
        <FlaskConical className="size-3.5" />
      </div>

      <div className="flex-1 min-w-0">
        <span
          className={`text-[12px] font-medium block truncate leading-tight ${
            isActive ? "text-primary" : "text-foreground/80"
          }`}
        >
          {session.title || t("research.title")}
        </span>
        <span className="text-[10px] text-muted-foreground/50 leading-tight mt-0.5 block">
          {new Date(session.updatedAt).toLocaleDateString()}
        </span>
      </div>

      <Button
        variant="ghost"
        size="icon-sm"
        className="opacity-0 group-hover:opacity-100 size-6 shrink-0 transition-opacity duration-150 hover:bg-destructive/10"
        onClick={(e) => {
          e.stopPropagation()
          onDelete?.(session.id)
        }}
        onPointerDown={(e) => e.stopPropagation()}
      >
        <Trash2 className="size-3 text-destructive/60" />
      </Button>
    </div>
  )
}
