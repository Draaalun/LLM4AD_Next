const root = document.documentElement

export function getCSSVar(name: string): string {
  return getComputedStyle(root).getPropertyValue(name).trim()
}

export function getPrimaryRGB(): string {
  return getCSSVar("--primary-rgb") || "0, 212, 255"
}
