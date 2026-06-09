import Editor, { loader } from "@monaco-editor/react"
import {
  ArrowDown,
  BookOpen,
  Code2,
  Dna,
  Download,
  ExternalLink,
  Eye,
  FileText,
  Lightbulb,
  Pencil,
  Sparkles,
} from "lucide-react"
import * as monaco from "monaco-editor"
import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts"

import { useTheme } from "@/components/theme-provider"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

import { MarkdownRenderer } from "./MarkdownRenderer"
import type { ArtifactVersion, StepState } from "./mock-data"

loader.config({ monaco })

interface ArtifactsPanelProps {
  step: number
  state: StepState | null
  onVersionChange?: (versionId: string) => void
  onContentChange?: (content: string) => void
}

const STEP_TABS: string[][] = [
  ["backgroundDoc"],
  ["designDoc", "algorithmCode", "evaluationCode", "testDataset"],
  ["evolutionChart", "evolutionLogs"],
  ["paperPdf", "paperMarkdown"],
]

const STEP_META: {
  icon: React.ElementType
  color: string
  gradient: string
}[] = [
  {
    icon: BookOpen,
    color: "text-blue-500",
    gradient: "from-blue-500/15 to-cyan-500/10",
  },
  {
    icon: Code2,
    color: "text-violet-500",
    gradient: "from-violet-500/15 to-purple-500/10",
  },
  {
    icon: Dna,
    color: "text-emerald-500",
    gradient: "from-emerald-500/15 to-teal-500/10",
  },
  {
    icon: FileText,
    color: "text-amber-500",
    gradient: "from-amber-500/15 to-orange-500/10",
  },
]

