import {
  AlertCircle,
  Check,
  ChevronDown,
  ChevronUp,
  Eye,
  Loader2,
  Sparkles,
} from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"

import type { BlockRecommendation } from "./types"

interface RecommendationCardProps {
  recommendation: BlockRecommendation
  selected: boolean
  onSelect: () => void
  onApply?: () => void
  onViewDetail?: () => void
  isApplying?: boolean
  readOnly?: boolean
}

const TIER_COLORS: Record<string, string> = {
  core: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  expanded: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  alternative:
    "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
}

const SIGNIFICANCE_COLORS: Record<string, string> = {
  high: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
  medium:
    "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
  low: "bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-300",
}

const FEASIBILITY_COLORS: Record<string, string> = {
  yes: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
  partial:
    "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
  no: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
}

export default function RecommendationCard({
  recommendation,
  selected,
  onSelect,
  onApply,
  onViewDetail,
  isApplying,
  readOnly,
}: RecommendationCardProps) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)
  const {
    file_path,
    line_start,
    line_end,
    tier,
    size_lines,
    discovery_rationale,
    advice,
    advice_error,
  } = recommendation

  return (
    <Card
      className={cn(
        "p-3 cursor-pointer transition-all border-2 group",
        selected
          ? "border-primary bg-primary/5"
          : "border-transparent hover:border-primary/30",
      )}
      onClick={onSelect}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          {/* File path and line range */}
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono font-medium truncate">
              {file_path.split("/").pop()}
            </span>
            <span className="text-[11px] text-muted-foreground shrink-0">
              L{line_start}-{line_end}
            </span>
            <span className="text-[10px] text-muted-foreground/60">
              {t("evolution.evolveAnnotation.sizeLines", { count: size_lines })}
            </span>
          </div>

          {/* Badges */}
          <div className="flex items-center gap-1.5 mb-2 flex-wrap">
            <Badge
              variant="secondary"
              className={cn("text-[10px] px-1.5 py-0", TIER_COLORS[tier])}
            >
              {t(`evolution.evolveAnnotation.tier.${tier}`)}
            </Badge>
            {advice?.feasibility && (
              <Badge
                variant="secondary"
                className={cn(
                  "text-[10px] px-1.5 py-0",
                  FEASIBILITY_COLORS[advice.feasibility],
                )}
              >
                {t(
                  `evolution.evolveAnnotation.feasibilityValue.${advice.feasibility}`,
                )}
              </Badge>
            )}
            {advice?.significance && (
              <Badge
                variant="secondary"
                className={cn(
                  "text-[10px] px-1.5 py-0",
                  SIGNIFICANCE_COLORS[advice.significance],
                )}
              >
                {t(
                  `evolution.evolveAnnotation.significance.${advice.significance}`,
                )}
              </Badge>
            )}
          </div>

          {/* Discovery rationale */}
          <p className="text-xs text-muted-foreground line-clamp-2">
            {discovery_rationale}
          </p>

          {/* Block summary from advice */}
          {advice?.block_summary && (
            <p className="text-xs mt-1 text-foreground/80 line-clamp-2">
              {advice.block_summary}
            </p>
          )}

          {/* Advice error */}
          {advice_error && (
            <p className="text-xs mt-1 text-destructive line-clamp-2">
              {advice_error}
            </p>
          )}
        </div>

        {/* Selection indicator */}
        <div className="shrink-0 flex flex-col items-center gap-1.5 mt-0.5">
          <div
            className={cn(
              "size-4 rounded-full border-2",
              selected
                ? "border-primary bg-primary"
                : "border-muted-foreground/40",
            )}
          >
            {selected && (
              <div className="size-full flex items-center justify-center">
                <div className="size-1.5 rounded-full bg-white" />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Expandable details */}
      {advice && selected && (
        <div className="mt-2">
          <button
            type="button"
            className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground"
            onClick={(e) => {
              e.stopPropagation()
              setExpanded(!expanded)
            }}
          >
            {expanded ? (
              <ChevronUp className="size-3" />
            ) : (
              <ChevronDown className="size-3" />
            )}
            {expanded
              ? t("evolution.evolveAnnotation.showLess")
              : t("evolution.evolveAnnotation.showMore")}
          </button>

          {expanded && (
            <div className="mt-2 space-y-2 text-[11px]">
              {/* Rationale */}
              {advice.rationale && (
                <p className="text-foreground/80 leading-relaxed">
                  {advice.rationale}
                </p>
              )}

              {/* Concerns */}
              {advice.concerns.length > 0 && (
                <div>
                  <span className="font-medium text-muted-foreground">
                    {t("evolution.evolveAnnotation.concerns")}:
                  </span>
                  <ul className="mt-1 space-y-1">
                    {advice.concerns.map((c, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <AlertCircle className="size-3 shrink-0 mt-0.5 text-amber-500" />
                        <span className="text-foreground/70">{c}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Suggestions */}
              {advice.suggestions.length > 0 && (
                <div>
                  <span className="font-medium text-muted-foreground">
                    {t("evolution.evolveAnnotation.suggestions")}:
                  </span>
                  <ul className="mt-1 space-y-1">
                    {advice.suggestions.map((s, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <Sparkles className="size-3 shrink-0 mt-0.5 text-primary" />
                        <span className="text-foreground/70">{s}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Action buttons */}
      <div className="mt-2 flex justify-end gap-1">
        {onViewDetail && (
          <Button
            variant="ghost"
            size="sm"
            className={cn(
              "h-6 text-[11px] px-2 gap-1 transition-opacity",
              "opacity-40 group-hover:opacity-100",
            )}
            onClick={(e) => {
              e.stopPropagation()
              onViewDetail()
            }}
          >
            <Eye className="size-3" />
            {t("evolution.evolveAnnotation.viewDetail", "Details")}
          </Button>
        )}
        {onApply && !readOnly && (
          <Button
            variant="ghost"
            size="sm"
            className={cn(
              "h-6 text-[11px] px-2 gap-1 transition-opacity",
              "opacity-40 group-hover:opacity-100",
            )}
            onClick={(e) => {
              e.stopPropagation()
              onApply()
            }}
            disabled={isApplying}
          >
            {isApplying ? (
              <Loader2 className="size-3 animate-spin" />
            ) : (
              <Check className="size-3" />
            )}
            {t("evolution.evolveAnnotation.apply")}
          </Button>
        )}
      </div>
    </Card>
  )
}
