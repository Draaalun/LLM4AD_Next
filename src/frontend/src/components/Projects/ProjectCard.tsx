import { useNavigate } from "@tanstack/react-router"
import { ArrowRight, Calendar, EllipsisVertical } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"

import type { ProjectResponse } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { formatDate } from "@/lib/utils"
import DeleteProject from "./DeleteProject"
import EditProject from "./EditProject"
import { getProjectIcon } from "./ProjectIcons"

interface ProjectCardProps {
  project: ProjectResponse
}

export default function ProjectCard({ project }: ProjectCardProps) {
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const { t } = useTranslation()
  const Icon = getProjectIcon(project.icon)

  const handleEnter = () => {
    navigate({ to: "/evolution", search: { projectId: project.id } })
  }

  return (
    <Card
      onClick={handleEnter}
      className="group relative overflow-hidden cursor-pointer transition-all duration-200 hover:border-primary/60 hover:shadow-lg hover:shadow-primary/10 hover:-translate-y-0.5"
    >
      {/* Decorative gradient accent (top-right corner) */}
      <div
        className="pointer-events-none absolute -top-12 -right-12 size-32 rounded-full bg-primary/10 blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"
        aria-hidden="true"
      />

      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-1.5 pt-4 px-4">
        <div className="flex items-center gap-2.5 min-w-0 pr-2">
          <div className="shrink-0 size-8 rounded-md bg-primary/10 text-primary flex items-center justify-center transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3">
            <Icon className="size-4.5" />
          </div>
          <CardTitle className="text-sm font-semibold leading-tight truncate">
            {project.name}
          </CardTitle>
        </div>
        <DropdownMenu open={menuOpen} onOpenChange={setMenuOpen}>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="size-8 shrink-0 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity z-20"
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
            <EditProject
              project={project}
              onSuccess={() => setMenuOpen(false)}
            />
            <DeleteProject
              id={project.id}
              name={project.name}
              onSuccess={() => setMenuOpen(false)}
            />
          </DropdownMenuContent>
        </DropdownMenu>
      </CardHeader>

      <CardContent className="pb-3 px-4">
        <p className="text-sm text-muted-foreground line-clamp-2 min-h-[2.5rem]">
          {project.description || t("projects.noDescription")}
        </p>
      </CardContent>

      <CardFooter className="pt-0 pb-3 px-4 flex items-center justify-between gap-2">
        <div className="flex items-center text-xs text-muted-foreground min-w-0">
          <Calendar className="size-3 mr-1.5 shrink-0" />
          <span className="truncate">{formatDate(project.created_time)}</span>
        </div>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            handleEnter()
          }}
          className="relative shrink-0 inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-medium text-muted-foreground border border-border bg-background transition-all duration-300 group-hover:bg-primary group-hover:text-primary-foreground group-hover:border-primary hover:opacity-90 active:scale-95"
        >
          <span>{t("projects.enterProject")}</span>
          <ArrowRight className="size-3.5 transition-transform duration-300 group-hover:translate-x-0.5" />
        </button>
      </CardFooter>
    </Card>
  )
}
