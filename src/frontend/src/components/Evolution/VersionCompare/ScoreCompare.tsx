import { useQueries } from "@tanstack/react-query"
import * as d3 from "d3"
import { useEffect, useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import type { TaskTreeItem } from "@/client"
import { Llm4AdTasksService } from "@/client"
import { taskKeys } from "@/lib/task-queries"
import { getCSSVar } from "@/utils/theme-colors"

interface ScoreCompareProps {
  selectedItems: TaskTreeItem[]
  versionMap: Map<string, number>
}

type ChartMode = "bar" | "radar"

const PALETTE = [
  "#00d4ff",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#a78bfa",
  "#ec4899",
  "#22d3ee",
  "#84cc16",
]

interface NodeStats {
  id: string
  label: string
  solution_count: number
  avg_score: number
  max_score: number
}

function labelFor(item: TaskTreeItem, version: number | undefined): string {
  const pad = (n: number) => String(n).padStart(2, "0")
  const fallback = (() => {
    const d = new Date(item.created_time)
    return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`
  })()
  const tag = item.tag || fallback
  return version !== undefined ? `v${version} · ${tag}` : tag
}

function formatNum(v: number): string {
  if (Number.isNaN(v)) return "-"
  return v.toFixed(4)
}

function GroupedBar({
  data,
  dims,
}: {
  data: NodeStats[]
  dims: { key: keyof NodeStats; label: string }[]
}) {
  const ref = useRef<SVGSVGElement | null>(null)
  const wrapperRef = useRef<HTMLDivElement | null>(null)
  const [size, setSize] = useState({ w: 600, h: 320 })

  useEffect(() => {
    const el = wrapperRef.current
    if (!el) return
    const obs = new ResizeObserver((entries) => {
      for (const e of entries) {
        const cr = e.contentRect
        setSize({ w: Math.max(360, cr.width), h: Math.max(240, cr.height) })
      }
    })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  useEffect(() => {
    if (!ref.current) return
    const svg = d3.select(ref.current)
    svg.selectAll("*").remove()

    const fg = getCSSVar("--foreground") || "#fff"
    const muted = getCSSVar("--muted-foreground") || "#888"

    const { w: width, h: height } = size
    const margin = { top: 30, right: 20, bottom: 60, left: 20 }
    const innerW = width - margin.left - margin.right
    const innerH = height - margin.top - margin.bottom

    const g = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`)

    const x0 = d3
      .scaleBand<string>()
      .domain(dims.map((d) => d.label))
      .range([0, innerW])
      .padding(0.2)

    const x1 = d3
      .scaleBand<string>()
      .domain(data.map((d) => d.id))
      .range([0, x0.bandwidth()])
      .padding(0.08)

    // X axis only (no Y axis ticks)
    g.append("g")
      .attr("transform", `translate(0,${innerH})`)
      .call(d3.axisBottom(x0).tickSize(0))
      .call((sel) => {
        sel.selectAll("path").attr("stroke", muted)
        sel.selectAll("line").remove()
        sel.selectAll("text").attr("fill", fg).attr("font-size", 11)
      })

    // Tooltip
    const tooltip = d3
      .select(wrapperRef.current)
      .append("div")
      .attr(
        "class",
        "pointer-events-none absolute z-10 px-2 py-1 rounded text-xs bg-background border border-border/60 shadow-md",
      )
      .style("opacity", "0")

    // Bars per dimension group
    for (const dim of dims) {
      const values = data.map((d) => d[dim.key] as number)
      const isNonNegative = dim.key === "solution_count"

      const maxAbs = d3.max(values.map(Math.abs)) || 1
      const domainMin = isNonNegative ? 0 : -maxAbs
      const domainMax = maxAbs

      const y = d3
        .scaleLinear()
        .domain([domainMin, domainMax])
        .range([innerH, 0])
      const baseline = y(0)

      const groupG = g
        .append("g")
        .attr("transform", `translate(${x0(dim.label) ?? 0},0)`)

      groupG
        .selectAll("rect")
        .data(data)
        .enter()
        .append("rect")
        .attr("x", (d) => x1(d.id) ?? 0)
        .attr("width", x1.bandwidth())
        .attr("y", (d) => {
          const v = d[dim.key] as number
          if (isNonNegative) return v === 0 ? baseline : y(v)
          return v >= 0 ? y(v) : baseline
        })
        .attr("height", (d) => {
          const v = d[dim.key] as number
          if (isNonNegative) return v === 0 ? 0 : baseline - y(v)
          return Math.abs(y(v) - baseline)
        })
        .attr("fill", (_d, i) => PALETTE[i % PALETTE.length])
        .attr("rx", 2)
        .on("mouseenter", (event, d) => {
          const v = d[dim.key] as number
          tooltip
            .html(
              `<div class="font-medium">${d.label}</div><div class="text-muted-foreground">${dim.label}: ${formatNum(v)}</div>`,
            )
            .style("opacity", "1")
          const rect = wrapperRef.current?.getBoundingClientRect()
          if (rect) {
            tooltip
              .style("left", `${event.clientX - rect.left + 10}px`)
              .style("top", `${event.clientY - rect.top + 10}px`)
          }
        })
        .on("mousemove", (event) => {
          const rect = wrapperRef.current?.getBoundingClientRect()
          if (rect) {
            tooltip
              .style("left", `${event.clientX - rect.left + 10}px`)
              .style("top", `${event.clientY - rect.top + 10}px`)
          }
        })
        .on("mouseleave", () => {
          tooltip.style("opacity", "0")
        })

      // Value labels on top of each bar
      groupG
        .selectAll("text.val")
        .data(data)
        .enter()
        .append("text")
        .attr("class", "val")
        .attr("x", (d) => (x1(d.id) ?? 0) + x1.bandwidth() / 2)
        .attr("y", (d) => {
          const v = d[dim.key] as number
          if (isNonNegative) return v === 0 ? baseline - 4 : y(v) - 4
          return v >= 0 ? y(v) - 4 : y(v) + 12
        })
        .attr("text-anchor", "middle")
        .attr("font-size", 10)
        .attr("fill", fg)
        .text((d) => formatNum(d[dim.key] as number))
    }

    return () => {
      tooltip.remove()
    }
  }, [data, dims, size])

  return (
    <div ref={wrapperRef} className="relative w-full h-full">
      <svg ref={ref} width={size.w} height={size.h} className="block" />
    </div>
  )
}

