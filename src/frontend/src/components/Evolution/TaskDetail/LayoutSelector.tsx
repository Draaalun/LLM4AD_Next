import { useTranslation } from "react-i18next"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"
import {
  LAYOUT_I18N_KEYS,
  LAYOUT_TYPES,
  type LayoutType,
} from "./panel-layout-types"

interface LayoutSelectorProps {
  layout: LayoutType
  onLayoutChange: (layout: LayoutType) => void
}

function LayoutIcon({ type }: { type: LayoutType }) {
  const w = 20
  const h = 14
  const s = "currentColor"
  const gap = 1.5

  switch (type) {
    case "1":
      return (
        <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
          <rect
            x={0.5}
            y={0.5}
            width={w - 1}
            height={h - 1}
            rx={1}
            fill="none"
            stroke={s}
            strokeWidth={1}
          />
        </svg>
      )
    case "2h":
      return (
        <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
          <rect
            x={0.5}
            y={0.5}
            width={w / 2 - gap}
            height={h - 1}
            rx={1}
            fill="none"
            stroke={s}
            strokeWidth={1}
          />
          <rect
            x={w / 2 + gap / 2}
            y={0.5}
            width={w / 2 - gap}
            height={h - 1}
            rx={1}
            fill="none"
            stroke={s}
            strokeWidth={1}
          />
        </svg>
      )
    case "2v":
      return (
        <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
          <rect
            x={0.5}
            y={0.5}
            width={w - 1}
            height={h / 2 - gap}
            rx={1}
            fill="none"
            stroke={s}
            strokeWidth={1}
          />
          <rect
            x={0.5}
            y={h / 2 + gap / 2}
            width={w - 1}
            height={h / 2 - gap}
            rx={1}
            fill="none"
            stroke={s}
            strokeWidth={1}
          />
        </svg>
      )
    case "3h": {
      const pw = (w - gap * 2 - 1) / 3
      return (
        <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
          <rect
            x={0.5}
            y={0.5}
            width={pw}
            height={h - 1}
            rx={1}
            fill="none"
            stroke={s}
            strokeWidth={1}
          />
          <rect
            x={0.5 + pw + gap}
            y={0.5}
            width={pw}
            height={h - 1}
            rx={1}
            fill="none"
            stroke={s}
            strokeWidth={1}
          />
          <rect
            x={0.5 + (pw + gap) * 2}
            y={0.5}
            width={pw}
            height={h - 1}
            rx={1}
            fill="none"
            stroke={s}
            strokeWidth={1}
          />
        </svg>
      )
    }
    case "3v": {
      const ph = (h - gap * 2 - 1) / 3
      return (
        <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
          <rect
            x={0.5}
            y={0.5}
            width={w - 1}
            height={ph}
            rx={1}
            fill="none"
            stroke={s}
            strokeWidth={1}
          />
          <rect
            x={0.5}
            y={0.5 + ph + gap}
            width={w - 1}
            height={ph}
            rx={1}
            fill="none"
            stroke={s}
            strokeWidth={1}
          />
          <rect
            x={0.5}
            y={0.5 + (ph + gap) * 2}
            width={w - 1}
            height={ph}
            rx={1}
            fill="none"
            stroke={s}
            strokeWidth={1}
          />
        </svg>
      )
    }
    case "3tb": {
      const topH = (h - gap - 1) / 2
      const botW = (w - gap - 1) / 2
      return (
        <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
          <rect
            x={0.5}
            y={0.5}
            width={w - 1}
            height={topH}
            rx={1}
            fill="none"
            stroke={s}
            strokeWidth={1}
          />
          <rect
            x={0.5}
            y={0.5 + topH + gap}
            width={botW}
            height={topH}
            rx={1}
            fill="none"
            stroke={s}
            strokeWidth={1}
          />
          <rect
            x={0.5 + botW + gap}
            y={0.5 + topH + gap}
            width={botW}
            height={topH}
            rx={1}
            fill="none"
            stroke={s}
            strokeWidth={1}
          />
        </svg>
      )
    }
    case "3lr": {
      const leftW = (w - gap - 1) / 2
      const rightH = (h - gap - 1) / 2
      return (
        <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
          <rect
            x={0.5}
            y={0.5}
            width={leftW}
            height={h - 1}
            rx={1}
            fill="none"
            stroke={s}
            strokeWidth={1}
          />
          <rect
            x={0.5 + leftW + gap}
            y={0.5}
            width={leftW}
            height={rightH}
            rx={1}
            fill="none"
            stroke={s}
            strokeWidth={1}
          />
          <rect
            x={0.5 + leftW + gap}
            y={0.5 + rightH + gap}
            width={leftW}
            height={rightH}
            rx={1}
            fill="none"
            stroke={s}
            strokeWidth={1}
          />
        </svg>
      )
    }
    case "4grid": {
      const gw = (w - gap - 1) / 2
      const gh = (h - gap - 1) / 2
      return (
        <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
          <rect
            x={0.5}
            y={0.5}
            width={gw}
            height={gh}
            rx={1}
            fill="none"
            stroke={s}
            strokeWidth={1}
          />
          <rect
            x={0.5 + gw + gap}
            y={0.5}
            width={gw}
            height={gh}
            rx={1}
            fill="none"
            stroke={s}
            strokeWidth={1}
          />
          <rect
            x={0.5}
            y={0.5 + gh + gap}
            width={gw}
            height={gh}
            rx={1}
            fill="none"
            stroke={s}
            strokeWidth={1}
          />
          <rect
            x={0.5 + gw + gap}
            y={0.5 + gh + gap}
            width={gw}
            height={gh}
            rx={1}
            fill="none"
            stroke={s}
            strokeWidth={1}
          />
        </svg>
      )
    }
  }
}

export default function LayoutSelector({
  layout,
  onLayoutChange,
}: LayoutSelectorProps) {
  const { t } = useTranslation()
  return (
    <DropdownMenu>
      <TooltipProvider delayDuration={200}>
        <Tooltip>
          <TooltipTrigger asChild>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="p-1 rounded text-muted-foreground hover:text-primary transition-colors outline-none"
                aria-label={t("evolution.layout.switchLayout")}
              >
                <LayoutIcon type={layout} />
              </button>
            </DropdownMenuTrigger>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-xs leading-relaxed">
            {t("evolution.layout.switchLayout")}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
      <DropdownMenuContent
        align="end"
        className="bg-popover border-border/60 min-w-0"
      >
        {LAYOUT_TYPES.map((type) => (
          <DropdownMenuItem
            key={type}
            onClick={() => onLayoutChange(type)}
            className={cn(
              "text-xs gap-2 cursor-pointer",
              layout === type
                ? "text-primary"
                : "text-muted-foreground focus:text-primary",
            )}
          >
            <LayoutIcon type={type} />
            {t(LAYOUT_I18N_KEYS[type])}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
