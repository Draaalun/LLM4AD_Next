import { DiffEditor, loader, type Monaco } from "@monaco-editor/react"
import * as monaco from "monaco-editor"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useTheme } from "@/components/theme-provider"
import { Checkbox } from "@/components/ui/checkbox"

import { getLanguageFromPath } from "./types"

loader.config({ monaco })

interface AnnotationDiffViewProps {
  filePath: string
  originalContent: string
  modifiedContent: string
  showFull?: boolean
  onShowFullChange?: (value: boolean) => void
  contentKey?: string
}

export default function AnnotationDiffView({
  filePath,
  originalContent,
  modifiedContent,
  showFull: controlledShowFull,
  onShowFullChange,
  contentKey,
}: AnnotationDiffViewProps) {
  const { t } = useTranslation()
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme !== "light"
  const language = getLanguageFromPath(filePath)
  const [localShowFull, setLocalShowFull] = useState(false)

  const showFull = controlledShowFull ?? localShowFull
  const setShowFull = onShowFullChange ?? setLocalShowFull

  return (
    <div
      className={`flex flex-col h-full ${isDark ? "bg-[#0D1A2D]" : "bg-background"}`}
    >
      <div
        className={`shrink-0 flex items-center justify-between px-3 py-1.5 border-b ${isDark ? "bg-[#0D1A2D] border-[#1a2d45]" : "bg-muted/30 border-border"}`}
      >
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span>{t("evolution.evolveAnnotation.diffOriginal")}</span>
          <span>→</span>
          <span>{t("evolution.evolveAnnotation.diffModified")}</span>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 cursor-pointer select-none">
            <Checkbox
              checked={showFull}
              onCheckedChange={(v) => setShowFull(!!v)}
              className="size-3.5"
            />
            <span className="text-[11px] text-muted-foreground">
              {t("evolution.evolveAnnotation.showFullContent")}
            </span>
          </label>
          <span className="text-xs font-mono text-muted-foreground">
            {filePath}
          </span>
        </div>
      </div>
      <div className="flex-1 min-h-0">
        <DiffEditor
          key={`${contentKey ?? filePath}-${showFull ? "full" : "diff"}`}
          original={originalContent}
          modified={modifiedContent}
          language={language}
          theme={isDark ? "custom-dark" : "custom-light"}
          beforeMount={(m: Monaco) => {
            m.editor.defineTheme("custom-dark", {
              base: "vs-dark",
              inherit: true,
              rules: [],
              colors: {
                "editor.background": "#0D1A2D",
              },
            })
            m.editor.defineTheme("custom-light", {
              base: "vs",
              inherit: true,
              rules: [],
              colors: {
                "editor.background": "#ffffff",
              },
            })
          }}
          options={{
            readOnly: true,
            renderSideBySide: true,
            minimap: { enabled: false },
            fontSize: 12,
            lineNumbers: "on",
            scrollBeyondLastLine: false,
            automaticLayout: true,
            renderOverviewRuler: false,
            hideUnchangedRegions: {
              enabled: !showFull,
            },
          }}
        />
      </div>
    </div>
  )
}
