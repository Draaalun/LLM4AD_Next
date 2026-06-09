import { X } from "lucide-react"
import { type KeyboardEvent, useCallback, useRef, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { INPUT_LIMITS } from "@/lib/inputLimits"
import { cn } from "@/lib/utils"

interface ModelTagsInputProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
}

function parseModels(raw: string): string[] {
  return raw
    .split(";")
    .map((s) => s.trim())
    .filter(Boolean)
}

function serializeModels(models: string[]): string {
  return models.join(";")
}

export function ModelTagsInput({
  value,
  onChange,
  placeholder = "gpt-4",
  disabled,
}: ModelTagsInputProps) {
  const [inputValue, setInputValue] = useState("")
  const [isFocused, setIsFocused] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const models = parseModels(value ?? "")

  const addModel = useCallback(
    (raw: string) => {
      const names = parseModels(raw)
      if (names.length === 0) return
      const existing = new Set(models)
      const toAdd = names.filter((n) => !existing.has(n))
      if (toAdd.length === 0) {
        setInputValue("")
        return
      }
      onChange(serializeModels([...models, ...toAdd]))
      setInputValue("")
    },
    [models, onChange],
  )

  const removeModel = useCallback(
    (index: number) => {
      const next = models.filter((_, i) => i !== index)
      onChange(serializeModels(next))
    },
    [models, onChange],
  )

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ";") {
      e.preventDefault()
      addModel(inputValue)
    } else if (
      e.key === "Backspace" &&
      inputValue === "" &&
      models.length > 0
    ) {
      removeModel(models.length - 1)
    }
  }

  const handleBlur = () => {
    if (inputValue.trim()) {
      addModel(inputValue)
    }
    setIsFocused(false)
  }

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    const text = e.clipboardData.getData("text")
    if (text.includes(";")) {
      e.preventDefault()
      addModel(text)
    }
  }

  return (
    <div
      className={cn(
        "border-input bg-transparent flex min-h-9 w-full flex-wrap items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm shadow-xs transition-[color,box-shadow]",
        isFocused && "border-ring ring-ring/50 ring-[3px]",
        disabled && "cursor-not-allowed opacity-50",
      )}
      onClick={() => inputRef.current?.focus()}
    >
      {models.map((model, index) => (
        <Badge
          key={`${model}-${index}`}
          variant="secondary"
          className="gap-1 pr-1 shrink-0"
        >
          {model}
          {!disabled && (
            <button
              type="button"
              className="text-muted-foreground hover:text-foreground rounded-full p-0.5 transition-colors"
              onClick={(e) => {
                e.stopPropagation()
                removeModel(index)
              }}
            >
              <X className="size-3" />
            </button>
          )}
        </Badge>
      ))}
      <input
        ref={inputRef}
        type="text"
        autoComplete="one-time-code"
        className="placeholder:text-muted-foreground min-w-[120px] flex-1 bg-transparent outline-none disabled:cursor-not-allowed"
        value={inputValue}
        maxLength={INPUT_LIMITS.name}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        onFocus={() => setIsFocused(true)}
        onPaste={handlePaste}
        placeholder={models.length === 0 ? placeholder : ""}
        disabled={disabled}
      />
    </div>
  )
}
