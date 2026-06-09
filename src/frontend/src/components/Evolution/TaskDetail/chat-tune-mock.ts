/**
 * Mock conversation flow for the chat-based parameter tuning prototype.
 *
 * The flow is intentionally compact: it walks the user through the same seven
 * configuration stages as the stepwise wizard, but does so via short
 * structured turns instead of long forms.
 */

export type ChatStageKey =
  | "scenario"
  | "data"
  | "evolveAnnotation"
  | "evaluator"
  | "evolution"
  | "coder"
  | "advanced"
  | "confirm"

export interface ChoiceOption {
  value: string
  label: string
  description?: string
  ask_for_path?: boolean
  ask_for_dir?: boolean
  is_custom?: boolean
  file_path?: string
  dir_path?: string
}

interface BaseCard {
  cardId: string
  stage: ChatStageKey
  prompt: string
  hint?: string
}

export interface ChoiceCard extends BaseCard {
  kind: "choice"
  options: ChoiceOption[]
}

export interface MultiChoiceCard extends BaseCard {
  kind: "multichoice"
  options: ChoiceOption[]
  defaultSelected?: string[]
}

export interface NumberFormCard extends BaseCard {
  kind: "number"
  min?: number
  max?: number
  step?: number
  defaultValue: number
  unit?: string
}

export interface TextFormCard extends BaseCard {
  kind: "text"
  placeholder?: string
  defaultValue?: string
}

export interface SummaryCard extends BaseCard {
  kind: "summary"
}

export interface RunCard extends BaseCard {
  kind: "run"
}

export type AssistantCard =
  | ChoiceCard
  | MultiChoiceCard
  | NumberFormCard
  | TextFormCard
  | SummaryCard
  | RunCard

export type CardSubmission =
  | { kind: "choice"; value: string; label: string; filePath?: string }
  | { kind: "multichoice"; values: string[]; labels: string[] }
  | { kind: "number"; value: number }
  | { kind: "text"; value: string }
  | { kind: "summary"; ack: true }
  | { kind: "run"; ack: true }

export interface ChatMessage {
  id: string
  role: "user" | "assistant" | "system"
  text?: string
  card?: AssistantCard
  /** Set when the card has been submitted by the user (locked + readonly) */
  submission?: CardSubmission
  /** A purely informational text block accompanying or replacing a card */
  variant?: "info" | "success" | "warning"
  createdAt: number
}

/**
 * Configuration value collected from each stage. Stored alongside the chat
 * timeline so the right-hand panel can render a live preview.
 */
export interface CollectedConfig {
  scenario?: { value: string; label: string }
  data?: { value: string; label: string }
  evolveAnnotation?: { value: string; label: string }
  evaluator?: { timeoutSeconds: number }
  evolution?: { algorithm?: string; populationSize?: number }
  coder?: { strategy: string }
  advanced?: { enabledExtras: string[] }
}

/* ─────────────────────── Initial assistant turn ───────────────────────── */

let cardSeq = 0
const nextCardId = () => `card-${Date.now().toString(36)}-${++cardSeq}`

export const initialAssistantCards: AssistantCard[] = [
  {
    cardId: "card-scenario",
    stage: "scenario",
    kind: "choice",
    prompt:
      "你好，我会引导你完成任务参数配置。先告诉我你的算法演化场景，我会据此推荐合适的默认参数。",
    options: [
      { value: "tsp", label: "TSP / 路径规划", description: "经典旅行商问题" },
      {
        value: "cvrp",
        label: "CVRP / 车辆路径",
        description: "带容量约束的车辆路径问题",
      },
      {
        value: "scheduling",
        label: "调度优化",
        description: "生产、流水线等调度类问题",
      },
      {
        value: "custom",
        label: "自定义场景",
        description: "其它由我提供完整数据集",
      },
    ],
  },
]

/* ───────────────────────── Mock responder logic ────────────────────────── */

interface NextStep {
  text?: string
  cards?: AssistantCard[]
  variant?: "info" | "success" | "warning"
}

