import { Label } from "@/components/ui/label"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

export default function FieldLabel({
  label,
  description,
  required,
}: {
  label: string
  description?: string
  required?: boolean
}) {
  const requiredMark = required ? (
    <span className="text-destructive ml-1">*</span>
  ) : null

  if (!description) {
    return (
      <Label>
        {label}
        {requiredMark}
      </Label>
    )
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="text-sm font-medium leading-none cursor-help border-b border-dotted border-muted-foreground/50 inline-flex items-center">
          {label}
          {requiredMark}
        </span>
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-xs">
        {description}
      </TooltipContent>
    </Tooltip>
  )
}
