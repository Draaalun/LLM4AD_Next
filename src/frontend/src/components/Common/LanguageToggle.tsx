import { useCallback } from "react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"

const STORAGE_KEY = "llm4ad-language"

export default function LanguageToggle() {
  const { i18n } = useTranslation()
  const lang = i18n.language

  const toggle = useCallback(() => {
    const next = lang === "zh" ? "en" : "zh"
    localStorage.setItem(STORAGE_KEY, next)
    window.location.reload()
  }, [lang])

  return (
    <Button
      variant="ghost"
      size="sm"
      className="h-8 px-2 text-xs font-medium text-muted-foreground hover:text-primary"
      onClick={toggle}
    >
      {lang === "zh" ? "EN" : "中"}
    </Button>
  )
}
