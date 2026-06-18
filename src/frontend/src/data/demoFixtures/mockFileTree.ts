import type { FileTreeNode } from "@/client"

/**
 * Mock file tree shown in the demo's AI Build preview panel.
 *
 * Two-level structure: an `algorithm` folder with the evaluator/task code and
 * a `config` folder with config files. Mirrors the artifact layout the AI
 * build pipeline actually produces, so the demo's `FileTreeView` looks
 * indistinguishable from a real run.
 *
 * Wired through `<FileTreeView tree={DEMO_FILE_TREE} />` in DemoBuildShell —
 * the real `FileTreeView` component is reused as-is, no internal changes.
 */
export const DEMO_FILE_TREE: FileTreeNode[] = [
  {
    name: "algorithm",
    path: "algorithm",
    type: "directory",
    children: [
      {
        name: "evaluator.py",
        path: "algorithm/evaluator.py",
        type: "file",
      },
      {
        name: "task.py",
        path: "algorithm/task.py",
        type: "file",
      },
    ],
  },
  {
    name: "config",
    path: "config",
    type: "directory",
    children: [
      {
        name: "config.yaml",
        path: "config/config.yaml",
        type: "file",
      },
      {
        name: "params.json",
        path: "config/params.json",
        type: "file",
      },
    ],
  },
]
