import { Plus, Trash2 } from "lucide-react"
import {
  type ArrayPath,
  type Control,
  type FieldValues,
  useFieldArray,
} from "react-hook-form"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"

interface ArrayFieldManagerProps<T extends FieldValues> {
  control: Control<T>
  name: ArrayPath<T>
  defaultItem: Record<string, unknown>
  label: string
  addLabel?: string
  renderItem: (index: number) => React.ReactNode
}

export default function ArrayFieldManager<T extends FieldValues>({
  control,
  name,
  defaultItem,
  label,
  addLabel,
  renderItem,
}: ArrayFieldManagerProps<T>) {
  const { fields, append, remove } = useFieldArray({ control, name })
  const { t } = useTranslation()

  return (
    <div className="space-y-3">
      {fields.map((field, index) => (
        <div key={field.id} className="relative rounded-lg border bg-card p-4">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-muted-foreground">
              {label} #{index + 1}
            </span>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              onClick={() => remove(index)}
            >
              <Trash2 className="size-4" />
            </Button>
          </div>
          {renderItem(index)}
        </div>
      ))}
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => append(defaultItem as never)}
      >
        <Plus className="mr-1 size-4" />
        {addLabel || `${t("common.create")} ${label}`}
      </Button>
    </div>
  )
}