/**
 * Decide what the assistant should reply with after the user has submitted a
 * card. Returns one or more follow-up messages. Returning `null` means the
 * conversation flow has ended (everything has been gathered).
 */
export function mockNextTurn(
  currentStage: ChatStageKey,
  submission: CardSubmission,
  collected: CollectedConfig,
): NextStep | null {
  switch (currentStage) {
    case "scenario": {
      if (submission.kind !== "choice") return null
      const scenarioLabel = submission.label
      return {
        text: `好的，已记录场景为「${scenarioLabel}」。下面我们确认一下数据源：`,
        cards: [
          {
            cardId: nextCardId(),
            stage: "data",
            kind: "choice",
            prompt: "你的项目数据是否已就绪？",
            hint: "若尚未上传，可以稍后切换到「分步配置」补充上传步骤。",
            options: [
              { value: "ready", label: "已上传，使用我项目里的数据" },
              { value: "sample", label: "使用示例数据集快速体验" },
              { value: "later", label: "暂不上传，先保存配置" },
            ],
          },
        ],
      }
    }
    case "data": {
      if (submission.kind !== "choice") return null
      return {
        text: "数据来源确认完毕。接下来我需要标注源代码中要演化的代码块（EVOLVE_START / EVOLVE_END）：",
        cards: [
          {
            cardId: nextCardId(),
            stage: "evolveAnnotation",
            kind: "choice",
            prompt: "你想用哪种方式标注 EVOLVE 块？",
            options: [
              {
                value: "ai",
                label: "由 AI 推荐",
                description: "自动扫描源码并给出建议",
              },
              {
                value: "manual",
                label: "手动标注",
                description: "我会自己标注",
              },
              {
                value: "existing",
                label: "已经标注过",
                description: "使用源码中现有的标注",
              },
            ],
          },
        ],
      }
    }
    case "evolveAnnotation": {
      if (submission.kind !== "choice") return null
      return {
        text: "好的，标注方式记录完成。接下来配置评估器。",
        cards: [
          {
            cardId: nextCardId(),
            stage: "evaluator",
            kind: "number",
            prompt: "单次评估的超时时间（秒）？",
            hint: "复杂问题建议设置 60-120 秒，简单问题 10-30 秒即可。",
            min: 5,
            max: 600,
            step: 5,
            defaultValue: collected.scenario?.value === "scheduling" ? 90 : 30,
            unit: "秒",
          },
        ],
      }
    }
    case "evaluator": {
      if (submission.kind !== "number") return null
      return {
        text: `评估超时设置为 ${submission.value} 秒。下面挑选一种进化算法：`,
        cards: [
          {
            cardId: nextCardId(),
            stage: "evolution",
            kind: "choice",
            prompt: "选择进化算法策略",
            options: [
              {
                value: "funsearch",
                label: "FunSearch",
                description: "适合数学/组合搜索类问题，简单稳定",
              },
              {
                value: "eoh",
                label: "EoH",
                description: "Evolution of Heuristics，适合启发式生成",
              },
              {
                value: "meoh",
                label: "MEoH",
                description: "多目标版本，需要 Pareto 前沿",
              },
              {
                value: "regevo",
                label: "RegEvo",
                description: "正则化进化，适合稳健调优",
              },
            ],
          },
        ],
      }
    }
    case "evolution": {
      if (submission.kind === "choice") {
        return {
          text: `已选择「${submission.label}」算法。接下来设置种群规模：`,
          cards: [
            {
              cardId: nextCardId(),
              stage: "evolution",
              kind: "number",
              prompt: "初始种群大小？",
              hint: "通常 8-32 之间，越大探索越充分但耗时增加。",
              min: 4,
              max: 128,
              step: 2,
              defaultValue: 16,
              unit: "个个体",
            },
          ],
        }
      }
      if (submission.kind === "number") {
        return {
          text: `种群规模设置为 ${submission.value}。接下来配置代码生成策略：`,
          cards: [
            {
              cardId: nextCardId(),
              stage: "coder",
              kind: "choice",
              prompt: "选择代码生成策略",
              options: [
                {
                  value: "standard",
                  label: "标准模板",
                  description: "通用 Prompt + 完整代码替换",
                },
                {
                  value: "diff",
                  label: "Diff 模式",
                  description: "基于差异的增量编辑，节省 token",
                },
                {
                  value: "custom",
                  label: "自定义 Prompt",
                  description: "你自己提供 Prompt 模板",
                },
              ],
            },
          ],
        }
      }
      return null
    }
    case "coder": {
      if (submission.kind !== "choice") return null
      return {
        text: "代码生成策略已选定。最后看一下高级配置：",
        cards: [
          {
            cardId: nextCardId(),
            stage: "advanced",
            kind: "multichoice",
            prompt: "需要启用哪些高级能力？（可多选，留空则全部使用默认值）",
            hint: "未勾选的项会使用框架推荐默认值。",
            options: [
              {
                value: "memory",
                label: "启用记忆模块",
                description: "跨代复用历史经验",
              },
              {
                value: "multimodal",
                label: "多模态输入",
                description: "支持图像/草图输入",
              },
              {
                value: "version",
                label: "细粒度版本控制",
                description: "保存每代代码快照",
              },
              {
                value: "logging",
                label: "详细日志",
                description: "结构化 JSON 日志便于检索",
              },
            ],
            defaultSelected: ["logging"],
          },
        ],
      }
    }
    case "advanced": {
      if (submission.kind !== "multichoice") return null
      return {
        text: "全部参数已就绪，下面是配置摘要：",
        cards: [
          {
            cardId: nextCardId(),
            stage: "confirm",
            kind: "summary",
            prompt: "请确认配置内容",
          },
        ],
        variant: "success",
      }
    }
    case "confirm": {
      if (submission.kind !== "summary") return null
      return {
        text: "确认无误，可以提交运行：",
        cards: [
          {
            cardId: nextCardId(),
            stage: "confirm",
            kind: "run",
            prompt: "提交运行",
            hint: "提交后将创建子任务并消耗计算资源。",
          },
        ],
      }
    }
    default:
      return null
  }
}

