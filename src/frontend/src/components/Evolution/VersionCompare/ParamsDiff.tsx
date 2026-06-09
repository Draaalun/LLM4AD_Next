import { DiffEditor, loader } from "@monaco-editor/react"
import { useQueries } from "@tanstack/react-query"
import yaml from "js-yaml"
import * as monaco from "monaco-editor"
import { useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import type { TaskTreeItem } from "@/client"
import { Llm4AdTasksService } from "@/client"
import { useTheme } from "@/components/theme-provider"
import { taskKeys } from "@/lib/task-queries"

loader.config({ monaco })

const APP_THEME_LIGHT = "llm4ad-light"
const APP_THEME_DARK = "llm4ad-dark"

function defineAppMonacoThemes() {
  monaco.editor.defineTheme(APP_THEME_LIGHT, {
    base: "vs",
    inherit: true,
    rules: [],
    colors: {
      "editor.background": "#fafbfe",
      "editor.foreground": "#0f172a",
      "editorGutter.background": "#fafbfe",
      "diffEditor.insertedTextBackground": "#10b98122",
      "diffEditor.removedTextBackground": "#ef444422",
    },
  })
  monaco.editor.defineTheme(APP_THEME_DARK, {
    base: "vs-dark",
    inherit: true,
    rules: [],
    colors: {
      "editor.background": "#060b1a",
      "editor.foreground": "#e0e8ff",
      "editorGutter.background": "#060b1a",
      "diffEditor.insertedTextBackground": "#10b98133",
      "diffEditor.removedTextBackground": "#ef444433",
    },
  })
}

function dumpYaml(obj: Record<string, unknown> | undefined | null): string {
  if (!obj) return "# (empty)\n"
  return yaml.dump(obj, { indent: 2, lineWidth: -1, noRefs: true })
}

interface ParamsDiffProps {
  selectedItems: TaskTreeItem[]
  versionMap: Map<string, number>
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

export default function ParamsDiff({
  selectedItems,
  versionMap,
}: ParamsDiffProps) {
  const { t } = useTranslation()
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme !== "light"

  const queries = useQueries({
    queries: selectedItems.map((item) => ({
      queryKey: taskKeys.stats(item.id),
      queryFn: () => Llm4AdTasksService.getTaskStats({ taskId: item.id }),
      staleTime: 30_000,
    })),
  })

  const sortedByCreate = useMemo(
    () =>
      [...selectedItems].sort(
        (a, b) =>
          new Date(a.created_time).getTime() -
          new Date(b.created_time).getTime(),
      ),
    [selectedItems],
  )

  const [baselineId, setBaselineId] = useState<string | null>(null)
  const [compareId, setCompareId] = useState<string | null>(null)

  useEffect(() => {
    if (sortedByCreate.length < 2) return
    const ids = sortedByCreate.map((i) => i.id)
    const nextBaseline =
      baselineId && ids.includes(baselineId) ? baselineId : ids[0]
    const nextCompare =
      compareId && ids.includes(compareId) && compareId !== nextBaseline
        ? compareId
        : (ids.find((id) => id !== nextBaseline) ?? ids[ids.length - 1])
    if (nextBaseline !== baselineId) setBaselineId(nextBaseline)
    if (nextCompare !== compareId) setCompareId(nextCompare)
  }, [sortedByCreate, baselineId, compareId])

  const idIndex = useMemo(
    () => new Map(selectedItems.map((it, i) => [it.id, i])),
    [selectedItems],
  )
  const baselineIdx = baselineId ? idIndex.get(baselineId) : undefined
  const compareIdx = compareId ? idIndex.get(compareId) : undefined

  const baselineQuery =
    baselineIdx !== undefined ? queries[baselineIdx] : undefined
  const compareQuery =
    compareIdx !== undefined ? queries[compareIdx] : undefined

  const isLoading = baselineQuery?.isLoading || compareQuery?.isLoading || false

  const baselineYaml = useMemo(
    () =>
      dumpYaml(
        baselineQuery?.data?.input_args as Record<string, unknown> | undefined,
      ),
    [baselineQuery?.data],
  )
  const compareYaml = useMemo(
    () =>
      dumpYaml(
        compareQuery?.data?.input_args as Record<string, unknown> | undefined,
      ),
    [compareQuery?.data],
  )

  if (selectedItems.length < 2) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-1.5 text-sm text-muted-foreground">
        <span>{t("evolution.versionCompare.selectAtLeast2")}</span>
        <span className="text-xs italic">
          {t("evolution.versionCompare.selectHint")}
        </span>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2 h-full">
      <div className="flex flex-wrap items-center gap-3 text-xs">
        <div className="flex items-center gap-1.5">
          <span className="text-muted-foreground">
            {t("evolution.versionCompare.baseline")}
          </span>
          <select
            value={baselineId ?? ""}
            onChange={(e) => setBaselineId(e.target.value)}
            className="px-2 py-1 rounded border border-border/60 bg-background text-foreground"
          >
            {selectedItems.map((it) => (
              <option key={it.id} value={it.id}>
                {labelFor(it, versionMap.get(it.id))}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-muted-foreground">
            {t("evolution.versionCompare.compare")}
          </span>
          <select
            value={compareId ?? ""}
            onChange={(e) => setCompareId(e.target.value)}
            className="px-2 py-1 rounded border border-border/60 bg-background text-foreground"
          >
            {selectedItems.map((it) => (
              <option key={it.id} value={it.id}>
                {labelFor(it, versionMap.get(it.id))}
              </option>
            ))}
          </select>
        </div>
        {isLoading && (
          <span className="text-muted-foreground">
            {t("evolution.versionCompare.loading")}
          </span>
        )}
      </div>
      <div className="flex-1 min-h-0 border border-border/40 rounded overflow-hidden bg-background">
        <DiffEditor
          original={baselineYaml}
          modified={compareYaml}
          language="yaml"
          theme={isDark ? APP_THEME_DARK : APP_THEME_LIGHT}
          beforeMount={defineAppMonacoThemes}
          options={{
            readOnly: true,
            renderSideBySide: true,
            originalEditable: false,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            fontSize: 12,
          }}
        />
      </div>
    </div>
  )
}