export default function ArtifactsPanel({
  step,
  state,
  onVersionChange,
  onContentChange,
}: ArtifactsPanelProps) {
  const { t } = useTranslation()
  const [editMode, setEditMode] = useState(false)
  const { resolvedTheme } = useTheme()

  const activeVersion: ArtifactVersion | null = useMemo(() => {
    if (!state || state.versions.length === 0) return null
    return (
      state.versions.find((v) => v.id === state.activeVersionId) ??
      state.versions[state.versions.length - 1]
    )
  }, [state])

  const hasContent = !!activeVersion

  if (!hasContent) {
    return <EmptyState step={step} />
  }

  const tabs = STEP_TABS[step]
  const isEditableTab = [
    "backgroundDoc",
    "designDoc",
    "paperMarkdown",
    "algorithmCode",
    "evaluationCode",
    "testDataset",
  ].includes(tabs[0])

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <Tabs defaultValue={tabs[0]} className="flex-1 flex flex-col min-h-0">
        <div className="shrink-0 flex items-center justify-between px-4 py-2.5 border-b border-border/30 bg-muted/15">
          <TabsList className="h-8 bg-muted/40 border border-border/30">
            {tabs.map((tab) => (
              <TabsTrigger key={tab} value={tab} className="text-xs px-3">
                {t(`research.artifacts.${tab}`)}
              </TabsTrigger>
            ))}
          </TabsList>

          <div className="flex items-center gap-2">
            {isEditableTab && activeVersion.content && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2.5 gap-1.5 text-[11px] text-muted-foreground hover:text-foreground"
                onClick={() => setEditMode(!editMode)}
              >
                {editMode ? (
                  <>
                    <Eye className="size-3" />
                    {t("research.artifacts.preview")}
                  </>
                ) : (
                  <>
                    <Pencil className="size-3" />
                    {t("research.artifacts.edit")}
                  </>
                )}
              </Button>
            )}

            {step > 0 && state && state.versions.length > 1 && (
              <Select
                value={state.activeVersionId ?? undefined}
                onValueChange={(val) => onVersionChange?.(val)}
              >
                <SelectTrigger className="w-32 h-7 text-[11px] border-border/40 bg-muted/30 rounded-md">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {state.versions.map((v) => (
                    <SelectItem key={v.id} value={v.id} className="text-xs">
                      {v.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto bg-background/50">
          {step === 0 && (
            <TabsContent value="backgroundDoc" className="h-full m-0">
              <MonacoMarkdownEditor
                content={activeVersion.content ?? ""}
                editMode={editMode}
                onChange={onContentChange}
                theme={resolvedTheme}
              />
            </TabsContent>
          )}

          {step === 1 && (
            <>
              <TabsContent value="designDoc" className="h-full m-0">
                <MonacoMarkdownEditor
                  content={activeVersion.content ?? ""}
                  editMode={editMode}
                  onChange={onContentChange}
                  theme={resolvedTheme}
                />
              </TabsContent>
              <TabsContent value="algorithmCode" className="h-full m-0">
                <MonacoCodeEditor
                  content={
                    activeVersion.artifacts?.find(
                      (a) => a.name?.includes("algorithm") || a.type === "code",
                    )?.content ?? ""
                  }
                  language="python"
                  fileName="algorithm.py"
                  onChange={onContentChange}
                  theme={resolvedTheme}
                />
              </TabsContent>
              <TabsContent value="evaluationCode" className="h-full m-0">
                <MonacoCodeEditor
                  content={
                    activeVersion.artifacts?.find((a) =>
                      a.name?.includes("evaluation"),
                    )?.content ?? ""
                  }
                  language="python"
                  fileName="evaluation.py"
                  onChange={onContentChange}
                  theme={resolvedTheme}
                />
              </TabsContent>
              <TabsContent value="testDataset" className="h-full m-0">
                <MonacoCodeEditor
                  content={
                    activeVersion.artifacts?.find((a) =>
                      a.name?.includes("dataset"),
                    )?.content ?? ""
                  }
                  language="json"
                  fileName="dataset.json"
                  onChange={onContentChange}
                  theme={resolvedTheme}
                />
              </TabsContent>
            </>
          )}

          {step === 2 && (
            <>
              <TabsContent
                value="evolutionChart"
                className="h-full p-4 m-0 flex flex-col"
              >
                <EvolutionChart
                  content={activeVersion.content}
                  theme={resolvedTheme}
                />
                <div className="shrink-0 pt-4 flex justify-center">
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5 text-xs"
                    onClick={() => window.open("/evolution", "_blank")}
                  >
                    <ExternalLink className="size-3.5" />
                    {t("research.artifacts.viewEvolutionDetail")}
                  </Button>
                </div>
              </TabsContent>
              <TabsContent value="evolutionLogs" className="p-4 m-0">
                {state && state.logs.length > 0 ? (
                  <div className="space-y-1 font-mono text-xs">
                    {state.logs.map((log) => (
                      <div key={log.id} className="flex gap-2 py-0.5">
                        <span className="text-muted-foreground/50 shrink-0">
                          {new Date(log.timestamp).toLocaleTimeString()}
                        </span>
                        <span className="text-foreground/80">
                          {log.message}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <MiniEmpty text={t("research.artifacts.noContent")} />
                )}
              </TabsContent>
            </>
          )}

          {step === 3 && (
            <>
              <TabsContent value="paperPdf" className="p-6 m-0">
                {state?.status === "completed" ? (
                  <div className="rounded-xl border border-border/60 bg-card/80 h-[400px] flex items-center justify-center">
                    <div className="text-center">
                      <div className="size-16 rounded-2xl bg-muted/60 flex items-center justify-center mx-auto mb-4">
                        <FileText className="size-8 text-muted-foreground/30" />
                      </div>
                      <p className="text-sm text-muted-foreground mb-3">
                        {t("research.content.pdfPreview")}
                      </p>
                      <Button variant="outline" size="sm" className="gap-1.5">
                        <Download className="size-3" />
                        {t("research.content.downloadPdf")}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <MiniEmpty text={t("research.artifacts.noContent")} />
                )}
              </TabsContent>
              <TabsContent value="paperMarkdown" className="h-full m-0">
                <MonacoMarkdownEditor
                  content={activeVersion.content ?? ""}
                  editMode={editMode}
                  onChange={onContentChange}
                  theme={resolvedTheme}
                />
              </TabsContent>
            </>
          )}
        </div>
      </Tabs>
    </div>
  )
}

function MonacoMarkdownEditor({
  content,
  editMode,
  onChange,
  theme,
}: {
  content: string
  editMode: boolean
  onChange?: (content: string) => void
  theme?: string
}) {
  if (!editMode) {
    return (
      <div className="p-6 max-w-none">
        {content ? (
          <MarkdownRenderer content={content} />
        ) : (
          <MiniEmpty text="No content" />
        )}
      </div>
    )
  }

  return (
    <div className="h-full min-h-[300px]">
      <Editor
        height="100%"
        language="markdown"
        value={content}
        onChange={(val) => onChange?.(val ?? "")}
        theme={theme !== "light" ? "custom-dark" : "custom-light"}
        beforeMount={(m) => {
          m.editor.defineTheme("custom-dark", {
            base: "vs-dark",
            inherit: true,
            rules: [],
            colors: { "editor.background": "#0D1A2D" },
          })
          m.editor.defineTheme("custom-light", {
            base: "vs",
            inherit: true,
            rules: [],
            colors: { "editor.background": "#ffffff" },
          })
        }}
        options={{
          minimap: { enabled: false },
          fontSize: 13,
          lineNumbers: "on",
          scrollBeyondLastLine: false,
          wordWrap: "on",
          automaticLayout: true,
          tabSize: 2,
        }}
      />
    </div>
  )
}

function MonacoCodeEditor({
  content,
  language,
  fileName,
  onChange,
  theme,
}: {
  content: string
  language: string
  fileName: string
  onChange?: (content: string) => void
  theme?: string
}) {
  if (!content) {
    return <MiniEmpty text="No content" />
  }

  return (
    <div className="h-full flex flex-col">
      <div className="shrink-0 flex items-center gap-2 px-4 py-2.5 bg-muted/40 border-b border-border/40">
        <div className="size-6 rounded-md bg-primary/10 flex items-center justify-center">
          <Code2 className="size-3.5 text-primary" />
        </div>
        <span className="text-xs font-medium">{fileName}</span>
        <span className="text-[10px] text-muted-foreground/50 ml-auto">
          {language}
        </span>
      </div>
      <div className="flex-1 min-h-[300px]">
        <Editor
          height="100%"
          language={language}
          value={content}
          onChange={(val) => onChange?.(val ?? "")}
          theme={theme !== "light" ? "custom-dark" : "custom-light"}
          beforeMount={(m) => {
            m.editor.defineTheme("custom-dark", {
              base: "vs-dark",
              inherit: true,
              rules: [],
              colors: { "editor.background": "#0D1A2D" },
            })
            m.editor.defineTheme("custom-light", {
              base: "vs",
              inherit: true,
              rules: [],
              colors: { "editor.background": "#ffffff" },
            })
          }}
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: "on",
            scrollBeyondLastLine: false,
            wordWrap: "on",
            automaticLayout: true,
            tabSize: 2,
          }}
        />
      </div>
    </div>
  )
}

const MOCK_CHART_DATA = [
  { gen: 1, best: -2100, avg: -2500 },
  { gen: 5, best: -1950, avg: -2300 },
  { gen: 10, best: -1800, avg: -2100 },
  { gen: 15, best: -1700, avg: -1950 },
  { gen: 20, best: -1600, avg: -1850 },
  { gen: 25, best: -1550, avg: -1780 },
  { gen: 30, best: -1523, avg: -1720 },
  { gen: 35, best: -1500, avg: -1680 },
  { gen: 40, best: -1480, avg: -1650 },
  { gen: 45, best: -1460, avg: -1620 },
  { gen: 50, best: -1450, avg: -1600 },
]

function EvolutionChart({
  content,
  theme,
}: {
  content?: string
  theme?: string
}) {
  const { t } = useTranslation()
  const isDark = theme !== "light"

  if (!content) {
    return <MiniEmpty text={t("research.artifacts.noContent")} />
  }

  return (
    <div className="h-full flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <Dna className="size-4 text-emerald-500" />
        <span className="text-sm font-medium text-foreground/80">
          {t("research.artifacts.evolutionChart")}
        </span>
      </div>
      <div className="flex-1 min-h-[250px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={MOCK_CHART_DATA}
            margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke={isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)"}
            />
            <XAxis
              dataKey="gen"
              label={{
                value: "Generation",
                position: "insideBottom",
                offset: -5,
                fontSize: 11,
              }}
              tick={{ fontSize: 10 }}
              stroke={isDark ? "rgba(255,255,255,0.3)" : "rgba(0,0,0,0.3)"}
            />
            <YAxis
              label={{
                value: "Fitness",
                angle: -90,
                position: "insideLeft",
                fontSize: 11,
              }}
              tick={{ fontSize: 10 }}
              stroke={isDark ? "rgba(255,255,255,0.3)" : "rgba(0,0,0,0.3)"}
            />
            <RechartsTooltip
              contentStyle={{
                backgroundColor: isDark ? "#1a2332" : "#fff",
                border: `1px solid ${isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)"}`,
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line
              type="monotone"
              dataKey="best"
              stroke="#10b981"
              strokeWidth={2}
              dot={false}
              name="Best Fitness"
            />
            <Line
              type="monotone"
              dataKey="avg"
              stroke="#6366f1"
              strokeWidth={2}
              dot={false}
              name="Avg Fitness"
              strokeDasharray="4 2"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function EmptyState({ step }: { step: number }) {
  const { t } = useTranslation()
  const meta = STEP_META[step]
  const Icon = meta.icon

  return (
    <div className="h-full flex flex-col items-center justify-center px-10">
      <div
        className={`relative size-20 rounded-2xl bg-gradient-to-br ${meta.gradient} flex items-center justify-center mb-6 border border-border/30 shadow-lg`}
      >
        <Icon className={`size-9 ${meta.color}`} />
        <div className="absolute -top-1.5 -right-1.5 size-6 rounded-full bg-background border border-border/40 flex items-center justify-center shadow-sm">
          <Sparkles className="size-3.5 text-primary/60" />
        </div>
      </div>

      <h3 className="text-base font-semibold text-foreground mb-2">
        {t("research.artifacts.emptyTitle")}
      </h3>
      <p className="text-sm text-muted-foreground/70 text-center leading-relaxed mb-6 max-w-xs">
        {t(`research.guide.step${step + 1}Desc`)}
      </p>

      <div className="flex items-center gap-2 px-5 py-3 rounded-xl bg-primary/8 border border-primary/20 shadow-sm">
        <ArrowDown className="size-4 text-primary motion-safe:animate-bounce" />
        <span className="text-sm font-medium text-primary">
          {t("research.artifacts.emptyAction")}
        </span>
      </div>

      <div className="mt-8 w-full max-w-sm space-y-2">
        {[
          t(`research.guide.step${step + 1}Tip1`),
          t(`research.guide.step${step + 1}Tip2`),
        ].map((tip, i) => (
          <div
            key={i}
            className="flex items-start gap-2.5 text-left px-3 py-2 rounded-lg bg-muted/30 border border-border/20"
          >
            <Lightbulb className="size-3.5 text-amber-500/70 shrink-0 mt-0.5" />
            <span className="text-[11px] text-muted-foreground/70 leading-relaxed">
              {tip}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function MiniEmpty({ text }: { text: string }) {
  return (
    <div className="flex items-center justify-center h-full min-h-[200px]">
      <p className="text-sm text-muted-foreground/50">{text}</p>
    </div>
  )
}
