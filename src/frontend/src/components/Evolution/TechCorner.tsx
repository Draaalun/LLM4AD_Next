import { useId } from "react"
import { cn } from "@/lib/utils"

interface TechCornerProps {
  position: "top-left" | "top-right" | "bottom-left" | "bottom-right"
  size?: number
  color?: string
  /** Distance from the edge in px */
  inset?: number
  className?: string
}

function getPositionStyle(
  position: TechCornerProps["position"],
  inset: number,
): React.CSSProperties {
  const o = inset
  switch (position) {
    case "top-left":
      return { top: o, left: o }
    case "top-right":
      return { top: o, right: o }
    case "bottom-left":
      return { bottom: o, left: o }
    case "bottom-right":
      return { bottom: o, right: o }
  }
}

const svgTransforms: Record<TechCornerProps["position"], string | undefined> = {
  "top-left": undefined,
  "top-right": "scaleX(-1)",
  "bottom-left": "scaleY(-1)",
  "bottom-right": "scale(-1,-1)",
}

export default function TechCorner({
  position,
  size = 20,
  color = "color-mix(in srgb, var(--primary) 22%, transparent)",
  inset = 4,
  className,
}: TechCornerProps) {
  const uid = useId()
  const gradId = `corner-grad${uid}`

  const r = Math.min(4, size * 0.25) // corner radius
  const d = `M 0 ${size} L 0 ${r} Q 0 0 ${r} 0 L ${size} 0`
  const transform = svgTransforms[position]

  return (
    <div
      className={cn(
        "absolute pointer-events-none opacity-0 dark:opacity-100",
        className,
      )}
      style={getPositionStyle(position, inset)}
      aria-hidden="true"
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={transform ? { transform } : undefined}
      >
        <defs>
          <radialGradient
            id={gradId}
            cx="0"
            cy="0"
            r={size}
            gradientUnits="userSpaceOnUse"
          >
            <stop offset="0%" stopColor={color} stopOpacity={1} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </radialGradient>
        </defs>
        {/* Glow layer */}
        <path
          d={d}
          stroke={`url(#${gradId})`}
          strokeWidth={6}
          fill="none"
          strokeLinecap="round"
          opacity={0.25}
          style={{ filter: "blur(2px)" }}
        />
        {/* Crisp layer */}
        <path
          d={d}
          stroke={`url(#${gradId})`}
          strokeWidth={4}
          fill="none"
          strokeLinecap="round"
        />
      </svg>
    </div>
  )
}
