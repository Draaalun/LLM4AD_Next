import { useCallback, useState } from "react"
import { Group, Panel, Separator } from "react-resizable-panels"
import type { TaskResponse } from "@/client"
import { cn } from "@/lib/utils"
import EvolutionProgressBar from "../EvolutionProgressBar"
import LayoutSelector from "./LayoutSelector"
import PanelContentView from "./PanelContentView"
import {
  DEFAULT_PANEL_CONTENTS,
  LAYOUT_PANEL_COUNT,
  type LayoutType,
  loadPanelLayout,
  type PanelContentType,
  savePanelLayout,
} from "./panel-layout-types"

interface MultiPanelLayoutProps {
  task: TaskResponse
}

function ResizeHandle({
  orientation,
}: {
  orientation: "horizontal" | "vertical"
}) {
  const isHorizontal = orientation === "horizontal"
  return (
    <Separator
      className={cn(
        "group relative flex items-center justify-center bg-background transition-colors data-[separator]:hover:bg-primary/10 data-[separator=active]:bg-primary/15",
        isHorizontal ? "w-1.5" : "h-1.5",
      )}
    >
      <div
        className={cn(
          "bg-border transition-all duration-150 group-hover:bg-primary/60 group-data-[separator=active]:bg-primary",
          isHorizontal
            ? "w-px h-1/2 group-hover:h-full group-data-[separator=active]:h-full"
            : "h-px w-1/2 group-hover:w-full group-data-[separator=active]:w-full",
        )}
      />
    </Separator>
  )
}

export default function MultiPanelLayout({ task }: MultiPanelLayoutProps) {
  const initial = loadPanelLayout()
  const [layout, setLayout] = useState<LayoutType>(initial.layout)
  const [panelContents, setPanelContents] = useState<PanelContentType[]>(
    initial.panelContents,
  )

  const handleLayoutChange = useCallback((newLayout: LayoutType) => {
    setLayout(newLayout)
    const newCount = LAYOUT_PANEL_COUNT[newLayout]
    setPanelContents((prev) => {
      const defaults = DEFAULT_PANEL_CONTENTS[newLayout]
      const next =
        newCount <= prev.length
          ? prev.slice(0, newCount)
          : [...prev, ...defaults.slice(prev.length, newCount)]
      savePanelLayout({ layout: newLayout, panelContents: next })
      return next
    })
  }, [])

  const updatePanelContent = useCallback(
    (index: number, type: PanelContentType) => {
      setPanelContents((prev) => {
        const next = [...prev]
        next[index] = type
        savePanelLayout({ layout, panelContents: next })
        return next
      })
    },
    [layout],
  )

  const renderPanel = (index: number) => (
    <PanelContentView
      task={task}
      contentType={panelContents[index] ?? "visualization"}
      onContentChange={(type) => updatePanelContent(index, type)}
    />
  )

  const renderLayout = () => {
    switch (layout) {
      case "1":
        return <div className="h-full w-full">{renderPanel(0)}</div>

      case "2h":
        return (
          <Group key="2h" orientation="horizontal">
            <Panel defaultSize="50%" minSize="15%">
              {renderPanel(0)}
            </Panel>
            <ResizeHandle orientation="horizontal" />
            <Panel defaultSize="50%" minSize="15%">
              {renderPanel(1)}
            </Panel>
          </Group>
        )

      case "2v":
        return (
          <Group key="2v" orientation="vertical">
            <Panel defaultSize="50%" minSize="15%">
              {renderPanel(0)}
            </Panel>
            <ResizeHandle orientation="vertical" />
            <Panel defaultSize="50%" minSize="15%">
              {renderPanel(1)}
            </Panel>
          </Group>
        )

      case "3h":
        return (
          <Group key="3h" orientation="horizontal">
            <Panel defaultSize="33%" minSize="15%">
              {renderPanel(0)}
            </Panel>
            <ResizeHandle orientation="horizontal" />
            <Panel defaultSize="34%" minSize="15%">
              {renderPanel(1)}
            </Panel>
            <ResizeHandle orientation="horizontal" />
            <Panel defaultSize="33%" minSize="15%">
              {renderPanel(2)}
            </Panel>
          </Group>
        )

      case "3v":
        return (
          <Group key="3v" orientation="vertical">
            <Panel defaultSize="33%" minSize="15%">
              {renderPanel(0)}
            </Panel>
            <ResizeHandle orientation="vertical" />
            <Panel defaultSize="34%" minSize="15%">
              {renderPanel(1)}
            </Panel>
            <ResizeHandle orientation="vertical" />
            <Panel defaultSize="33%" minSize="15%">
              {renderPanel(2)}
            </Panel>
          </Group>
        )

      case "3tb":
        return (
          <Group key="3tb" orientation="vertical">
            <Panel defaultSize="50%" minSize="20%">
              {renderPanel(0)}
            </Panel>
            <ResizeHandle orientation="vertical" />
            <Panel defaultSize="50%" minSize="20%">
              <Group orientation="horizontal">
                <Panel defaultSize="50%" minSize="20%">
                  {renderPanel(1)}
                </Panel>
                <ResizeHandle orientation="horizontal" />
                <Panel defaultSize="50%" minSize="20%">
                  {renderPanel(2)}
                </Panel>
              </Group>
            </Panel>
          </Group>
        )

      case "3lr":
        return (
          <Group key="3lr" orientation="horizontal">
            <Panel defaultSize="50%" minSize="20%">
              {renderPanel(0)}
            </Panel>
            <ResizeHandle orientation="horizontal" />
            <Panel defaultSize="50%" minSize="20%">
              <Group orientation="vertical">
                <Panel defaultSize="50%" minSize="20%">
                  {renderPanel(1)}
                </Panel>
                <ResizeHandle orientation="vertical" />
                <Panel defaultSize="50%" minSize="20%">
                  {renderPanel(2)}
                </Panel>
              </Group>
            </Panel>
          </Group>
        )

      case "4grid":
        return (
          <Group key="4grid" orientation="vertical">
            <Panel defaultSize="50%" minSize="20%">
              <Group orientation="horizontal">
                <Panel defaultSize="50%" minSize="20%">
                  {renderPanel(0)}
                </Panel>
                <ResizeHandle orientation="horizontal" />
                <Panel defaultSize="50%" minSize="20%">
                  {renderPanel(1)}
                </Panel>
              </Group>
            </Panel>
            <ResizeHandle orientation="vertical" />
            <Panel defaultSize="50%" minSize="20%">
              <Group orientation="horizontal">
                <Panel defaultSize="50%" minSize="20%">
                  {renderPanel(2)}
                </Panel>
                <ResizeHandle orientation="horizontal" />
                <Panel defaultSize="50%" minSize="20%">
                  {renderPanel(3)}
                </Panel>
              </Group>
            </Panel>
          </Group>
        )
    }
  }

  return (
    <div className="h-full w-full flex flex-col">
      {/* Toolbar bar */}
      <div className="shrink-0 flex items-center justify-end px-2 py-1 bg-background border-b border-border/20">
        <LayoutSelector layout={layout} onLayoutChange={handleLayoutChange} />
      </div>

      {/* Panel layout area */}
      <div className="flex-1 min-h-0">{renderLayout()}</div>

      {/* Progress bar — rendered inside overview to avoid footer flicker on tab switch */}
      <div className="shrink-0 border-t border-border/40 bg-background/95">
        <EvolutionProgressBar task={task} />
      </div>
    </div>
  )
}
