import { toast } from "sonner"

const useCustomToast = () => {
  const showSuccessToast = (message: string) => {
    toast.success(message)
  }

  const showErrorToast = (message: string) => {
    toast.error(message)
  }

  return { showSuccessToast, showErrorToast }
}

export default useCustomToast
