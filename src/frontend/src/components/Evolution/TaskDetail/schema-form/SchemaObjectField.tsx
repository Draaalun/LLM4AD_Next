import type { JsonSchema } from "./resolveSchema"
import {
  compareSchemaEntries,
  isUiHidden,
  resolveSchema,
} from "./resolveSchema"
import SchemaField from "./SchemaField"

interface SchemaObjectFieldProps {
  schema: JsonSchema
  root: JsonSchema
  value: Record<string, unknown> | undefined
  onChange: (value: Record<string, unknown>) => void
}

export default function SchemaObjectField({
  schema,
  root,
  value,
  onChange,
}: SchemaObjectFieldProps) {
  const properties = schema.properties ?? {}
  const required = schema.required ?? []
  const current = value ?? {}

  const sortedEntries = Object.entries(properties)
    .filter(([, propSchema]) => {
      const { schema: resolved } = resolveSchema(propSchema, root)
      return !isUiHidden(resolved)
    })
    .sort(([keyA, a], [keyB, b]) => {
      const { schema: ra } = resolveSchema(a, root)
      const { schema: rb } = resolveSchema(b, root)
      return compareSchemaEntries(
        { schema: ra, parentRequired: required.includes(keyA) },
        { schema: rb, parentRequired: required.includes(keyB) },
      )
    })

  return (
    <div className="space-y-4">
      {sortedEntries.map(([key, propSchema]) => (
        <SchemaField
          key={key}
          name={key}
          schema={propSchema}
          root={root}
          value={current[key]}
          onChange={(v) => onChange({ ...current, [key]: v })}
          required={required.includes(key)}
        />
      ))}
    </div>
  )
}
