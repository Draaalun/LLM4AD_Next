import { Link } from "@tanstack/react-router"

import { cn } from "@/lib/utils"
import icon from "/assets/images/logo.svg"
import logo from "/assets/images/logo.svg"

import "./Logo.css"

interface LogoProps {
  variant?: "full" | "icon" | "responsive"
  className?: string
  asLink?: boolean
  to?: string
}

function LogoText() {
  return (
    <svg
      viewBox="0 0 260 32"
      className="logo-text-svg h-6 w-auto group-data-[collapsible=icon]:hidden"
      aria-label="LLM4AD WEB"
    >
      <defs>
        {/* Animated gradient fill */}
        <linearGradient id="logo-grad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#60efff">
            <animate
              attributeName="stop-color"
              values="#60efff;#00d4ff;#0088ff;#60efff"
              dur="4s"
              repeatCount="indefinite"
            />
          </stop>
          <stop offset="50%" stopColor="#00d4ff">
            <animate
              attributeName="stop-color"
              values="#00d4ff;#0088ff;#60efff;#00d4ff"
              dur="4s"
              repeatCount="indefinite"
            />
          </stop>
          <stop offset="100%" stopColor="#0088ff">
            <animate
              attributeName="stop-color"
              values="#0088ff;#60efff;#00d4ff;#0088ff"
              dur="4s"
              repeatCount="indefinite"
            />
          </stop>
        </linearGradient>

        {/* Glow filter */}
        <filter id="logo-glow" x="-20%" y="-40%" width="140%" height="180%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blur" />
          <feColorMatrix
            in="blur"
            type="matrix"
            values="0 0 0 0 0  0 0.83 0 0 0  0 0 1 0 0  0 0 0 0.6 0"
            result="glow"
          />
          <feMerge>
            <feMergeNode in="glow" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Main text — bold, heavy weight */}
      <text
        x="0"
        y="24"
        fontFamily="'Inter', 'SF Pro Display', -apple-system, system-ui, sans-serif"
        fontSize="26"
        fontWeight="900"
        letterSpacing="2"
        fill="url(#logo-grad)"
        filter="url(#logo-glow)"
      >
        LLM4AD
      </text>

      {/* Separator dot */}
      <circle cx="168" cy="20" r="2.5" fill="#00d4ff" opacity="0.6">
        <animate
          attributeName="opacity"
          values="0.3;0.8;0.3"
          dur="2s"
          repeatCount="indefinite"
        />
      </circle>

      {/* "WEB" — lighter weight, spaced */}
      <text
        x="180"
        y="24"
        fontFamily="'Inter', 'SF Pro Display', -apple-system, system-ui, sans-serif"
        fontSize="20"
        fontWeight="400"
        letterSpacing="4"
        fill="#8ca0bc"
        opacity="0.85"
      >
        WEB
      </text>
    </svg>
  )
}

export function Logo({
  variant = "full",
  className,
  asLink = true,
  to = "/",
}: LogoProps) {
  const content =
    variant === "responsive" ? (
      <>
        <div className="flex items-center gap-3">
          <img
            src={logo}
            alt="LLM4AD"
            className={cn(
              "h-14 w-auto group-data-[collapsible=icon]:hidden",
              className,
            )}
          />
          <LogoText />
        </div>
        <img
          src={icon}
          alt="LLM4AD"
          className={cn(
            "size-5 hidden group-data-[collapsible=icon]:block",
            className,
          )}
        />
      </>
    ) : (
      <img
        src={variant === "full" ? logo : icon}
        alt="LLM4AD"
        className={cn(variant === "full" ? "h-6 w-auto" : "size-5", className)}
      />
    )

  if (!asLink) {
    return content
  }

  return <Link to={to}>{content}</Link>
}
