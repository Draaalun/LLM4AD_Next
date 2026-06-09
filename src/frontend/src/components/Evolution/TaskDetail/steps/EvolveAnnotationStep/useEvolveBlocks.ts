import { useMemo } from "react"

import type { EvolveBlockPosition } from "./types"

const EVOLVE_START_RE =
  /(?:#|\/\/|\/\*|<!--)\s*EVOLVE[_\s-]START\b.*?(?:\*\/|-->)?/i
const EVOLVE_END_RE =
  /(?:#|\/\/|\/\*|<!--)\s*EVOLVE[_\s-]END\b.*?(?:\*\/|-->)?/i

export function parseEvolveBlocks(content: string): EvolveBlockPosition[] {
  const lines = content.split("\n")
  const blocks: EvolveBlockPosition[] = []
  let currentStart: { line: number; marker: string } | null = null

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    if (EVOLVE_START_RE.test(line)) {
      currentStart = { line: i + 1, marker: line.trim() }
    } else if (EVOLVE_END_RE.test(line) && currentStart) {
      blocks.push({
        startLine: currentStart.line,
        endLine: i + 1,
        startMarker: currentStart.marker,
        endMarker: line.trim(),
      })
      currentStart = null
    }
  }

  return blocks
}

export function useEvolveBlocks(content: string | null) {
  return useMemo(() => {
    if (!content) return { blocks: [] as EvolveBlockPosition[], count: 0 }
    const blocks = parseEvolveBlocks(content)
    return { blocks, count: blocks.length }
  }, [content])
}

export function countEvolveBlocksInContent(content: string): number {
  return parseEvolveBlocks(content).length
}
