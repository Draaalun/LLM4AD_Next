import { ChevronLeft, ChevronRight, MoreHorizontal } from "lucide-react"
import { Button } from "@/components/ui/button"

interface PageNumbersProps {
  currentPage: number
  totalPages: number
  onPageChange: (page: number) => void
}

function getPageNumbers(
  current: number,
  total: number,
): (number | "ellipsis")[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i)
  }

  const pages: (number | "ellipsis")[] = [0]

  if (current > 3) {
    pages.push("ellipsis")
  }

  const start = Math.max(1, current - 1)
  const end = Math.min(total - 2, current + 1)

  for (let i = start; i <= end; i++) {
    if (!pages.includes(i)) pages.push(i)
  }

  if (current < total - 4) {
    pages.push("ellipsis")
  }

  if (!pages.includes(total - 1)) {
    pages.push(total - 1)
  }

  return pages
}

export function PageNumbers({
  currentPage,
  totalPages,
  onPageChange,
}: PageNumbersProps) {
  if (totalPages <= 1) return null

  const pages = getPageNumbers(currentPage, totalPages)

  return (
    <div className="flex items-center gap-1">
      <Button
        variant="outline"
        size="icon"
        className="size-7"
        disabled={currentPage === 0}
        onClick={() => onPageChange(currentPage - 1)}
      >
        <ChevronLeft className="size-3.5" />
      </Button>

      {pages.map((p, idx) =>
        p === "ellipsis" ? (
          <span
            key={`e-${idx}`}
            className="flex size-7 items-center justify-center"
          >
            <MoreHorizontal className="size-3.5 text-muted-foreground" />
          </span>
        ) : (
          <Button
            key={p}
            variant={p === currentPage ? "default" : "outline"}
            size="icon"
            className="size-7 text-xs"
            onClick={() => onPageChange(p)}
          >
            {p + 1}
          </Button>
        ),
      )}

      <Button
        variant="outline"
        size="icon"
        className="size-7"
        disabled={currentPage >= totalPages - 1}
        onClick={() => onPageChange(currentPage + 1)}
      >
        <ChevronRight className="size-3.5" />
      </Button>
    </div>
  )
}
