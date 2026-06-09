import { createFileRoute } from "@tanstack/react-router"

export const Route = createFileRoute("/_layout/config_template")({
  component: RouteComponent,
})

function RouteComponent() {
  return <div>Hello "/_layout/config_template"!</div>
}
