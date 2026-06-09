import { ChevronLeft, ChevronRight } from "lucide-react"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

import ArtifactsPanel from "./ArtifactsPanel"
import ChatArea from "./ChatArea"
import ConfigDialog from "./ConfigDialog"
import {
  createEmptySession,
  DEFAULT_CONFIG,
  MOCK_EXTRA_SESSIONS,
  MOCK_GROUPS,
  MOCK_SESSIONS,
  type ResearchSession,
  type SessionGroup,
  type SessionSnapshot,
  type StepState,
} from "./mock-data"
import ResearchHeader from "./ResearchHeader"
import SessionSidebar from "./SessionSidebar"
import SnapshotDialog from "./SnapshotDialog"
import StepNav from "./StepNav"

export default function ResearchPage() {
  const { t } = useTranslation()
  const [sessions, setSessions] = useState<ResearchSession[]>([
    ...MOCK_SESSIONS,
    ...MOCK_EXTRA_SESSIONS,
  ])
  const [groups, setGroups] = useState<SessionGroup[]>(MOCK_GROUPS)
  const [activeSessionId, setActiveSessionId] = useState<string | null>(
    MOCK_SESSIONS[0]?.id ?? null,
  )
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [artifactsCollapsed, setArtifactsCollapsed] = useState(false)
  const [configOpen, setConfigOpen] = useState(false)
  const [inputValue, setInputValue] = useState("")
  const [streamingContent] = useState<string | null>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const RIGHT_PANEL_MIN_WIDTH = 320
  const [rightWidth, setRightWidth] = useState(520)
  const [isResizing, setIsResizing] = useState(false)

  const startResize = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)

    const onMove = (ev: MouseEvent) => {
      const container = document.getElementById("research-main-area")
      if (!container) return
      const rect = container.getBoundingClientRect()
      const next = rect.right - ev.clientX
      const max = Math.floor(rect.width * 0.5)
      setRightWidth(Math.max(RIGHT_PANEL_MIN_WIDTH, Math.min(max, next)))
    }

    const onUp = () => {
      setIsResizing(false)
      document.removeEventListener("mousemove", onMove)
      document.removeEventListener("mouseup", onUp)
      document.body.style.userSelect = ""
      document.body.style.cursor = ""
    }

    document.addEventListener("mousemove", onMove)
    document.addEventListener("mouseup", onUp)
    document.body.style.userSelect = "none"
    document.body.style.cursor = "ew-resize"
  }, [])

  useEffect(() => {
    const onResize = () => {
      const container = document.getElementById("research-main-area")
      if (!container) return
      const max = Math.floor(container.getBoundingClientRect().width * 0.5)
      setRightWidth((w) => Math.max(RIGHT_PANEL_MIN_WIDTH, Math.min(max, w)))
    }
    window.addEventListener("resize", onResize)
    return () => window.removeEventListener("resize", onResize)
  }, [])

  const activeSession = useMemo(
    () => sessions.find((s) => s.id === activeSessionId) ?? null,
    [sessions, activeSessionId],
  )

  const [activeStep, setActiveStep] = useState<number>(
    activeSession?.currentStep ?? 0,
  )

  const handleStepChange = useCallback(
    (step: number) => {
      setActiveStep(step)
      if (!activeSession) return
      const stepState = activeSession.steps[step]
      if (
        stepState &&
        stepState.versions.length > 0 &&
        !stepState.activeVersionId
      ) {
        setSessions((prev) =>
          prev.map((s) => {
            if (s.id !== activeSessionId) return s
            const steps = [...s.steps]
            steps[step] = {
              ...steps[step],
              activeVersionId: steps[step].versions[0].id,
            }
            return { ...s, steps }
          }),
        )
      }
    },
    [activeSession, activeSessionId],
  )

  const handleNewSession = useCallback(() => {
    const activeGroup = activeSession?.groupId ?? null
    const id = `session-${Date.now()}`
    const session = createEmptySession(id, "", activeGroup)
    setSessions((prev) => [session, ...prev])
    setActiveSessionId(id)
    setActiveStep(0)
    setSidebarOpen(false)
  }, [activeSession])

  const handleDeleteSession = useCallback(
    (id: string) => {
      setSessions((prev) => {
        const remaining = prev.filter((s) => s.id !== id)
        if (activeSessionId === id) {
          const next = remaining[0] ?? null
          setActiveSessionId(next?.id ?? null)
          setActiveStep(next?.currentStep ?? 0)
        }
        return remaining
      })
    },
    [activeSessionId],
  )

  const handleSelectSession = useCallback(
    (id: string) => {
      setActiveSessionId(id)
      setSidebarOpen(false)
      const session = sessions.find((s) => s.id === id)
      if (session) setActiveStep(session.currentStep)
    },
    [sessions],
  )

  const handleCreateGroup = useCallback((name: string) => {
    const group: SessionGroup = {
      id: `group-${Date.now()}`,
      name,
      createdAt: new Date().toISOString(),
      isCollapsed: false,
    }
    setGroups((prev) => [...prev, group])
  }, [])

  const handleRenameGroup = useCallback((id: string, name: string) => {
    setGroups((prev) => prev.map((g) => (g.id === id ? { ...g, name } : g)))
  }, [])

  const handleDeleteGroup = useCallback((id: string) => {
    setGroups((prev) => prev.filter((g) => g.id !== id))
    setSessions((prev) =>
      prev.map((s) => (s.groupId === id ? { ...s, groupId: null } : s)),
    )
  }, [])

  const handleToggleGroupCollapse = useCallback((id: string) => {
    setGroups((prev) =>
      prev.map((g) =>
        g.id === id ? { ...g, isCollapsed: !g.isCollapsed } : g,
      ),
    )
  }, [])

  const handleMoveSession = useCallback(
    (sessionId: string, groupId: string | null) => {
      setSessions((prev) =>
        prev.map((s) => (s.id === sessionId ? { ...s, groupId } : s)),
      )
    },
    [],
  )

  const handleSendMessage = useCallback(() => {
    if (!inputValue.trim() || !activeSession) return
    const newMsg = {
      id: `msg-${Date.now()}`,
      role: "user" as const,
      content: inputValue.trim(),
      timestamp: new Date().toISOString(),
      step: activeStep,
    }
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id !== activeSessionId) return s
        return { ...s, messages: [...s.messages, newMsg] }
      }),
    )
    setInputValue("")
  }, [inputValue, activeSession, activeSessionId, activeStep])

  const handleVersionChange = useCallback(
    (versionId: string) => {
      setSessions((prev) =>
        prev.map((s) => {
          if (s.id !== activeSessionId) return s
          const steps = [...s.steps]
          steps[activeStep] = {
            ...steps[activeStep],
            activeVersionId: versionId,
          }
          return { ...s, steps }
        }),
      )
    },
    [activeSessionId, activeStep],
  )

  const handleArtifactContentChange = useCallback(
    (content: string) => {
      setSessions((prev) =>
        prev.map((s) => {
          if (s.id !== activeSessionId) return s
          const steps = [...s.steps]
          const step = steps[activeStep]
          const versions = step.versions.map((v) =>
            v.id === step.activeVersionId ? { ...v, content } : v,
          )
          steps[activeStep] = { ...step, versions }
          return { ...s, steps }
        }),
      )
    },
    [activeSessionId, activeStep],
  )

  const [snapshots, setSnapshots] = useState<SessionSnapshot[]>([])
  const [snapshotDialogOpen, setSnapshotDialogOpen] = useState(false)

  const sessionSnapshots = useMemo(
    () =>
      snapshots
        .filter((s) => s.sessionId === activeSessionId)
        .sort((a, b) => b.createdAt.localeCompare(a.createdAt)),
    [snapshots, activeSessionId],
  )

  const handleSaveSnapshot = useCallback(
    (name: string) => {
      if (!activeSession) return
      const snapshot: SessionSnapshot = {
        id: `snap-${Date.now()}`,
        sessionId: activeSession.id,
        name,
        createdAt: new Date().toISOString(),
        currentStep: activeStep,
        steps: structuredClone(activeSession.steps),
        config: { ...activeSession.config },
      }
      setSnapshots((prev) => [...prev, snapshot])
    },
    [activeSession, activeStep],
  )

  const handleRestoreSnapshot = useCallback(
    (snapshotId: string) => {
      const snapshot = snapshots.find((s) => s.id === snapshotId)
      if (!snapshot || !activeSession) return
      setSessions((prev) =>
        prev.map((s) => {
          if (s.id !== activeSession.id) return s
          return {
            ...s,
            currentStep: snapshot.currentStep,
            steps: structuredClone(snapshot.steps),
            config: { ...snapshot.config },
            updatedAt: new Date().toISOString(),
          }
        }),
      )
      setActiveStep(snapshot.currentStep)
    },
    [snapshots, activeSession],
  )

  const handleDeleteSnapshot = useCallback((snapshotId: string) => {
    setSnapshots((prev) => prev.filter((s) => s.id !== snapshotId))
  }, [])

  const currentStepState: StepState | null =
    activeSession?.steps[activeStep] ?? null

  const sessionTitle = activeSession?.title || t("research.title")

  return (
    <TooltipProvider>
      <div className="flex flex-col h-screen w-screen overflow-hidden bg-background">
        <ResearchHeader title={sessionTitle} />

        <div className="flex-1 flex min-h-0 relative">
          {/* Decorative background */}
          <div className="absolute inset-0 pointer-events-none overflow-hidden">
            <div className="absolute top-0 right-1/4 w-96 h-96 bg-primary/3 rounded-full blur-[100px]" />
            <div className="absolute bottom-0 left-1/3 w-80 h-80 bg-blue-500/3 rounded-full blur-[80px]" />
          </div>

          <SessionSidebar
            open={sidebarOpen}
            sessions={sessions}
            groups={groups}
            activeSessionId={activeSessionId}
            onSelect={handleSelectSession}
            onDelete={handleDeleteSession}
            onCreateGroup={handleCreateGroup}
            onRenameGroup={handleRenameGroup}
            onDeleteGroup={handleDeleteGroup}
            onToggleGroupCollapse={handleToggleGroupCollapse}
            onMoveSession={handleMoveSession}
          />

          {/* Main workspace */}
          <div className="flex-1 flex flex-col min-w-0 relative z-10">
            {/* Step navigation bar - horizontal at top */}
            <StepNav
              activeStep={activeStep}
              steps={activeSession?.steps ?? []}
              onStepChange={handleStepChange}
              onNewResearch={handleNewSession}
              onToggleHistory={() => setSidebarOpen(!sidebarOpen)}
            />

            {/* Content area below step nav */}
            <div className="flex-1 flex min-h-0 relative">
              {/* Main content area */}
              <div
                id="research-main-area"
                className="flex-1 flex min-h-0 min-w-0 relative"
              >
                {/* Chat area (center) */}
                <ChatArea
                  step={activeStep}
                  messages={activeSession?.messages ?? []}
                  logs={activeSession?.steps.flatMap((s) => s.logs) ?? []}
                  inputValue={inputValue}
                  onInputChange={setInputValue}
                  onSend={handleSendMessage}
                  inputRef={inputRef}
                  stepState={currentStepState}
                  onNext={() => handleStepChange(Math.min(activeStep + 1, 3))}
                  streamingContent={streamingContent}
                  onOpenConfig={() => setConfigOpen(true)}
                  onOpenArchive={() => setSnapshotDialogOpen(true)}
                  onRestoreLog={(logId) => {
                    console.log("Restore to log:", logId)
                  }}
                  onViewLog={(logId) => {
                    console.log("View log:", logId)
                  }}
                />

                {/* Right panel toggle - vertically centered at panel edge */}
                {artifactsCollapsed ? (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        onClick={() => setArtifactsCollapsed(false)}
                        className="absolute right-0 top-1/2 -translate-y-1/2 z-20 flex items-center justify-center w-4 h-10 rounded-l-md bg-muted/60 border border-r-0 border-border/30 hover:bg-primary/10 hover:text-primary text-muted-foreground/60 transition-colors"
                      >
                        <ChevronLeft className="size-3.5" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="left">
                      {t("research.artifacts.expand")}
                    </TooltipContent>
                  </Tooltip>
                ) : (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        onClick={() => setArtifactsCollapsed(true)}
                        className="absolute top-1/2 -translate-y-1/2 z-40 flex items-center justify-center w-4 h-10 rounded-l-md bg-muted/60 border border-r-0 border-border/30 hover:bg-primary/10 hover:text-primary text-muted-foreground/60 transition-colors"
                        style={{ right: `${rightWidth}px` }}
                      >
                        <ChevronRight className="size-3.5" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="left">
                      {t("research.artifacts.title")}
                    </TooltipContent>
                  </Tooltip>
                )}

                {/* Artifacts panel (right) */}
                {!artifactsCollapsed && (
                  <aside
                    className={`relative shrink-0 flex flex-col overflow-hidden border-l border-border/30 bg-card/30 ${
                      isResizing
                        ? ""
                        : "transition-[width] duration-300 ease-in-out"
                    }`}
                    style={{ width: `${rightWidth}px` }}
                  >
                    <div
                      onMouseDown={startResize}
                      className="absolute left-0 top-0 bottom-0 w-1 z-30 cursor-ew-resize hover:bg-primary/40 active:bg-primary/60"
                    />
                    <div className="shrink-0 flex items-center px-4 h-11 border-b border-border/30 bg-muted/20">
                      <span className="text-xs font-semibold text-foreground/80 tracking-wide">
                        {t("research.artifacts.title")}
                      </span>
                    </div>
                    <div className="flex-1 min-h-0">
                      <ArtifactsPanel
                        step={activeStep}
                        state={currentStepState}
                        onVersionChange={handleVersionChange}
                        onContentChange={handleArtifactContentChange}
                      />
                    </div>
                  </aside>
                )}
              </div>
            </div>
          </div>
        </div>

        <ConfigDialog
          open={configOpen}
          onOpenChange={setConfigOpen}
          config={activeSession?.config ?? DEFAULT_CONFIG}
          onSave={() => setConfigOpen(false)}
        />

        <SnapshotDialog
          open={snapshotDialogOpen}
          onOpenChange={setSnapshotDialogOpen}
          snapshots={sessionSnapshots}
          onSave={handleSaveSnapshot}
          onRestore={handleRestoreSnapshot}
          onDelete={handleDeleteSnapshot}
        />
      </div>
    </TooltipProvider>
  )
}
