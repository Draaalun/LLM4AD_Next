import * as d3 from "d3"
import { useEffect, useMemo, useRef } from "react"
import { useTranslation } from "react-i18next"
import type { TaskTreeItem } from "@/client"
import { getCSSVar } from "@/utils/theme-colors"

const STATUS_COLORS: Record<string, string> = {
  uninitialized: "#6b7280",
  pending: "#f59e0b",
  running: "#00d4ff",
  completed: "#10b981",
  failed: "#ef4444",
}

const NODE_RADIUS = 14
const LEVEL_WIDTH = 180
const SIBLING_GAP = 56
const MARGIN = { top: 32, right: 120, bottom: 32, left: 80 }

function formatTagFallback(createdTime: string): string {
  const d = new Date(createdTime)
  const pad = (n: number) => String(n).padStart(2, "0")
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`
}

function nodeLabel(item: TaskTreeItem): string {
  return item.tag || formatTagFallback(item.created_time)
}

interface VersionTreeD3Props {
  root: TaskTreeItem
  branches: TaskTreeItem[]
  selectedIds: string[]
  currentId: string | null
  latestId: string | null
  lastModifiedId: string | null
  versionMap: Map<string, number>
  onSelect: (id: string, isMulti: boolean) => void
}

interface HierarchyDatum {
  item: TaskTreeItem
  children?: HierarchyDatum[]
}

function buildHierarchy(
  root: TaskTreeItem,
  branches: TaskTreeItem[],
): HierarchyDatum {
  const childMap = new Map<string, TaskTreeItem[]>()
  for (const c of branches) {
    const pid = c.parent_id ?? root.id
    if (!childMap.has(pid)) childMap.set(pid, [])
    childMap.get(pid)!.push(c)
  }
  const sortByTime = (arr: TaskTreeItem[]) =>
    arr.sort(
      (a, b) =>
        new Date(a.created_time).getTime() - new Date(b.created_time).getTime(),
    )
  function build(item: TaskTreeItem): HierarchyDatum {
    const kids = sortByTime(childMap.get(item.id) ?? [])
    return {
      item,
      children: kids.length > 0 ? kids.map(build) : undefined,
    }
  }
  return build(root)
}

export default function VersionTreeD3({
  root,
  branches,
  selectedIds,
  currentId,
  latestId,
  lastModifiedId,
  versionMap,
  onSelect,
}: VersionTreeD3Props) {
  const { t } = useTranslation()
  const svgRef = useRef<SVGSVGElement | null>(null)
  const wrapperRef = useRef<HTMLDivElement | null>(null)

  const layout = useMemo(() => {
    const data = buildHierarchy(root, branches)
    const hierarchy = d3.hierarchy<HierarchyDatum>(data)
    // nodeSize is [siblingSep, depthSep] in d3-tree coordinates (x, y).
    // For horizontal (left-to-right) rendering, x becomes the vertical axis
    // and y the horizontal axis when drawing.
    const treeLayout = d3
      .tree<HierarchyDatum>()
      .nodeSize([SIBLING_GAP, LEVEL_WIDTH])
    return treeLayout(hierarchy)
  }, [root, branches])

  const { nodes, links, width, height, offsetY } = useMemo(() => {
    const ns = layout.descendants()
    const ls = layout.links()
    let minX = Infinity
    let maxX = -Infinity
    let maxY = -Infinity
    for (const n of ns) {
      if (n.x < minX) minX = n.x
      if (n.x > maxX) maxX = n.x
      if (n.y > maxY) maxY = n.y
    }
    return {
      nodes: ns,
      links: ls,
      width: maxY + MARGIN.left + MARGIN.right,
      height: maxX - minX + MARGIN.top + MARGIN.bottom,
      offsetY: -minX + MARGIN.top,
    }
  }, [layout])

  useEffect(() => {
    if (!svgRef.current || !wrapperRef.current) return

    const svg = d3.select(svgRef.current)
    svg.selectAll("*").remove()

    const primary = getCSSVar("--primary") || "#00d4ff"
    const muted = getCSSVar("--muted-foreground") || "#888"
    const fg = getCSSVar("--foreground") || "#fff"
    const bg = getCSSVar("--background") || "#0a0a0a"

    const root_g = svg
      .append("g")
      .attr("transform", `translate(${MARGIN.left}, ${offsetY})`)

    // Edges (curved, left-to-right)
    const linkGen = d3
      .linkHorizontal<
        d3.HierarchyPointLink<HierarchyDatum>,
        d3.HierarchyPointNode<HierarchyDatum>
      >()
      .x((d) => d.y)
      .y((d) => d.x)

    root_g
      .append("g")
      .attr("class", "edges")
      .selectAll("path")
      .data(links)
      .enter()
      .append("path")
      .attr("d", (d) => linkGen(d) ?? "")
      .attr("fill", "none")
      .attr("stroke", muted)
      .attr("stroke-opacity", 0.45)
      .attr("stroke-width", 1.5)
      .attr("stroke-dasharray", "6 4")

    // Nodes
    const nodeGroup = root_g
      .append("g")
      .attr("class", "nodes")
      .selectAll<SVGGElement, d3.HierarchyPointNode<HierarchyDatum>>("g")
      .data(nodes, (d) => d.data.item.id)
      .enter()
      .append("g")
      .attr("transform", (d) => `translate(${d.y}, ${d.x})`)
      .style("cursor", "pointer")
      .on("click", (event: MouseEvent, d) => {
        const isMulti = event.ctrlKey || event.metaKey
        onSelect(d.data.item.id, isMulti)
      })

    // Outer halo for selected (multi-select)
    nodeGroup
      .append("circle")
      .attr("r", NODE_RADIUS + 6)
      .attr("fill", "none")
      .attr("stroke", primary)
      .attr("stroke-width", 2)
      .attr("stroke-opacity", (d) =>
        selectedIds.includes(d.data.item.id) ? 0.7 : 0,
      )

    // Status base circle
    nodeGroup
      .append("circle")
      .attr("r", NODE_RADIUS)
      .attr(
        "fill",
        (d) => STATUS_COLORS[d.data.item.status] ?? STATUS_COLORS.uninitialized,
      )
      .attr("fill-opacity", 0.18)
      .attr("stroke", (d) => {
        if (d.data.item.id === currentId) return primary
        return STATUS_COLORS[d.data.item.status] ?? STATUS_COLORS.uninitialized
      })
      .attr("stroke-width", (d) => (d.data.item.id === currentId ? 3 : 1.5))

    // Version label inside circle
    nodeGroup
      .append("text")
      .attr("text-anchor", "middle")
      .attr("dominant-baseline", "central")
      .attr("font-size", 10)
      .attr("font-family", "monospace")
      .attr("fill", fg)
      .text((d) => `v${versionMap.get(d.data.item.id) ?? "?"}`)

    // Latest badge — top right (emerald dot)
    nodeGroup
      .filter((d) => d.data.item.id === latestId)
      .append("circle")
      .attr("cx", NODE_RADIUS - 2)
      .attr("cy", -NODE_RADIUS + 2)
      .attr("r", 4)
      .attr("fill", "#10b981")
      .attr("stroke", bg)
      .attr("stroke-width", 1.5)

    // Last-modified badge — top left (amber dot)
    nodeGroup
      .filter((d) => d.data.item.id === lastModifiedId)
      .append("circle")
      .attr("cx", -NODE_RADIUS + 2)
      .attr("cy", -NODE_RADIUS + 2)
      .attr("r", 4)
      .attr("fill", "#f59e0b")
      .attr("stroke", bg)
      .attr("stroke-width", 1.5)

    // Tag/timestamp label to the right of circle
    nodeGroup
      .append("text")
      .attr("x", NODE_RADIUS + 8)
      .attr("y", 0)
      .attr("text-anchor", "start")
      .attr("dominant-baseline", "central")
      .attr("font-size", 11)
      .attr("fill", fg)
      .text((d) => {
        const label = nodeLabel(d.data.item)
        return label.length > 18 ? `${label.slice(0, 17)}…` : label
      })
      .append("title")
      .text((d) => {
        const item = d.data.item
        const lines = [
          nodeLabel(item),
          `v${versionMap.get(item.id) ?? "?"}`,
          `status: ${item.status}`,
          `created: ${new Date(item.created_time).toLocaleString()}`,
          `updated: ${new Date(item.updated_time).toLocaleString()}`,
        ]
        return lines.join("\n")
      })

    // Badge labels (latest / last-modified) — second line under main label
    nodeGroup
      .filter(
        (d) => d.data.item.id === latestId || d.data.item.id === lastModifiedId,
      )
      .append("text")
      .attr("x", NODE_RADIUS + 8)
      .attr("y", 14)
      .attr("text-anchor", "start")
      .attr("dominant-baseline", "central")
      .attr("font-size", 9)
      .attr("fill", muted)
      .text((d) => {
        const labels: string[] = []
        if (d.data.item.id === latestId)
          labels.push(t("evolution.versionTree.latestLabel"))
        if (d.data.item.id === lastModifiedId)
          labels.push(t("evolution.versionCompare.lastModifiedLabel"))
        return labels.join(" · ")
      })
  }, [
    nodes,
    links,
    offsetY,
    selectedIds,
    currentId,
    latestId,
    lastModifiedId,
    versionMap,
    onSelect,
    t,
  ])

  return (
    <div className="flex flex-col gap-2 w-full h-full">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[11px] text-muted-foreground shrink-0">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block size-2.5 rounded-full border-[2px] border-primary bg-primary/15" />
          {t("evolution.versionCompare.legendCurrent")}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block size-2 rounded-full bg-emerald-500" />
          {t("evolution.versionCompare.legendLatest")}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block size-2 rounded-full bg-amber-500" />
          {t("evolution.versionCompare.legendLastModified")}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block size-3 rounded-full ring-2 ring-primary/70 ring-offset-1 ring-offset-background" />
          {t("evolution.versionCompare.legendSelected")}
        </span>
        <span className="ml-auto italic">
          {t("evolution.versionCompare.selectHint")}
        </span>
      </div>
      <div
        ref={wrapperRef}
        className="flex-1 min-h-0 overflow-auto bg-muted/20 rounded border border-border/40"
      >
        <svg
          ref={svgRef}
          width={Math.max(width, 600)}
          height={Math.max(height, 200)}
          className="block"
        >
          <title>{t("evolution.versionCompare.title")}</title>
        </svg>
      </div>
    </div>
  )
}