/* ───────────────────────── Helpers for collected config ──────────────── */

export function applySubmissionToConfig(
  collected: CollectedConfig,
  card: AssistantCard,
  submission: CardSubmission,
): CollectedConfig {
  const next: CollectedConfig = { ...collected }
  switch (card.stage) {
    case "scenario":
      if (submission.kind === "choice")
        next.scenario = { value: submission.value, label: submission.label }
      break
    case "data":
      if (submission.kind === "choice")
        next.data = { value: submission.value, label: submission.label }
      break
    case "evolveAnnotation":
      if (submission.kind === "choice")
        next.evolveAnnotation = {
          value: submission.value,
          label: submission.label,
        }
      break
    case "evaluator":
      if (submission.kind === "number")
        next.evaluator = { timeoutSeconds: submission.value }
      break
    case "evolution":
      if (submission.kind === "choice")
        next.evolution = {
          ...(next.evolution ?? {}),
          algorithm: submission.label,
        }
      else if (submission.kind === "number")
        next.evolution = {
          ...(next.evolution ?? {}),
          populationSize: submission.value,
        }
      break
    case "coder":
      if (submission.kind === "choice")
        next.coder = { strategy: submission.label }
      break
    case "advanced":
      if (submission.kind === "multichoice")
        next.advanced = { enabledExtras: submission.labels }
      break
    default:
      break
  }
  return next
}

export const STAGE_ORDER: ChatStageKey[] = [
  "scenario",
  "data",
  "evolveAnnotation",
  "evaluator",
  "evolution",
  "coder",
  "advanced",
  "confirm",
]

export const STAGE_TITLES: Record<ChatStageKey, string> = {
  scenario: "场景",
  data: "数据准备",
  evolveAnnotation: "演化块标注",
  evaluator: "评估器",
  evolution: "进化算法",
  coder: "代码生成",
  advanced: "高级配置",
  confirm: "确认提交",
}