function Radar({
  data,
  dims,
}: {
  data: NodeStats[]
  dims: { key: keyof NodeStats; label: string }[]
}) {
  const ref = useRef<SVGSVGElement | null>(null)
  const wrapperRef = useRef<HTMLDivElement | null>(null)
  const [size, setSize] = useState({ w: 480, h: 360 })

  useEffect(() => {
    const el = wrapperRef.current
    if (!el) return
    const obs = new ResizeObserver((entries) => {
      for (const e of entries) {
        const cr = e.contentRect
        setSize({ w: Math.max(320, cr.width), h: Math.max(280, cr.height) })
      }
    })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  useEffect(() => {
    if (!ref.current) return
    const svg = d3.select(ref.current)
    svg.selectAll("*").remove()

    const fg = getCSSVar("--foreground") || "#fff"
    const muted = getCSSVar("--muted-foreground") || "#888"

    const { w: width, h: height } = size
    const cx = width / 2
    const cy = height / 2 + 10
    const radius = Math.min(width, height) / 2 - 60

    const g = svg.append("g").attr("transform", `translate(${cx}, ${cy})`)

    // Per-dim normalized values
    const dimRanges = new Map<string, { min: number; max: number }>()
    for (const dim of dims) {
      const values = data.map((d) => d[dim.key] as number)
      const mn = d3.min(values) ?? 0
      const mx = d3.max(values) ?? 1
      dimRanges.set(dim.label, { min: mn, max: mx })
    }

    const angleStep = (Math.PI * 2) / dims.length
    const angleFor = (i: number) => -Math.PI / 2 + i * angleStep

    // Background rings
    const rings = [0.25, 0.5, 0.75, 1]
    for (const r of rings) {
      g.append("polygon")
        .attr(
          "points",
          dims
            .map((_, i) => {
              const a = angleFor(i)
              return `${Math.cos(a) * radius * r},${Math.sin(a) * radius * r}`
            })
            .join(" "),
        )
        .attr("fill", "none")
        .attr("stroke", muted)
        .attr("stroke-opacity", 0.25)
        .attr("stroke-width", 1)
    }

    // Axes
    dims.forEach((_, i) => {
      const a = angleFor(i)
      g.append("line")
        .attr("x1", 0)
        .attr("y1", 0)
        .attr("x2", Math.cos(a) * radius)
        .attr("y2", Math.sin(a) * radius)
        .attr("stroke", muted)
        .attr("stroke-opacity", 0.4)
    })

    // Dim labels
    dims.forEach((d, i) => {
      const a = angleFor(i)
      const lx = Math.cos(a) * (radius + 18)
      const ly = Math.sin(a) * (radius + 18)
      g.append("text")
        .attr("x", lx)
        .attr("y", ly)
        .attr("text-anchor", "middle")
        .attr("dominant-baseline", "central")
        .attr("font-size", 11)
        .attr("fill", fg)
        .text(d.label)
    })

    // Tooltip
    const tooltip = d3
      .select(wrapperRef.current)
      .append("div")
      .attr(
        "class",
        "pointer-events-none absolute z-10 px-2 py-1 rounded text-xs bg-background border border-border/60 shadow-md",
      )
      .style("opacity", "0")

    // Polygons per node
    data.forEach((node, idx) => {
      const color = PALETTE[idx % PALETTE.length]
      const pts = dims.map((dim, i) => {
        const range = dimRanges.get(dim.label)!
        const v = node[dim.key] as number
        const norm =
          range.max > range.min
            ? (v - range.min) / (range.max - range.min)
            : 0.5
        const a = angleFor(i)
        return [Math.cos(a) * radius * norm, Math.sin(a) * radius * norm] as [
          number,
          number,
        ]
      })

      g.append("polygon")
        .attr("points", pts.map((p) => p.join(",")).join(" "))
        .attr("fill", color)
        .attr("fill-opacity", 0.12)
        .attr("stroke", color)
        .attr("stroke-width", 2)

      pts.forEach(([px, py], i) => {
        const dim = dims[i]
        const v = node[dim.key] as number
        g.append("circle")
          .attr("cx", px)
          .attr("cy", py)
          .attr("r", 3.5)
          .attr("fill", color)
          .style("cursor", "pointer")
          .on("mouseenter", (event) => {
            tooltip
              .html(
                `<div class="font-medium">${node.label}</div><div class="text-muted-foreground">${dim.label}: ${formatNum(v)}</div>`,
              )
              .style("opacity", "1")
            const rect = wrapperRef.current?.getBoundingClientRect()
            if (rect) {
              tooltip
                .style("left", `${event.clientX - rect.left + 10}px`)
                .style("top", `${event.clientY - rect.top + 10}px`)
            }
          })
          .on("mousemove", (event) => {
            const rect = wrapperRef.current?.getBoundingClientRect()
            if (rect) {
              tooltip
                .style("left", `${event.clientX - rect.left + 10}px`)
                .style("top", `${event.clientY - rect.top + 10}px`)
            }
          })
          .on("mouseleave", () => {
            tooltip.style("opacity", "0")
          })
      })
    })

    return () => {
      tooltip.remove()
    }
  }, [data, dims, size])

  return (
    <div ref={wrapperRef} className="relative w-full h-full">
      <svg ref={ref} width={size.w} height={size.h} className="block" />
    </div>
  )
}

export default function ScoreCompare({
  selectedItems,
  versionMap,
}: ScoreCompareProps) {
  const { t } = useTranslation()
  const [mode, setMode] = useState<ChartMode>("bar")

  const queries = useQueries({
    queries: selectedItems.map((item) => ({
      queryKey: taskKeys.stats(item.id),
      queryFn: () => Llm4AdTasksService.getTaskStats({ taskId: item.id }),
      staleTime: 30_000,
    })),
  })

  const isLoading = queries.some((q) => q.isLoading)

  const data: NodeStats[] = useMemo(() => {
    return selectedItems.map((item, idx) => {
      const stats = queries[idx]?.data
      return {
        id: item.id,
        label: labelFor(item, versionMap.get(item.id)),
        solution_count: stats?.solution_count ?? 0,
        avg_score: stats?.avg_score ?? 0,
        max_score: stats?.max_score ?? 0,
      }
    })
  }, [selectedItems, queries, versionMap])

  const dims: { key: keyof NodeStats; label: string }[] = [
    {
      key: "solution_count",
      label: t("evolution.versionCompare.dimSolutions"),
    },
    { key: "avg_score", label: t("evolution.versionCompare.dimAvg") },
    { key: "max_score", label: t("evolution.versionCompare.dimMax") },
  ]

  if (selectedItems.length < 1) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        {t("evolution.versionCompare.selectAtLeast2")}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2 h-full">
      <div className="flex items-center gap-2 text-xs">
        <div className="inline-flex rounded border border-border/60 overflow-hidden">
          <button
            type="button"
            onClick={() => setMode("bar")}
            className={`px-3 py-1 transition-colors ${
              mode === "bar"
                ? "bg-primary/15 text-primary"
                : "hover:bg-accent/60 text-muted-foreground"
            }`}
          >
            {t("evolution.versionCompare.chartBar")}
          </button>
          <button
            type="button"
            onClick={() => setMode("radar")}
            className={`px-3 py-1 transition-colors border-l border-border/60 ${
              mode === "radar"
                ? "bg-primary/15 text-primary"
                : "hover:bg-accent/60 text-muted-foreground"
            }`}
          >
            {t("evolution.versionCompare.chartRadar")}
          </button>
        </div>
        {isLoading && (
          <span className="text-muted-foreground">
            {t("evolution.versionCompare.loading")}
          </span>
        )}
        <div className="ml-auto flex flex-wrap gap-2">
          {data.map((d, i) => (
            <span
              key={d.id}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-muted/50"
            >
              <span
                className="size-2 rounded-full"
                style={{ background: PALETTE[i % PALETTE.length] }}
              />
              <span className="truncate max-w-[140px]">{d.label}</span>
            </span>
          ))}
        </div>
      </div>
      <div className="flex-1 min-h-0 border border-border/40 rounded p-2">
        {mode === "bar" ? (
          <GroupedBar data={data} dims={dims} />
        ) : (
          <Radar data={data} dims={dims} />
        )}
      </div>
    </div>
  )
}
