import { AlertCircle, Code2, FileText, Sparkles, Target } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"

import type { BlockRecommendation } from "./types"

interface RecommendDetailDialogProps {
  recommendation: BlockRecommendation | null
  open: boolean
  onOpenChange: (open: boolean) => void
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

export default function RecommendDetailDialog({
  recommendation,
  open,
  onOpenChange,
}: RecommendDetailDialogProps) {
  const { t } = useTranslation()

  if (!recommendation) return null

  const {
    file_path,
    line_start,
    line_end,
    tier,
    size_lines,
    discovery_rationale,
    advice,
    advice_error,
    variant_index,
  } = recommendation

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Target className="size-5 text-primary" />
            {t("evolution.evolveAnnotation.recommendTitle")}
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 min-h-0 overflow-y-auto space-y-4 py-2">
          {/* File location info */}
          <Card className="p-3">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="size-4 text-muted-foreground" />
              <span className="text-sm font-medium">
                {t("evolution.evolveAnnotation.blockRef")}
              </span>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <code className="text-xs bg-muted px-2 py-1 rounded font-mono">
                {file_path}
              </code>
              <Badge variant="outline" className="text-[10px]">
                L{line_start} - L{line_end}
              </Badge>
              <Badge variant="outline" className="text-[10px]">
                {t("evolution.evolveAnnotation.sizeLines", {
                  count: size_lines,
                })}
              </Badge>
              {variant_index != null && (
                <Badge variant="outline" className="text-[10px]">
                  {t("evolution.evolveAnnotation.variant", {
                    index: variant_index,
                  })}
                </Badge>
              )}
            </div>
          </Card>

          {/* Tier & badges */}
          <div className="flex items-center gap-2 flex-wrap">
            <Badge
              variant="secondary"
              className={cn("text-xs px-2 py-0.5", TIER_COLORS[tier])}
            >
              {t(`evolution.evolveAnnotation.tier.${tier}`)}
            </Badge>
            {advice?.feasibility && (
              <Badge
                variant="secondary"
                className={cn(
                  "text-xs px-2 py-0.5",
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
                  "text-xs px-2 py-0.5",
                  SIGNIFICANCE_COLORS[advice.significance],
                )}
              >
                {t(
                  `evolution.evolveAnnotation.significance.${advice.significance}`,
                )}
              </Badge>
            )}
            {advice?.score != null && (
              <Badge variant="outline" className="text-xs px-2 py-0.5">
                {t("evolution.evolveAnnotation.score")}: {advice.score}
              </Badge>
            )}
          </div>

          {/* Discovery rationale */}
          <Card className="p-3">
            <div className="flex items-center gap-2 mb-1.5">
              <Code2 className="size-3.5 text-muted-foreground" />
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                {t("evolution.evolveAnnotation.discoveryRationale")}
              </h4>
            </div>
            <p className="text-sm leading-relaxed">{discovery_rationale}</p>
          </Card>

          {/* Advice error */}
          {advice_error && (
            <Card className="p-3 border-destructive/30 bg-destructive/5">
              <div className="flex items-start gap-2">
                <AlertCircle className="size-4 text-destructive shrink-0 mt-0.5" />
                <p className="text-sm text-destructive">{advice_error}</p>
              </div>
            </Card>
          )}

          {/* Advice details */}
          {advice && (
            <>
              <Separator />

              {/* Block summary */}
              {advice.block_summary && (
                <Card className="p-3">
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1.5">
                    {t("evolution.evolveAnnotation.blockSummary")}
                  </h4>
                  <p className="text-sm leading-relaxed">
                    {advice.block_summary}
                  </p>
                </Card>
              )}

              {/* Rationale */}
              {advice.rationale && (
                <Card className="p-3">
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1.5">
                    {t("evolution.evolveAnnotation.rationale")}
                  </h4>
                  <p className="text-sm leading-relaxed">{advice.rationale}</p>
                </Card>
              )}

              {/* Feasibility & Significance side by side */}
              <div className="grid grid-cols-2 gap-3">
                <Card className="p-3">
                  <div className="flex items-center gap-2 mb-1.5">
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                      {t("evolution.evolveAnnotation.feasibility")}
                    </h4>
                  </div>
                  <p className="text-xs leading-relaxed text-foreground/80">
                    {advice.feasibility_reason}
                  </p>
                </Card>
                <Card className="p-3">
                  <div className="flex items-center gap-2 mb-1.5">
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                      {t("evolution.evolveAnnotation.significanceLabel")}
                    </h4>
                  </div>
                  <p className="text-xs leading-relaxed text-foreground/80">
                    {advice.significance_reason}
                  </p>
                </Card>
              </div>

              {/* Concerns */}
              {advice.concerns.length > 0 && (
                <Card className="p-3">
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                    {t("evolution.evolveAnnotation.concerns")}
                  </h4>
                  <ul className="space-y-1.5">
                    {advice.concerns.map((item, i) => (
                      <li
                        key={i}
                        className="text-xs flex items-start gap-2 text-foreground/80"
                      >
                        <AlertCircle className="size-3 shrink-0 mt-0.5 text-amber-500" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </Card>
              )}

              {/* Suggestions */}
              {advice.suggestions.length > 0 && (
                <Card className="p-3">
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                    {t("evolution.evolveAnnotation.suggestions")}
                  </h4>
                  <ul className="space-y-1.5">
                    {advice.suggestions.map((item, i) => (
                      <li
                        key={i}
                        className="text-xs flex items-start gap-2 text-foreground/80"
                      >
                        <Sparkles className="size-3 shrink-0 mt-0.5 text-primary" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </Card>
              )}

              {/* Block ref from advice */}
              {advice.block_ref && (
                <Card className="p-3">
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1.5">
                    {t("evolution.evolveAnnotation.blockRef")} (Advice)
                  </h4>
                  <code className="text-xs font-mono text-foreground/80">
                    {advice.block_ref.file_path} (L
                    {advice.block_ref.line_start}-{advice.block_ref.line_end})
                    {advice.block_ref.block_name &&
                      ` — ${advice.block_ref.block_name}`}
                  </code>
                </Card>
              )}
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
