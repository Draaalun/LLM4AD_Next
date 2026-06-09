export type PanelContentType = "visualization" | "logs" | "trend"

export const PANEL_CONTENT_TYPES: PanelContentType[] = [
  "visualization",
  "logs",
  "trend",
]

export type LayoutType =
  | "1"
  | "2h"
  | "2v"
  | "3h"
  | "3v"
  | "3tb"
  | "3lr"
  | "4grid"

export const LAYOUT_TYPES: LayoutType[] = [
  "1",
  "2h",
  "2v",
  "3h",
  "3v",
  "3tb",
  "3lr",
  "4grid",
]

export const LAYOUT_I18N_KEYS: Record<LayoutType, string> = {
  "1": "evolution.layout.panels1",
  "2h": "evolution.layout.panels2h",
  "2v": "evolution.layout.panels2v",
  "3h": "evolution.layout.panels3h",
  "3v": "evolution.layout.panels3v",
  "3tb": "evolution.layout.panels3tb",
  "3lr": "evolution.layout.panels3lr",
  "4grid": "evolution.layout.panels4grid",
}

export const LAYOUT_PANEL_COUNT: Record<LayoutType, number> = {
  "1": 1,
  "2h": 2,
  "2v": 2,
  "3h": 3,
  "3v": 3,
  "3tb": 3,
  "3lr": 3,
  "4grid": 4,
}

export const DEFAULT_LAYOUT: LayoutType = "2h"
export const DEFAULT_PANEL_CONTENTS: Record<LayoutType, PanelContentType[]> = {
  "1": ["visualization"],
  "2h": ["visualization", "logs"],
  "2v": ["visualization", "logs"],
  "3h": ["visualization", "logs", "trend"],
  "3v": ["visualization", "logs", "trend"],
  "3tb": ["visualization", "logs", "trend"],
  "3lr": ["visualization", "logs", "trend"],
  "4grid": ["visualization", "logs", "trend", "visualization"],
}

const STORAGE_KEY = "evolution-panel-layout"

interface PersistedState {
  layout: LayoutType
  panelContents: PanelContentType[]
}

export function loadPanelLayout(): PersistedState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as PersistedState
      if (parsed.layout && parsed.panelContents) {
        return parsed
      }
    }
  } catch {
    /* ignore */
  }
  return {
    layout: DEFAULT_LAYOUT,
    panelContents: DEFAULT_PANEL_CONTENTS[DEFAULT_LAYOUT],
  }
}

export function savePanelLayout(state: PersistedState): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    /* ignore */
  }
}
