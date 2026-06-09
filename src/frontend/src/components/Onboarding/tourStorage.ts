const TOUR_KEY_PREFIX = "onboarding:tour:"
const ALL_DONE_KEY = "onboarding:all_done"

export function isTourDone(tourId: string): boolean {
  if (typeof window === "undefined") return true
  try {
    if (localStorage.getItem(ALL_DONE_KEY) === "1") return true
    return localStorage.getItem(TOUR_KEY_PREFIX + tourId) === "1"
  } catch {
    return true
  }
}

export function markTourDone(tourId: string): void {
  try {
    localStorage.setItem(TOUR_KEY_PREFIX + tourId, "1")
  } catch {
    // ignore
  }
}

export function markAllToursDone(): void {
  try {
    localStorage.setItem(ALL_DONE_KEY, "1")
  } catch {
    // ignore
  }
}

export function resetAllTours(): void {
  try {
    localStorage.removeItem(ALL_DONE_KEY)
    const keysToRemove: string[] = []
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i)
      if (k?.startsWith(TOUR_KEY_PREFIX)) keysToRemove.push(k)
    }
    keysToRemove.forEach((k) => {
      localStorage.removeItem(k)
    })
  } catch {
    // ignore
  }
}
