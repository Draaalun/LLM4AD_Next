import { useCallback } from "react"
import { useTranslation } from "react-i18next"

import type { JsonSchema, UiLocale } from "./resolveSchema"
import {
  getDiscriminatorInfo as _getDiscriminatorInfo,
  getUiDescription as _getUiDescription,
  getUiLabel as _getUiLabel,
  validateSchema as _validateSchema,
} from "./resolveSchema"

export function useSchemaUi() {
  const { i18n } = useTranslation()
  const locale = (i18n.language as UiLocale) ?? "zh"

  const label = useCallback(
    (schema: JsonSchema, fallback?: string) =>
      _getUiLabel(schema, fallback, locale),
    [locale],
  )

  const description = useCallback(
    (schema: JsonSchema) => _getUiDescription(schema, locale),
    [locale],
  )

  const discriminatorInfo = useCallback(
    (schema: JsonSchema, root: JsonSchema) =>
      _getDiscriminatorInfo(schema, root, locale),
    [locale],
  )

  const validate = useCallback(
    (schema: JsonSchema, root: JsonSchema, value: unknown) =>
      _validateSchema(schema, root, value, locale),
    [locale],
  )

  return { locale, label, description, discriminatorInfo, validate }
}
