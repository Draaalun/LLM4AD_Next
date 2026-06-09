import { Plus, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import FieldLabel from "./FieldLabel"
import type { JsonSchema } from "./resolveSchema"
import { getDefaultValue, resolveSchema } from "./resolveSchema"
import SchemaField from "./SchemaField"
import { useSchemaUi } from "./useSchemaUi"

interface SchemaArrayFieldProps {
  schema: JsonSchema
  root: JsonSchema
  value: unknown[] | undefined
  onChange: (value: unknown[]) => void
  label?: string
}

export default function SchemaArrayField({
  schema,
  root,
  value,
  onChange,
  label,
}: SchemaArrayFieldProps) {
  const { t } = useTranslation()
  const { label: uiLabel, description: uiDescription } = useSchemaUi()
  const items = value ?? []
  const itemSchema = schema.items
    ? resolveSchema(schema.items, root).schema
    : { type: "string" as const }

  const addItem = () => {
    const defaultVal =
      getDefaultValue(itemSchema, root) ??
      (itemSchema.type === "object" ? {} : "")
    onChange([...items, defaultVal])
  }

  const removeItem = (index: number) => {
    onChange(items.filter((_, i) => i !== index))
  }

  const updateItem = (index: number, val: unknown) => {
    const newItems = [...items]
    newItems[index] = val
    onChange(newItems)
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <FieldLabel
          label={
            label ??
            uiLabel(schema, t("evolution.schemaForm.arrayFallbackLabel"))
          }
          description={uiDescription(schema)}
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={addItem}
          className="h-7 gap-1 text-xs"
        >
          <Plus className="size-3" />
          {t("evolution.schemaForm.arrayAdd")}
        </Button>
      </div>
      {items.length === 0 && (
        <p className="text-xs text-muted-foreground py-2">
          {t("evolution.schemaForm.arrayEmpty")}
        </p>
      )}
      {items.map((item, index) => (
        <div
          key={index}
          className="relative rounded-lg border bg-card p-4 space-y-3"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-muted-foreground">
              #{index + 1}
            </span>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => removeItem(index)}
              className="h-6 w-6 p-0 text-destructive hover:text-destructive"
            >
              <Trash2 className="size-3" />
            </Button>
          </div>
          <SchemaField
            name={`item-${index}`}
            schema={schema.items ?? { type: "string" }}
            root={root}
            value={item}
            onChange={(v) => updateItem(index, v)}
          />
        </div>
      ))}
    </div>
  )
}
