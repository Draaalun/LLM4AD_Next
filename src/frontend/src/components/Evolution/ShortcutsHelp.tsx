import { Keyboard } from "lucide-react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface ShortcutItem {
  keys: string[]
  labelKey: string
  fallback: string
}

const SHORTCUTS: ShortcutItem[] = [
  {
    keys: ["["],
    labelKey: "evolution.shortcuts.toggleLeft",
    fallback: "切换左侧任务列表",
  },
  {
    keys: ["]"],
    labelKey: "evolution.shortcuts.toggleRight",
    fallback: "切换右侧信息面板",
  },
  {
    keys: ["←"],
    labelKey: "evolution.shortcuts.prevGen",
    fallback: "上一代",
  },
  {
    keys: ["→"],
    labelKey: "evolution.shortcuts.nextGen",
    fallback: "下一代",
  },
  {
    keys: ["Space"],
    labelKey: "evolution.shortcuts.togglePlay",
    fallback: "播放 / 暂停",
  },
  {
    keys: ["Esc"],
    labelKey: "evolution.shortcuts.exitFullscreen",
    fallback: "退出全屏",
  },
  {
    keys: ["?"],
    labelKey: "evolution.shortcuts.showHelp",
    fallback: "显示快捷键帮助",
  },
]

export default function ShortcutsHelp() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const isTypingTarget = (el: EventTarget | null) => {
      if (!(el instanceof HTMLElement)) return false
      const tag = el.tagName
      return (
        tag === "INPUT" ||
        tag === "TEXTAREA" ||
        tag === "SELECT" ||
        el.isContentEditable
      )
    }

    const onKey = (e: KeyboardEvent) => {
      if (e.defaultPrevented || isTypingTarget(e.target)) return
      if (e.ctrlKey || e.metaKey || e.altKey) return
      if (e.key === "?") {
        e.preventDefault()
        setOpen((v) => !v)
      }
    }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [])

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <TooltipProvider delayDuration={200}>
        <Tooltip>
          <TooltipTrigger asChild>
            <PopoverTrigger asChild>
              <button
                type="button"
                aria-label={t("evolution.shortcuts.title", {
                  defaultValue: "键盘快捷键",
                })}
                className="inline-flex items-center justify-center size-7 rounded-md
                  text-muted-foreground hover:text-primary
                  hover:bg-accent/60 border border-transparent hover:border-border/40
                  transition-colors focus:outline-none"
              >
                <Keyboard className="size-4" />
              </button>
            </PopoverTrigger>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            {t("evolution.shortcuts.tooltip", {
              defaultValue: "键盘快捷键 (?)",
            })}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
      <PopoverContent align="end" sideOffset={8} className="w-72 p-3">
        <div className="flex items-center gap-2 mb-2 pb-2 border-b border-border/40">
          <Keyboard className="size-3.5 text-primary" />
          <span className="text-xs font-semibold text-primary tracking-wider uppercase">
            {t("evolution.shortcuts.title", {
              defaultValue: "键盘快捷键",
            })}
          </span>
        </div>
        <ul className="space-y-1.5">
          {SHORTCUTS.map((s) => (
            <li
              key={s.labelKey}
              className="flex items-center justify-between gap-3 text-xs"
            >
              <span className="text-muted-foreground truncate">
                {t(s.labelKey, { defaultValue: s.fallback })}
              </span>
              <span className="flex items-center gap-1 shrink-0">
                {s.keys.map((k) => (
                  <kbd
                    key={k}
                    className="inline-flex items-center justify-center min-w-[22px] h-5 px-1.5 rounded
                      text-[10px] font-mono font-medium
                      text-foreground bg-muted border border-border/60
                      shadow-[0_1px_0] shadow-border/40"
                  >
                    {k}
                  </kbd>
                ))}
              </span>
            </li>
          ))}
        </ul>
        <p className="mt-2 pt-2 border-t border-border/40 text-[10px] text-muted-foreground/70">
          {t("evolution.shortcuts.hint", {
            defaultValue: "聚焦输入框时快捷键自动禁用",
          })}
        </p>
      </PopoverContent>
    </Popover>
  )
}
