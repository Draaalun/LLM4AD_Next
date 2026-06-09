import mermaid from "mermaid"
import { useEffect, useRef, useState } from "react"

import { useTheme } from "@/components/theme-provider"
import { cn } from "@/lib/utils"

mermaid.initialize({
  startOnLoad: false,
  securityLevel: "loose",
})

interface MermaidDiagramProps {
  id: string
  chart: string
}

export function MermaidDiagram({ id, chart }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)
  const { resolvedTheme } = useTheme()

  const hasCustomFills = /style\s+\w+\s+fill:/i.test(chart)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    let cancelled = false

    mermaid.initialize({
      startOnLoad: false,
      securityLevel: "loose",
      theme: resolvedTheme === "dark" ? "dark" : "default",
    })

    mermaid
      .render(id.replace(/[^a-zA-Z0-9-]/g, ""), chart)
      .then(({ svg }) => {
        if (cancelled) return
        el.innerHTML = svg
        setError(null)
      })
      .catch((err) => {
        if (cancelled) return
        setError(String(err))
      })

    return () => {
      cancelled = true
    }
  }, [id, chart, resolvedTheme])

  if (error) {
    return (
      <pre className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive overflow-x-auto">
        {chart}
      </pre>
    )
  }

  return (
    <div
      ref={containerRef}
      className={cn(
        "my-4 flex justify-center [&_svg]:max-w-full",
        resolvedTheme === "dark" &&
          hasCustomFills &&
          "[&_.nodeLabel]:!text-[#1a1a2e] [&_.nodeLabel_p]:!text-[#1a1a2e] [&_.label_foreignObject_div]:!text-[#1a1a2e]",
      )}
    />
  )
}
