import { useTheme } from "@/components/theme-provider"
import { cn } from "@/lib/utils"

import TechCorner from "./TechCorner"

interface TechPanelProps {
  children: React.ReactNode
  className?: string
  cornerSize?: number
  cornerColor?: string
}

export default function TechPanel({
  children,
  className,
  cornerSize = 20,
  cornerColor,
}: TechPanelProps) {
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme === "dark"

  return (
    <div
      className={cn(
        "relative overflow-hidden",
        !isDark && "border border-border/50",
        className,
      )}
      style={
        isDark
          ? {
              boxShadow:
                "inset 0 0 15px color-mix(in srgb, var(--primary) 3%, transparent), 0 0 8px color-mix(in srgb, var(--primary) 5%, transparent)",
            }
          : {
              boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
            }
      }
    >
      <TechCorner position="top-left" size={cornerSize} color={cornerColor} />
      <TechCorner position="top-right" size={cornerSize} color={cornerColor} />
      <TechCorner
        position="bottom-left"
        size={cornerSize}
        color={cornerColor}
      />
      <TechCorner
        position="bottom-right"
        size={cornerSize}
        color={cornerColor}
      />
      {children}
    </div>
  )
}
