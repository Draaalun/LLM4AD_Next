import { ChevronDown, ChevronRight } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { JsonSchema } from "../schema-form/resolveSchema"
import {
  compareSchemaEntries,
  isPrimitive,
  isUiHidden,
  resolveSchema,
} from "../schema-form/resolveSchema"
import SchemaField from "../schema-form/SchemaField"
import SchemaObjectField from "../schema-form/SchemaObjectField"
import { useSchemaUi } from "../schema-form/useSchemaUi"

interface AdvancedStepProps {
  schema: JsonSchema
  root: JsonSchema
  value: Record<string, unknown>
  onChange: (value: Record<string, unknown>) => void
  onBack?: () => void
  onNext?: () => void
}

export default function AdvancedStep({
  schema,
  root,
  value,
  onChange,
  onBack,
  onNext,
}: AdvancedStepProps) {
  const { t } = useTranslation()
  const { schema: resolved } = resolveSchema(schema, root)
  const properties = resolved.properties ?? {}

  const requiredKeys = new Set(resolved.required ?? [])

  // Split into primitive (basic) and complex (collapsible) fields
  const basicEntries: [string, JsonSchema][] = []
  const complexEntries: [string, JsonSchema][] = []
  for (const [key, propSchema] of Object.entries(properties)) {
    const { schema: propResolved } = resolveSchema(propSchema, root)
    if (isUiHidden(propResolved)) continue
    if (isPrimitive(propResolved) || propResolved.enum) {
      basicEntries.push([key, propSchema])
    } else {
      complexEntries.push([key, propSchema])
    }
  }

  const sortEntries = (a: [string, JsonSchema], b: [string, JsonSchema]) => {
    const { schema: ra } = resolveSchema(a[1], root)
    const { schema: rb } = resolveSchema(b[1], root)
    return compareSchemaEntries(
      { schema: ra, parentRequired: requiredKeys.has(a[0]) },
      { schema: rb, parentRequired: requiredKeys.has(b[0]) },
    )
  }
  basicEntries.sort(sortEntries)
  complexEntries.sort(sortEntries)

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 min-h-0 overflow-y-auto space-y-6 pr-1">
        {/* Basic (primitive) params */}
        {basicEntries.length > 0 && (
          <div className="space-y-4">
            {basicEntries.map(([key, propSchema]) => (
              <SchemaField
                key={key}
                name={key}
                schema={propSchema}
                root={root}
                value={value[key]}
                onChange={(v) => onChange({ ...value, [key]: v })}
              />
            ))}
          </div>
        )}

        {/* Complex (nested) params in collapsible panels */}
        {complexEntries.length > 0 && (
          <div className="space-y-3">
            {complexEntries.map(([key, propSchema]) => (
              <CollapsibleGroup
                key={key}
                name={key}
                schema={propSchema}
                root={root}
                value={value[key]}
                onChange={(v) => onChange({ ...value, [key]: v })}
              />
            ))}
          </div>
        )}
      </div>

      <div className="shrink-0 py-2">
        <div className="flex justify-center gap-6">
          {onBack && (
            <Button type="button" variant="outline" onClick={onBack}>
              {t("common.previousStep")}
            </Button>
          )}
          {onNext && (
            <Button type="button" onClick={onNext}>
              {t("common.nextStep")}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

function CollapsibleGroup({
  name,
  schema,
  root,
  value,
  onChange,
}: {
  name: string
  schema: JsonSchema
  root: JsonSchema
  value: unknown
  onChange: (v: unknown) => void
}) {
  const [isOpen, setIsOpen] = useState(false)
  const { label: uiLabel, description: uiDescription } = useSchemaUi()
  const { schema: resolved } = resolveSchema(schema, root)
  const title = uiLabel(resolved, name)
  const desc = uiDescription(resolved)
  // Objects with properties are rendered directly by SchemaObjectField — using
  // SchemaField here would add a second collapsible header for the same object.
  const isObjectWithProperties =
    resolved.type === "object" && !!resolved.properties

  return (
    <div className="rounded-lg border bg-card">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex w-full items-center gap-2 p-3 text-left hover:bg-accent/30 transition-colors rounded-lg",
          isOpen && "rounded-b-none border-b",
        )}
      >
        {isOpen ? (
          <ChevronDown className="size-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="size-4 text-muted-foreground" />
        )}
        <span className="text-sm font-medium">{title}</span>
        {desc && (
          <span className="text-xs text-muted-foreground ml-2 truncate">
            {desc}
          </span>
        )}
      </button>
      {isOpen && (
        <div className="p-4">
          {isObjectWithProperties ? (
            <SchemaObjectField
              schema={resolved}
              root={root}
              value={value as Record<string, unknown> | undefined}
              onChange={onChange as (v: Record<string, unknown>) => void}
            />
          ) : (
            <SchemaField
              name={name}
              schema={schema}
              root={root}
              value={value}
              onChange={onChange}
            />
          )}
        </div>
      )}
    </div>
  )
}
