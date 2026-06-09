import { zodResolver } from "@hookform/resolvers/zod"
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
} from "@tanstack/react-router"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { useTranslation } from "react-i18next"
import { z } from "zod"
import { AuthLayout } from "@/components/Common/AuthLayout"
import { PrivacyPolicyDialog } from "@/components/Common/PrivacyPolicyDialog"
import { Checkbox } from "@/components/ui/checkbox"
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
import { PasswordInput } from "@/components/ui/password-input"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import i18n from "@/i18n"

export const Route = createFileRoute("/signup")({
  component: SignUp,
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
        title: i18n.t("signup.pageTitle"),
      },
    ],
  }),
})

function SignUp() {
  const { t } = useTranslation()
  const { signUpMutation } = useAuth()
  const [showPrivacyDialog, setShowPrivacyDialog] = useState(false)

  const formSchema = z
    .object({
      email: z.email().max(255),
      full_name: z
        .string()
        .min(1, { message: t("validation.nameRequired") })
        .max(255),
      password: z
        .string()
        .min(1, { message: t("validation.passwordRequired") })
        .min(8, { message: t("validation.passwordMinLength") })
        .max(255),
      confirm_password: z
        .string()
        .min(1, { message: t("validation.confirmPasswordRequired") })
        .max(255),
      privacy_policy_accepted: z.boolean().refine((val) => val === true, {
        message: t("signup.privacyPolicyRequired"),
      }),
    })
    .refine((data) => data.password === data.confirm_password, {
      message: t("validation.passwordMismatch"),
      path: ["confirm_password"],
    })

  type FormData = z.infer<typeof formSchema>

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      email: "",
      full_name: "",
      password: "",
      confirm_password: "",
      privacy_policy_accepted: false,
    },
  })

  const onSubmit = (data: FormData) => {
    if (signUpMutation.isPending) return
    const { confirm_password: _confirm_password, ...submitData } = data
    signUpMutation.mutate(submitData)
  }

  return (
    <AuthLayout>
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="flex flex-col gap-5"
        >
          <div className="flex flex-col items-center gap-1 text-center mb-1">
            <h1 className="text-2xl font-bold tracking-wide landing-gradient">
              {t("signup.title")}
            </h1>
            <p className="text-sm text-muted-foreground">
              {t("signup.subtitle")}
            </p>
          </div>

          <div className="grid gap-3.5">
            <FormField
              control={form.control}
              name="full_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-foreground">
                    {t("signup.nameLabel")}
                  </FormLabel>
                  <FormControl>
                    <Input
                      data-testid="full-name-input"
                      placeholder={t("signup.namePlaceholder")}
                      type="text"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-foreground">
                    {t("signup.emailLabel")}
                  </FormLabel>
                  <FormControl>
                    <Input
                      data-testid="email-input"
                      placeholder="user@example.com"
                      type="email"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-foreground">
                    {t("signup.passwordLabel")}
                  </FormLabel>
                  <FormControl>
                    <PasswordInput
                      data-testid="password-input"
                      placeholder={t("signup.passwordPlaceholder")}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="confirm_password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-foreground">
                    {t("signup.confirmPasswordLabel")}
                  </FormLabel>
                  <FormControl>
                    <PasswordInput
                      data-testid="confirm-password-input"
                      placeholder={t("signup.confirmPasswordPlaceholder")}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="privacy_policy_accepted"
              render={({ field }) => (
                <FormItem>
                  <div className="flex items-start space-x-3">
                    <FormControl>
                      <Checkbox
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                    <div className="space-y-1 leading-none">
                      <FormLabel className="text-sm font-normal text-foreground">
                        {t("signup.privacyPolicyLabel")}{" "}
                        <button
                          type="button"
                          onClick={() => setShowPrivacyDialog(true)}
                          className="text-primary hover:text-primary/80 transition-colors underline"
                        >
                          {t("signup.privacyPolicyLink")}
                        </button>
                      </FormLabel>
                      <FormMessage />
                    </div>
                  </div>
                </FormItem>
              )}
            />

            <LoadingButton
              type="submit"
              className="w-full"
              loading={signUpMutation.isPending}
              disabled={!form.watch("privacy_policy_accepted")}
            >
              {t("signup.signupButton")}
            </LoadingButton>
          </div>

          <div className="text-center text-sm text-muted-foreground">
            {t("signup.hasAccount")}{" "}
            <RouterLink
              to="/login"
              className="text-primary hover:text-primary/80 transition-colors"
            >
              {t("signup.loginLink")}
            </RouterLink>
          </div>
        </form>
      </Form>

      <PrivacyPolicyDialog
        open={showPrivacyDialog}
        onAccept={() => {
          form.setValue("privacy_policy_accepted", true)
          setShowPrivacyDialog(false)
        }}
        onDecline={() => {
          form.setValue("privacy_policy_accepted", false)
          setShowPrivacyDialog(false)
        }}
        allowClose={true}
      />
    </AuthLayout>
  )
}
