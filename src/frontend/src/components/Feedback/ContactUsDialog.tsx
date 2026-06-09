import { useQuery } from "@tanstack/react-query"
import { Copy, Loader2, Mail, MessageCircle, X } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { LiveQrService } from "@/client/sdk.gen"
import type { LiveCodeContactInfo } from "@/client/types.gen"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard"
import useCustomToast from "@/hooks/useCustomToast"
import { cn } from "@/lib/utils"

interface ContactUsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

/** Prepend the API base to a relative path returned by the backend. */
function apiUrl(path: string): string {
  const base = import.meta.env.VITE_API_URL || ""
  return `${base}${path}`
}

/** A single WeChat group QR card with its own image-error fallback. */
function ContactQrCard({ contact }: { contact: LiveCodeContactInfo }) {
  const { t } = useTranslation()
  const [qrError, setQrError] = useState(false)

  // The card is in the contact list (so it IS configured); an empty image_url
  // or a load error means the underlying code is temporarily unavailable.
  if (!contact.image_url || qrError) {
    return (
      <div
        className={cn(
          "flex aspect-square w-full items-center justify-center rounded-lg",
          "border border-dashed border-border bg-muted/40",
          "px-4 text-center text-xs text-muted-foreground",
        )}
      >
        {t("contactUs.wechatUnavailable")}
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center gap-1.5 w-full">
      <div className="aspect-square w-full rounded-lg border border-border bg-white p-1.5">
        <img
          src={apiUrl(contact.image_url)}
          alt={contact.landing_title ?? "WeChat Group QR Code"}
          className="w-full h-full object-contain"
          onError={() => setQrError(true)}
        />
      </div>
      <span className="text-xs text-muted-foreground text-center max-w-full">
        {contact.landing_title || t("contactUs.scanToJoin")}
      </span>
    </div>
  )
}

export function ContactUsDialog({ open, onOpenChange }: ContactUsDialogProps) {
  const { t } = useTranslation()
  const [copiedField, setCopiedField] = useState<string | null>(null)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [, copy] = useCopyToClipboard()

  // The WeChat group QRs are served by the admin-maintained live-code system.
  // Only fetch while the dialog is open; an empty list means none configured.
  const { data: contacts, isLoading: contactLoading } = useQuery({
    queryKey: ["live-qr-contact"],
    queryFn: () => LiveQrService.contact(),
    enabled: open,
    staleTime: 5 * 60 * 1000,
  })

  const contactList = contacts ?? []

  const handleCopy = async (text: string, field: string) => {
    const ok = await copy(text)
    if (ok) {
      setCopiedField(field)
      setTimeout(() => setCopiedField(null), 2000)
      showSuccessToast(t("contactUs.copySuccess"))
    } else {
      showErrorToast(t("contactUs.copyFailed"))
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="sm:max-w-2xl p-0 gap-0 max-h-[80vh] flex flex-col"
        showCloseButton={false}
      >
        <div className="shrink-0 flex items-center justify-between px-6 pt-5 pb-4 border-b border-border">
          <DialogTitle className="text-lg font-semibold">
            {t("contactUs.title")}
          </DialogTitle>
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="rounded-sm opacity-70 transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
          >
            <X className="size-4" />
            <span className="sr-only">Close</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          <p className="text-sm text-muted-foreground">
            {t("contactUs.description")}
          </p>

          {/* Email */}
          <div className="flex items-start gap-3 p-3 rounded-lg border border-border/60 bg-muted/30">
            <Mail className="size-5 text-primary mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium">{t("contactUs.email")}</div>
              <div className="mt-2 space-y-2">
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-foreground">CityU</span>
                  <span className="text-muted-foreground">
                    llm4ad@cityu.edu.hk
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 px-1.5 shrink-0"
                    onClick={() =>
                      handleCopy("llm4ad@cityu.edu.hk", "email-cityu")
                    }
                  >
                    <Copy className="size-3" />
                    <span className="ml-1 text-xs">
                      {copiedField === "email-cityu"
                        ? t("contactUs.copied")
                        : t("contactUs.copy")}
                    </span>
                  </Button>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-foreground">Huawei</span>
                  <span className="text-muted-foreground">
                    llm4ad@huawei.com
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 px-1.5 shrink-0"
                    onClick={() =>
                      handleCopy("llm4ad@huawei.com", "email-huawei")
                    }
                  >
                    <Copy className="size-3" />
                    <span className="ml-1 text-xs">
                      {copiedField === "email-huawei"
                        ? t("contactUs.copied")
                        : t("contactUs.copy")}
                    </span>
                  </Button>
                </div>
              </div>
            </div>
          </div>

          {/* WeChat Groups (powered by the live-code system) */}
          <div className="flex items-start gap-3 p-3 rounded-lg border border-border/60 bg-muted/30">
            <MessageCircle className="size-5 text-primary mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium">
                {t("contactUs.wechatGroup")}
              </div>
              <div className="text-sm text-muted-foreground mt-0.5 mb-3">
                {t("contactUs.wechatGroupDesc")}
              </div>

              {contactLoading ? (
                <div className="flex h-32 w-32 items-center justify-center rounded-lg border border-border bg-muted">
                  <Loader2 className="size-5 animate-spin text-muted-foreground" />
                </div>
              ) : contactList.length > 0 ? (
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
                  {contactList.map((c) => (
                    <ContactQrCard key={c.slug} contact={c} />
                  ))}
                </div>
              ) : (
                <div
                  className={cn(
                    "flex h-32 w-full items-center justify-center rounded-lg",
                    "border border-dashed border-border bg-muted/40",
                    "px-4 text-center text-xs text-muted-foreground",
                  )}
                >
                  {t("contactUs.wechatNotConfigured")}
                </div>
              )}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
