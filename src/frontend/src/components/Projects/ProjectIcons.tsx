import { useTranslation } from "react-i18next"
import { cn } from "@/lib/utils"

/* ── 10 abstract minimalist SVG icons for projects ── */

function IconHexagon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M12 2l8.66 5v10L12 22l-8.66-5V7z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

function IconCircuit(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
      <path d="M10 6.5h4.5a2 2 0 012 2V14" />
      <path d="M14 17.5H9.5a2 2 0 01-2-2V10" />
    </svg>
  )
}

function IconMolecule(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <circle cx="12" cy="12" r="2.5" />
      <circle cx="5" cy="6" r="2" />
      <circle cx="19" cy="6" r="2" />
      <circle cx="5" cy="18" r="2" />
      <circle cx="19" cy="18" r="2" />
      <path d="M10 10L6.5 7.5M14 10l3.5-2.5M10 14l-3.5 2.5M14 14l3.5 2.5" />
    </svg>
  )
}

function IconPrism(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M12 3L3 20h18L12 3z" />
      <path d="M12 3v17" opacity="0.4" />
      <path d="M7.5 11.5h9" opacity="0.4" />
    </svg>
  )
}

function IconOrbit(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <circle cx="12" cy="12" r="2" />
      <ellipse cx="12" cy="12" rx="10" ry="4" />
      <ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(60 12 12)" />
      <ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(120 12 12)" />
    </svg>
  )
}

function IconLayers(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M12 4L3 9l9 5 9-5-9-5z" />
      <path d="M3 14l9 5 9-5" opacity="0.6" />
      <path d="M3 19l9 5 9-5" opacity="0.3" />
    </svg>
  )
}

function IconWave(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M2 12c2-4 4-6 6-6s4 6 6 6 4-6 6-6" />
      <path d="M2 17c2-4 4-6 6-6s4 6 6 6 4-6 6-6" opacity="0.4" />
    </svg>
  )
}

function IconCube(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M12 2l10 5v10l-10 5L2 17V7l10-5z" />
      <path d="M12 22V12" />
      <path d="M22 7l-10 5" />
      <path d="M2 7l10 5" />
    </svg>
  )
}

function IconDNA(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M7 2c0 5 10 5 10 10S7 17 7 22" />
      <path d="M17 2c0 5-10 5-10 10s10 5 10 10" />
      <path d="M7 7h10" opacity="0.5" />
      <path d="M7 17h10" opacity="0.5" />
      <path d="M9 12h6" opacity="0.5" />
    </svg>
  )
}

function IconNexus(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <circle cx="12" cy="4" r="2" />
      <circle cx="4" cy="12" r="2" />
      <circle cx="20" cy="12" r="2" />
      <circle cx="12" cy="20" r="2" />
      <circle cx="12" cy="12" r="2.5" />
      <path d="M12 6.5v3M12 14.5v3M6.5 12h3M14.5 12h3" />
    </svg>
  )
}

/* ── Registry ── */

export const PROJECT_ICONS = [
  { id: "hexagon", Icon: IconHexagon },
  { id: "circuit", Icon: IconCircuit },
  { id: "molecule", Icon: IconMolecule },
  { id: "prism", Icon: IconPrism },
  { id: "orbit", Icon: IconOrbit },
  { id: "layers", Icon: IconLayers },
  { id: "wave", Icon: IconWave },
  { id: "cube", Icon: IconCube },
  { id: "dna", Icon: IconDNA },
  { id: "nexus", Icon: IconNexus },
] as const

export const DEFAULT_ICON_ID = PROJECT_ICONS[0].id

/**
 * Get the icon component for a given icon ID.
 * When iconId is null/undefined, returns the first icon.
 */
export function getProjectIcon(iconId: string | null | undefined) {
  if (iconId) {
    const entry = PROJECT_ICONS.find((i) => i.id === iconId)
    if (entry) return entry.Icon
  }
  return PROJECT_ICONS[0].Icon
}

/* ── Icon picker for forms ── */

interface IconPickerProps {
  value: string
  onChange: (iconId: string) => void
}

export function IconPicker({ value, onChange }: IconPickerProps) {
  const { t } = useTranslation()
  return (
    <div className="grid grid-cols-5 gap-2">
      {PROJECT_ICONS.map(({ id, Icon }) => (
        <button
          key={id}
          type="button"
          title={t(`projects.iconNames.${id}`)}
          className={cn(
            "flex items-center justify-center rounded-md border p-2.5 transition-all hover:bg-accent/50",
            value === id
              ? "border-primary bg-primary/10 text-primary ring-1 ring-primary/30"
              : "border-input text-muted-foreground hover:text-foreground",
          )}
          onClick={() => onChange(id)}
        >
          <Icon className="size-6" />
        </button>
      ))}
    </div>
  )
}
