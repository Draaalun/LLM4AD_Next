import type React from "react"

export function MarkdownRenderer({ content }: { content: string }) {
  const lines = content.split("\n")
  const elements: React.ReactNode[] = []
  let inCodeBlock = false
  let codeContent = ""
  let codeKey = 0

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]

    if (line.startsWith("```")) {
      if (inCodeBlock) {
        elements.push(
          <pre
            key={`code-${codeKey++}`}
            className="rounded-lg p-3 text-xs overflow-x-auto bg-muted/60 border border-border/50 my-3"
          >
            <code>{codeContent.trim()}</code>
          </pre>,
        )
        codeContent = ""
        inCodeBlock = false
      } else {
        inCodeBlock = true
      }
      continue
    }

    if (inCodeBlock) {
      codeContent += `${line}\n`
      continue
    }

    if (line.startsWith("### ")) {
      elements.push(
        <h3
          key={i}
          className="text-base font-semibold mt-5 mb-2 text-foreground"
        >
          {line.slice(4)}
        </h3>,
      )
    } else if (line.startsWith("## ")) {
      elements.push(
        <h2 key={i} className="text-lg font-bold mt-6 mb-2 text-foreground">
          {line.slice(3)}
        </h2>,
      )
    } else if (line.startsWith("# ")) {
      elements.push(
        <h1 key={i} className="text-xl font-bold mt-7 mb-3 text-foreground">
          {line.slice(2)}
        </h1>,
      )
    } else if (line.startsWith("- ") || line.startsWith("* ")) {
      elements.push(
        <li
          key={i}
          className="ml-5 text-sm text-foreground/80 list-disc leading-relaxed"
        >
          {renderInline(line.slice(2))}
        </li>,
      )
    } else if (/^\d+\.\s/.test(line)) {
      elements.push(
        <li
          key={i}
          className="ml-5 text-sm text-foreground/80 list-decimal leading-relaxed"
        >
          {renderInline(line.replace(/^\d+\.\s/, ""))}
        </li>,
      )
    } else if (line.startsWith("|")) {
      const cells = line
        .split("|")
        .filter(Boolean)
        .map((c) => c.trim())
      if (cells.every((c) => /^[-:]+$/.test(c))) continue
      elements.push(
        <div
          key={i}
          className="flex gap-4 text-xs py-1.5 border-b border-border/30 px-1"
        >
          {cells.map((cell, ci) => (
            <span key={ci} className="flex-1 text-foreground/70">
              {renderInline(cell)}
            </span>
          ))}
        </div>,
      )
    } else if (line.trim() === "") {
      elements.push(<div key={i} className="h-2" />)
    } else {
      elements.push(
        <p key={i} className="text-sm text-foreground/80 leading-relaxed">
          {renderInline(line)}
        </p>,
      )
    }
  }

  return <>{elements}</>
}

function renderInline(text: string): React.ReactNode {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={i}
          className="px-1.5 py-0.5 rounded-md bg-primary/10 text-primary text-xs font-mono"
        >
          {part.slice(1, -1)}
        </code>
      )
    }
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={i} className="font-semibold text-foreground">
          {part.slice(2, -2)}
        </strong>
      )
    }
    return part
  })
}
