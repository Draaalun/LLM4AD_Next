import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useCallback } from "react"

import {
  Llm4AdProvidersService,
  Llm4AdUserDefaultModelsService,
} from "@/client"

export const providersQueryKey = ["providers"] as const
export const userDefaultModelsQueryKey = ["user-default-models"] as const

export const providersQueryOptions = {
  queryKey: providersQueryKey,
  queryFn: () => Llm4AdProvidersService.listProviders({ skip: 0, limit: 100 }),
  staleTime: 5 * 60 * 1000,
}

export const userDefaultModelsQueryOptions = {
  queryKey: userDefaultModelsQueryKey,
  queryFn: () => Llm4AdUserDefaultModelsService.getUserDefaultModel(),
  staleTime: 5 * 60 * 1000,
}

export function useProviders() {
  return useQuery(providersQueryOptions)
}

export function useUserDefaultModels() {
  return useQuery(userDefaultModelsQueryOptions)
}

export function usePrefetchProviders() {
  const queryClient = useQueryClient()
  return useCallback(() => {
    queryClient.prefetchQuery(providersQueryOptions)
    queryClient.prefetchQuery(userDefaultModelsQueryOptions)
  }, [queryClient])
}
