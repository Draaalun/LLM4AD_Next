import { useDroppable } from "@dnd-kit/core"
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable"
import {
  ChevronRight,
  Folder,
  MoreHorizontal,
  Pencil,
  Trash2,
} from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"

import type { ResearchSession, SessionGroup } from "./mock-data"
import SessionItem from "./SessionItem"

export default function SessionGroupSection({
  group,
  sessions,
  activeSessionId,
  onToggleCollapse,
  onRename,
  onDelete,
  onSelectSession,
  onDeleteSession,
}: {
  group: SessionGroup
  sessions: ResearchSession[]
  activeSessionId: string | null
  onToggleCollapse: (id: string) => void
  onRename: (id: string, name: string) => void
  onDelete: (id: string) => void
  onSelectSession: (id: string) => void
  onDeleteSession: (id: string) => void
}) {
  const { t } = useTranslation()
  const [isRenaming, setIsRenaming] = useState(false)
  const [renameValue, setRenameValue] = useState(group.name)
  const inputRef = useRef<HTMLInputElement>(null)

  const { setNodeRef, isOver } = useDroppable({ id: group.id })

  const sessionIds = sessions.map((s) => s.id)

  useEffect(() => {
    if (isRenaming) {
      inputRef.current?.focus()
      inputRef.current?.select()
    }
  }, [isRenaming])

  const handleRenameConfirm = () => {
    const trimmed = renameValue.trim()
    if (trimmed && trimmed !== group.name) {
      onRename(group.id, trimmed)
    } else {
      setRenameValue(group.name)
    }
    setIsRenaming(false)
  }

  return (
    <div
      ref={setNodeRef}
      className={`rounded-lg transition-all duration-200 ${
        isOver ? "ring-1.5 ring-primary/30 bg-primary/5" : ""
      }`}
    >
      <div
        className="flex items-center gap-1.5 px-2 py-2 rounded-md hover:bg-muted/50 cursor-pointer group/header transition-colors"
        onClick={() => !isRenaming && onToggleCollapse(group.id)}
      >
        <ChevronRight
          className={`size-3.5 text-muted-foreground/60 transition-transform duration-200 shrink-0 ${
            !group.isCollapsed ? "rotate-90" : ""
          }`}
        />

        <Folder className="size-3.5 text-muted-foreground/50 shrink-0" />

        {isRenaming ? (
          <Input
            ref={inputRef}
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            onBlur={handleRenameConfirm}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleRenameConfirm()
              if (e.key === "Escape") {
                setRenameValue(group.name)
                setIsRenaming(false)
              }
            }}
            onClick={(e) => e.stopPropagation()}
            className="h-6 text-[11px] px-1.5 py-0 border-primary/30 bg-background"
          />
        ) : (
          <span className="text-[11px] font-semibold text-foreground/60 truncate flex-1">
            {group.name}
          </span>
        )}

        <span className="text-[10px] text-muted-foreground/50 shrink-0 tabular-nums">
          {sessions.length}
        </span>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              className="size-5 opacity-0 group-hover/header:opacity-100 transition-opacity shrink-0"
              onClick={(e) => e.stopPropagation()}
            >
              <MoreHorizontal className="size-3.5 text-muted-foreground" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-36">
            <DropdownMenuItem
              onClick={(e) => {
                e.stopPropagation()
                setRenameValue(group.name)
                setIsRenaming(true)
              }}
            >
              <Pencil className="size-3.5 mr-2" />
              {t("research.sidebar.renameGroup")}
            </DropdownMenuItem>
            <DropdownMenuItem
              className="text-destructive focus:text-destructive"
              onClick={(e) => {
                e.stopPropagation()
                onDelete(group.id)
              }}
            >
              <Trash2 className="size-3.5 mr-2" />
              {t("research.sidebar.deleteGroup")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {!group.isCollapsed && (
        <div className="pl-3 pr-0.5 pb-1.5">
          <SortableContext
            items={sessionIds}
            strategy={verticalListSortingStrategy}
          >
            {sessions.length === 0 ? (
              <div className="flex items-center justify-center py-4 px-2">
                <span className="text-[10px] text-muted-foreground/35 italic">
                  {t("research.sidebar.emptyGroup")}
                </span>
              </div>
            ) : (
              <div className="space-y-0.5">
                {sessions.map((session) => (
                  <SessionItem
                    key={session.id}
                    session={session}
                    isActive={session.id === activeSessionId}
                    onSelect={onSelectSession}
                    onDelete={onDeleteSession}
                  />
                ))}
              </div>
            )}
          </SortableContext>
        </div>
      )}
    </div>
  )
}
