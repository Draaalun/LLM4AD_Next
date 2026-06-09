import Markdown from "react-markdown"
import remarkGfm from "remark-gfm"

interface ReportMarkdownProps {
  content: string
  className?: string
}

export default function ReportMarkdown({
  content,
  className,
}: ReportMarkdownProps) {
  return (
    <div
      className={`prose prose-sm dark:prose-invert max-w-none
        prose-headings:text-foreground prose-headings:font-semibold
        prose-h1:text-xl prose-h1:border-b prose-h1:border-border/50 prose-h1:pb-2
        prose-h2:text-lg prose-h2:mt-6
        prose-h3:text-base
        prose-p:text-foreground/80 prose-p:leading-relaxed
        prose-strong:text-foreground
        prose-a:text-primary prose-a:no-underline hover:prose-a:underline
        prose-code:text-primary prose-code:bg-muted prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-code:before:content-none prose-code:after:content-none
        prose-pre:bg-muted prose-pre:border prose-pre:border-border/50 prose-pre:rounded-lg
        prose-table:text-sm
        prose-th:bg-muted/50 prose-th:px-3 prose-th:py-2 prose-th:text-left prose-th:font-semibold prose-th:border-border
        prose-td:px-3 prose-td:py-2 prose-td:border-border
        prose-li:text-foreground/80
        prose-blockquote:border-primary/30 prose-blockquote:text-foreground/70
        prose-hr:border-border/50
        ${className ?? ""}`}
    >
      <Markdown remarkPlugins={[remarkGfm]}>{content}</Markdown>
    </div>
  )
}
