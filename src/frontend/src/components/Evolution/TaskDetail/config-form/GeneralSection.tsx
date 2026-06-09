import { useFormContext } from "react-hook-form"
import { useTranslation } from "react-i18next"

import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"

export default function GeneralSection() {
  const { control } = useFormContext()
  const { t } = useTranslation()

  return (
    <div className="grid grid-cols-2 gap-4">
      <FormField
        control={control}
        name="project_name"
        render={({ field }) => (
          <FormItem>
            <FormLabel>{t("configForm.general.projectName")}</FormLabel>
            <FormControl>
              <Input {...field} />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
      <FormField
        control={control}
        name="run_id"
        render={({ field }) => (
          <FormItem>
            <FormLabel>{t("configForm.general.runId")}</FormLabel>
            <FormControl>
              <Input {...field} value={field.value ?? ""} />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
      <FormField
        control={control}
        name="random_seed"
        render={({ field }) => (
          <FormItem>
            <FormLabel>{t("configForm.general.randomSeed")}</FormLabel>
            <FormControl>
              <Input type="number" {...field} />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
      <FormField
        control={control}
        name="base_dir"
        render={({ field }) => (
          <FormItem>
            <FormLabel>{t("configForm.general.baseDirectory")}</FormLabel>
            <FormControl>
              <Input {...field} />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
      <FormField
        control={control}
        name="background"
        render={({ field }) => (
          <FormItem className="col-span-2">
            <FormLabel>{t("configForm.general.background")}</FormLabel>
            <FormControl>
              <Input {...field} />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
    </div>
  )
}
