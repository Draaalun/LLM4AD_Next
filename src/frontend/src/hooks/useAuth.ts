import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"

import {
  type Body_login_login_access_token as AccessToken,
  type ApiError,
  LoginService,
  type UserPublic,
  type UserRegister,
  UsersService,
} from "@/client"
import { handleError } from "@/utils"
import { AUTH_PAGES } from "@/utils/auth"
import useCustomToast from "./useCustomToast"

const isLoggedIn = () => {
  return localStorage.getItem("access_token") !== null
}

interface UseAuthOptions {
  onPrivacyPolicyRequired?: (email: string, password: string) => void
  redirectTo?: string
}

const useAuth = (options?: UseAuthOptions) => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()

  const { data: user } = useQuery<UserPublic | null, Error>({
    queryKey: ["currentUser"],
    queryFn: UsersService.readUserMe,
    enabled: isLoggedIn(),
  })

  const signUpMutation = useMutation({
    mutationFn: (data: UserRegister) =>
      UsersService.registerUser({ requestBody: data }),
    onSuccess: (data, variables) => {
      navigate({
        to: "/verify-email",
        search: { email: variables.email, verify_code: data.verify_code || "" },
      })
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })

  const login = async (data: AccessToken) => {
    const response = await LoginService.loginAccessToken({
      formData: data,
    })
    localStorage.setItem("access_token", response.access_token)
    localStorage.setItem("refresh_token", response.refresh_token)
  }

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: () => {
      if (options?.redirectTo) {
        navigate({ to: options.redirectTo })
      } else {
        navigate({ to: "/projects" })
      }
    },
    onError: (err: ApiError, variables: AccessToken) => {
      if (err.status === 409) {
        navigate({
          to: "/verify-email",
          search: { email: variables.username, verify_code: "" },
        })
        return
      }
      if (err.status === 403) {
        const errorDetail = (err.body as any)?.detail || ""
        if (
          errorDetail.includes("隐私协议") ||
          errorDetail.includes("Privacy Policy")
        ) {
          if (options?.onPrivacyPolicyRequired) {
            options.onPrivacyPolicyRequired(
              variables.username,
              variables.password,
            )
          }
          return
        }
      }
      handleError.call(showErrorToast, err)
    },
  })

  const logout = () => {
    const currentPath = window.location.pathname
    localStorage.removeItem("access_token")
    localStorage.removeItem("refresh_token")
    document.cookie =
      "code_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/"
    if (AUTH_PAGES.some((p) => currentPath.startsWith(p))) {
      navigate({ to: "/login" })
    } else {
      const redirectTarget = currentPath + window.location.search
      navigate({ to: "/login", search: { redirect: redirectTarget } })
    }
  }

  return {
    signUpMutation,
    loginMutation,
    logout,
    user,
  }
}

export { isLoggedIn }
export default useAuth
