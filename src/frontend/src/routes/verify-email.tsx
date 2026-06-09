import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
  useNavigate,
} from "@tanstack/react-router"
import { useCallback, useEffect, useRef, useState } from "react"
import { useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod"

import { UsersService } from "@/client"
import { AuthLayout } from "@/components/Common/AuthLayout"
import { Button } from "@/components/ui/button"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import { isLoggedIn } from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import i18n from "@/i18n"
import { handleError } from "@/utils"

export const Route = createFileRoute("/verify-email")({
  component: VerifyEmail,
  validateSearch: (search: Record<string, unknown>) => ({
    email: (search.email as string) || "",
    verify_code: (search.verify_code as string) || "",
  }),
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({
        to: "/projects",
      })
    }
  },
  head: () => ({
    meta: [
      {
        title: i18n.t("verifyEmail.pageTitle"),
      },
    ],
  }),
})

function VerifyEmail() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { email, verify_code } = Route.useSearch()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const STORAGE_KEY = "verify_email_resend_expiry"

  const [autoFilledCode, setAutoFilledCode] = useState(verify_code || "")

  const getInitialCountdown = () => {
    const expiry = localStorage.getItem(STORAGE_KEY)
    if (!expiry) return 0
    const remaining = Math.ceil((Number(expiry) - Date.now()) / 1000)
    return remaining > 0 ? remaining : 0
  }

  const [countdown, setCountdown] = useState(getInitialCountdown)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const formSchema = z.object({
    code: z
      .string()
      .min(6, { message: t("verifyEmail.codePlaceholder") })
      .max(6, { message: t("verifyEmail.codePlaceholder") }),
  })

  type FormData = z.infer<typeof formSchema>

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    defaultValues: {
      code: autoFilledCode,
    },
  })

  const startCountdown = useCallback(() => {
    const expiryTime = Date.now() + 60 * 1000
    localStorage.setItem(STORAGE_KEY, String(expiryTime))
    setCountdown(60)
    if (timerRef.current) clearInterval(timerRef.current)
    timerRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timerRef.current!)
          timerRef.current = null
          localStorage.removeItem(STORAGE_KEY)
          return 0
        }
        return prev - 1
      })
    }, 1000)
  }, [])

  useEffect(() => {
    if (countdown > 0 && !timerRef.current) {
      timerRef.current = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(timerRef.current!)
            timerRef.current = null
            localStorage.removeItem(STORAGE_KEY)
            return 0
          }
          return prev - 1
        })
      }, 1000)
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
    }
  }, [countdown])

  const verifyMutation = useMutation({
    mutationFn: (data: FormData) =>
      UsersService.verifyEmail({
        requestBody: { email, code: data.code },
      }),
    onSuccess: () => {
      showSuccessToast(t("verifyEmail.verifySuccess"))
      navigate({ to: "/login" })
    },
    onError: handleError.bind(showErrorToast),
  })

  const resendMutation = useMutation({
    mutationFn: () =>
      UsersService.resendVerifyCode({
        requestBody: { email },
      }),
    onSuccess: (data) => {
      showSuccessToast(t("verifyEmail.resendSuccess"))
      startCountdown()
      if (data.verify_code) {
        setAutoFilledCode(data.verify_code)
        form.setValue("code", data.verify_code)
      }
    },
    onError: handleError.bind(showErrorToast),
  })

  const onSubmit = (data: FormData) => {
    if (verifyMutation.isPending) return
    verifyMutation.mutate(data)
  }

  return (
    <AuthLayout>
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="flex flex-col gap-6"
        >
          <div className="flex flex-col items-center gap-2 text-center">
            <h1
              className="text-2xl font-bold tracking-wide"
              style={{
                background: "linear-gradient(90deg, #60efff, #00d4ff, #0088ff)",
                backgroundClip: "text",
                WebkitBackgroundClip: "text",
                color: "transparent",
              }}
            >
              {t("verifyEmail.title")}
            </h1>
            <p className="text-sm text-[#6b8ab0]">
              {t("verifyEmail.subtitle", { email: email || "—" })}
            </p>
          </div>

          <div className="grid gap-4">
            {autoFilledCode && (
              <div className="rounded-md bg-blue-500/10 border border-blue-500/20 px-3 py-2 text-sm text-blue-400">
                {t("verifyEmail.autoFilledHint")}
              </div>
            )}

            <FormField
              control={form.control}
              name="code"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-[#8ca0bc]">
                    {t("verifyEmail.codeLabel")}
                  </FormLabel>
                  <FormControl>
                    <Input
                      data-testid="code-input"
                      placeholder={t("verifyEmail.codePlaceholder")}
                      maxLength={6}
                      className="text-center text-lg tracking-[0.5em]"
                      readOnly={!!autoFilledCode}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <LoadingButton
              type="submit"
              className="w-full"
              loading={verifyMutation.isPending}
            >
              {t("verifyEmail.verifyButton")}
            </LoadingButton>

            <Button
              type="button"
              variant="outline"
              className="w-full"
              disabled={countdown > 0 || resendMutation.isPending}
              onClick={() => resendMutation.mutate()}
            >
              {countdown > 0
                ? t("verifyEmail.resendCountdown", { seconds: countdown })
                : t("verifyEmail.resendButton")}
            </Button>
          </div>

          <div className="text-center text-sm text-[#6b8ab0]">
            <RouterLink
              to="/login"
              className="text-[#00d4ff] hover:text-[#60efff] transition-colors"
            >
              {t("verifyEmail.loginLink")}
            </RouterLink>
          </div>
        </form>
      </Form>
    </AuthLayout>
  )
}
