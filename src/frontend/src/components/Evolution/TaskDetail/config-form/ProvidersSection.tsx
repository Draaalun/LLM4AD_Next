import { Plus, Trash2 } from "lucide-react"
import { useFieldArray, useFormContext } from "react-hook-form"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

const providerTypes = ["openai", "anthropic", "openai_compatible"] as const

const defaultProvider = {
  name: "default",
  type: "openai",
  api_key: "",
  base_url: null,
  model: "gpt-4",
  temperature: 0.7,
  max_tokens: 32768,
  timeout: 60,
  max_retries: 3,
}

export default function ProvidersSection() {
  const { control } = useFormContext()
  const { t } = useTranslation()
  const { fields, append, remove } = useFieldArray({
    control,
    name: "providers",
  })

  return (
    <div className="space-y-3">
      {fields.map((field, index) => (
        <div key={field.id} className="relative rounded-lg border bg-card p-4">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-muted-foreground">
              {t("configForm.providers.providerIndex", { index: index + 1 })}
            </span>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              onClick={() => remove(index)}
            >
              <Trash2 className="size-4" />
            </Button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <FormField
              control={control}
              name={`providers.${index}.name`}
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("configForm.providers.name")}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={control}
              name={`providers.${index}.type`}
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("configForm.providers.type")}</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {providerTypes.map((pt) => (
                        <SelectItem key={pt} value={pt}>
                          {pt}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={control}
              name={`providers.${index}.model`}
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("configForm.providers.model")}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={control}
              name={`providers.${index}.api_key`}
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("configForm.providers.apiKey")}</FormLabel>
                  <FormControl>
                    <Input type="password" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={control}
              name={`providers.${index}.base_url`}
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("configForm.providers.baseUrl")}</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      value={field.value ?? ""}
                      onChange={(e) => field.onChange(e.target.value || null)}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={control}
              name={`providers.${index}.temperature`}
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("configForm.providers.temperature")}</FormLabel>
                  <FormControl>
                    <Input type="number" step="0.1" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={control}
              name={`providers.${index}.max_tokens`}
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("configForm.providers.maxTokens")}</FormLabel>
                  <FormControl>
                    <Input type="number" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={control}
              name={`providers.${index}.timeout`}
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("configForm.providers.timeout")}</FormLabel>
                  <FormControl>
                    <Input type="number" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={control}
              name={`providers.${index}.max_retries`}
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("configForm.providers.maxRetries")}</FormLabel>
                  <FormControl>
                    <Input type="number" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        </div>
      ))}
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => append(defaultProvider)}
      >
        <Plus className="mr-1 size-4" />
        {t("configForm.providers.addProvider")}
      </Button>
    </div>
  )
}
