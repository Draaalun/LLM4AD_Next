import { useCallback, useEffect, useRef, useState } from "react"

/**
 * useState with localStorage persistence. Reads once on mount, writes on every
 * change. Falls back to `initial` if storage is unavailable or the stored
 * value can't be parsed.
 */
export function usePersistentState<T>(
  key: string,
  initial: T | (() => T),
): [T, (value: T | ((prev: T) => T)) => void] {
  const [state, setState] = useState<T>(() => {
    if (typeof window === "undefined") {
      return typeof initial === "function" ? (initial as () => T)() : initial
    }
    try {
      const raw = window.localStorage.getItem(key)
      if (raw != null) return JSON.parse(raw) as T
    } catch {
      /* ignore parse / access errors */
    }
    return typeof initial === "function" ? (initial as () => T)() : initial
  })

  const keyRef = useRef(key)
  keyRef.current = key

  useEffect(() => {
    try {
      window.localStorage.setItem(keyRef.current, JSON.stringify(state))
    } catch {
      /* quota / disabled — silently ignore */
    }
  }, [state])

  const set = useCallback((value: T | ((prev: T) => T)) => {
    setState(value)
  }, [])

  return [state, set]
}
