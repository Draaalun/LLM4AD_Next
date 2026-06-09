import { useNavigate } from "@tanstack/react-router"
import { ArrowRight, Calendar, EllipsisVertical } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"

import type { ProjectResponse } from "@/client"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { formatDate } from "@/lib/utils"
import DeleteProject from "./DeleteProject"
import EditProject from "./EditProject"
import { getProjectIcon } from "./ProjectIcons"

interface ProjectListItemProps {
  project: ProjectResponse
}

export default function ProjectListItem({ project }: ProjectListItemProps) {
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const { t } = useTranslation()
  const Icon = getProjectIcon(project.icon)

  const handleEnter = () => {
    navigate({ to: "/evolution", search: { projectId: project.id } })
  }

  return (
    <div
      onClick={handleEnter}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault()
          handleEnter()
        }
      }}
      role="button"
      tabIndex={0}
      className="group relative flex items-center gap-4 rounded-lg border bg-card px-4 py-3 cursor-pointer transition-all duration-200 hover:border-primary/60 hover:shadow-md hover:shadow-primary/10"
    >
      <div className="shrink-0 size-10 rounded-md bg-primary/10 text-primary flex items-center justify-center transition-transform duration-300 group-hover:scale-110">
        <Icon className="size-5" />
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 min-w-0">
          <h3 className="text-sm font-semibold truncate">{project.name}</h3>
        </div>
        <p className="mt-0.5 text-xs text-muted-foreground line-clamp-1">
          {project.description || t("projects.noDescription")}
        </p>
      </div>

      <div className="shrink-0 hidden sm:flex flex-col items-end gap-0.5 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <Calendar className="size-3" />
          <span>{formatDate(project.created_time)}</span>
        </div>
        {project.updated_time !== project.created_time && (
          <span className="text-[11px] text-muted-foreground/60">
            {t("projects.lastUpdated", {
              time: formatDate(project.updated_time),
            })}
          </span>
        )}
      </div>

      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation()
          handleEnter()
        }}
        className="shrink-0 inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-medium text-muted-foreground border border-border bg-background transition-all duration-300 hover:text-primary hover:border-primary/40 active:scale-95"
      >
        <span>{t("projects.enterProject")}</span>
        <ArrowRight className="size-3.5" />
      </button>

      <DropdownMenu open={menuOpen} onOpenChange={setMenuOpen}>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="size-8 shrink-0 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity"
            onClick={(e) => e.stopPropagation()}
          >
            <EllipsisVertical className="size-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          align="end"
          className="z-30"
          onClick={(e) => e.stopPropagation()}
        >
          <EditProject project={project} onSuccess={() => setMenuOpen(false)} />
          <DeleteProject
            id={project.id}
            name={project.name}
            onSuccess={() => setMenuOpen(false)}
          />
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}
