import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import type { Components } from "react-markdown"
import Markdown from "react-markdown"
import remarkGfm from "remark-gfm"
import type { PrivacyPolicyContent } from "@/client"
import { PrivacyPolicyService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface PrivacyPolicyDialogProps {
  open: boolean
  onAccept: () => void
  onDecline?: () => void
  showDeclineButton?: boolean
  allowClose?: boolean // 是否允许通过叉叉或点击外部关闭
}

export function PrivacyPolicyDialog({
  open,
  onAccept,
  onDecline,
  showDeclineButton = true,
  allowClose = true,
}: PrivacyPolicyDialogProps) {
  const { t, i18n } = useTranslation()
  const [content, setContent] = useState<PrivacyPolicyContent | null>(null)
  const [loading, setLoading] = useState(false)

  const components: Components = {
    a: ({ href, children, ...props }) => (
      <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
        {children}
      </a>
    ),
  }

  useEffect(() => {
    if (open) {
      setLoading(true)
      // 重新加载前先清空旧内容，避免上一次的缓存导致加载中按钮可点击
      setContent(null)
      // 获取当前语言，i18n.language 可能是 'zh-CN' 或 'en-US'，取前两位
      const lang = i18n.language.split("-")[0]
      PrivacyPolicyService.getPrivacyPolicyContent({ lang })
        .then((data) => {
          setContent(data)
        })
        .catch((error) => {
          console.error("Failed to load privacy policy:", error)
        })
        .finally(() => {
          setLoading(false)
        })
    }
  }, [open, i18n.language])

  const handleOpenChange = (newOpen: boolean) => {
    // 只有在允许关闭且有 onDecline 回调时才允许关闭
    if (!newOpen && allowClose && onDecline) {
      onDecline()
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="w-[900px] max-w-[calc(100vw-2rem)] sm:max-w-[900px] max-h-[85vh] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle>{t("privacyPolicy.title")}</DialogTitle>
          <DialogDescription>
            {content?.version && `Version: ${content.version}`}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 min-h-[300px] w-full rounded-md border p-4 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <p className="text-muted-foreground">
                {t("privacyPolicy.loading")}
              </p>
            </div>
          ) : content ? (
            <div
              className="prose prose-sm dark:prose-invert max-w-none
              prose-headings:text-foreground prose-headings:font-semibold
              prose-h1:text-xl prose-h1:border-b prose-h1:border-border/50 prose-h1:pb-2
              prose-h2:text-lg prose-h2:mt-6
              prose-h3:text-base
              prose-p:text-foreground/80 prose-p:leading-relaxed
              prose-strong:text-foreground
              prose-a:text-primary prose-a:no-underline prose-a:hover:underline
              prose-code:text-primary prose-code:bg-muted prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-code:before:content-none prose-code:after:content-none
              prose-pre:bg-muted prose-pre:border prose-pre:border-border/50 prose-pre:rounded-lg
              prose-ul:text-foreground/80
              prose-ol:text-foreground/80
              prose-li:text-foreground/80
              prose-blockquote:border-primary/30 prose-blockquote:text-foreground/70
              prose-hr:border-border/50"
            >
              <Markdown remarkPlugins={[remarkGfm]} components={components}>
                {content.content}
              </Markdown>
              {content.updated_at && (
                <p className="text-sm text-muted-foreground mt-4">
                  {t("common.updatedTime")}:{" "}
                  {new Date(content.updated_at).toLocaleDateString()}
                </p>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <p className="text-muted-foreground">
                {t("privacyPolicy.loadError")}
              </p>
            </div>
          )}
        </div>

        <DialogFooter className="flex-shrink-0">
          {showDeclineButton && onDecline && (
            <Button
              variant="outline"
              onClick={onDecline}
              disabled={loading || !content}
            >
              {t("privacyPolicy.disagree")}
            </Button>
          )}
          <Button onClick={onAccept} disabled={loading || !content}>
            {t("privacyPolicy.agree")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
