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

export default function MemorySection() {
  const { control } = useFormContext()
  const { t } = useTranslation()

  return (
    <div className="grid grid-cols-2 gap-4">
      <FormField
        control={control}
        name="memory.embedding_dim"
        render={({ field }) => (
          <FormItem>
            <FormLabel>{t("configForm.memory.embeddingDimension")}</FormLabel>
            <FormControl>
              <Input type="number" {...field} />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
      <FormField
        control={control}
        name="memory.max_entries"
        render={({ field }) => (
          <FormItem>
            <FormLabel>{t("configForm.memory.maxEntries")}</FormLabel>
            <FormControl>
              <Input type="number" {...field} />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
      <FormField
        control={control}
        name="memory.similarity_threshold"
        render={({ field }) => (
          <FormItem>
            <FormLabel>{t("configForm.memory.similarityThreshold")}</FormLabel>
            <FormControl>
              <Input type="number" step="0.01" {...field} />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
      <FormField
        control={control}
        name="memory.decay_factor"
        render={({ field }) => (
          <FormItem>
            <FormLabel>{t("configForm.memory.decayFactor")}</FormLabel>
            <FormControl>
              <Input type="number" step="0.01" {...field} />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
    </div>
  )
}
