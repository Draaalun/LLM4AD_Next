import { useSuspenseQuery } from "@tanstack/react-query"
import { useState } from "react"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar"
import useAuth from "@/hooks/useAuth"
import { User } from "../Sidebar/User"
import { getProjectsQueryOptions, Project } from "./Project"
import { Task } from "./Task"

export function AppSidebar() {
  const { user: currentUser } = useAuth()
  const { data: projects } = useSuspenseQuery(getProjectsQueryOptions())
  const [selectedProjectId, setSelectedProjectId] = useState<string>(
    () => projects.items[0]?.id ?? "",
  )

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-4 py-6 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:items-center">
        <Project
          selectedProjectId={selectedProjectId}
          onSelectProject={setSelectedProjectId}
        />
      </SidebarHeader>
      <SidebarContent>
        <Task projectId={selectedProjectId} />
      </SidebarContent>
      <SidebarFooter>
        <User user={currentUser} />
      </SidebarFooter>
    </Sidebar>
  )
}

export default AppSidebar
