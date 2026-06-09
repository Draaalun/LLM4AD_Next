import { useTranslation } from "react-i18next"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import FieldLabel from "./FieldLabel"
import type { JsonSchema } from "./resolveSchema"
import {
  compareSchemaEntries,
  getDefaultValue,
  isUiHidden,
  resolveSchema,
} from "./resolveSchema"
import SchemaField from "./SchemaField"
import { useSchemaUi } from "./useSchemaUi"

interface SchemaDiscriminatedFieldProps {
  schema: JsonSchema
  root: JsonSchema
  value: Record<string, unknown> | undefined
  onChange: (value: Record<string, unknown>) => void
  label?: string
}

export default function SchemaDiscriminatedField({
  schema,
  root,
  value,
  onChange,
  label,
}: SchemaDiscriminatedFieldProps) {
  const {
    label: uiLabel,
    description: uiDescription,
    discriminatorInfo,
  } = useSchemaUi()
  const { t } = useTranslation()
  const info = discriminatorInfo(schema, root)
  if (!info) return null

  const currentType = value?.[info.propertyName] as string | undefined
  const selectedOption =
    info.options.find((o) => o.value === currentType) ?? info.options[0]

  const handleTypeChange = (newType: string) => {
    const option = info.options.find((o) => o.value === newType)
    if (!option) return
    const defaults = getDefaultValue(option.schema, root) as
      | Record<string, unknown>
      | undefined
    onChange({ ...defaults, [info.propertyName]: newType })
  }

  const filteredProperties = { ...selectedOption.schema.properties }
  delete filteredProperties[info.propertyName]

  const requiredSet = new Set(
    selectedOption.schema.required?.filter((r) => r !== info.propertyName) ??
      [],
  )

  const sortedEntries = Object.entries(filteredProperties)
    .filter(([, propSchema]) => {
      const { schema: resolved } = resolveSchema(propSchema, root)
      return !isUiHidden(resolved)
    })
    .sort(([keyA, a], [keyB, b]) => {
      const { schema: ra } = resolveSchema(a, root)
      const { schema: rb } = resolveSchema(b, root)
      return compareSchemaEntries(
        { schema: ra, parentRequired: requiredSet.has(keyA) },
        { schema: rb, parentRequired: requiredSet.has(keyB) },
      )
    })

  const filteredSchema: JsonSchema = {
    ...selectedOption.schema,
    properties: filteredProperties,
    required: selectedOption.schema.required?.filter(
      (r) => r !== info.propertyName,
    ),
  }

  const fieldLabel =
    label ??
    uiLabel(schema, t("evolution.schemaForm.discriminatorFallbackLabel"))
  const fieldDescription = uiDescription(schema)

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <FieldLabel label={fieldLabel} description={fieldDescription} />
        <Select
          value={currentType ?? selectedOption.value}
          onValueChange={handleTypeChange}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {info.options.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {sortedEntries.length > 0 && (
        <div className="ml-2 border-l-2 border-border pl-4 space-y-4">
          {sortedEntries.map(([key, propSchema]) => (
            <SchemaField
              key={key}
              name={key}
              schema={propSchema}
              root={root}
              value={(value as Record<string, unknown>)?.[key]}
              onChange={(v) => onChange({ ...value, [key]: v })}
              required={filteredSchema.required?.includes(key)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
