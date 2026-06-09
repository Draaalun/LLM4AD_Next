import { Link } from "@tanstack/react-router"
import { LogOut, Settings } from "lucide-react"
import { useTranslation } from "react-i18next"

import LanguageToggle from "@/components/Common/LanguageToggle"
import ThemeToggle from "@/components/Common/ThemeToggle"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import useAuth from "@/hooks/useAuth"
import { getInitials } from "@/utils"

import icon from "/assets/images/logo.svg"

export default function ResearchHeader({ title }: { title: string }) {
  const { t } = useTranslation()
  const { user, logout } = useAuth()

  return (
    <header className="shrink-0 z-30 relative flex h-14 items-center justify-between px-5 bg-background/80 backdrop-blur-xl border-b border-border/40">
      {/* Subtle glow line at bottom */}
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent" />

      {/* Left: logo with animation */}
      <Link to="/" className="flex items-center gap-2.5 group">
        <div className="relative">
          <img
            src={icon}
            alt="LLM4AD"
            className="h-8 w-auto landing-spin-periodic"
          />
          <div className="absolute inset-0 rounded-full bg-primary/20 blur-md opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
        </div>
        <span className="text-base font-bold tracking-wider landing-gradient-animated">
          LLM4AD
        </span>
        <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
          Research
        </span>
      </Link>

      {/* Center: title */}
      <div className="absolute left-1/2 -translate-x-1/2 flex items-center gap-2">
        <div className="size-1.5 rounded-full bg-primary/60 animate-pulse" />
        <h1 className="text-sm font-semibold text-foreground/90 tracking-wide">
          {title}
        </h1>
      </div>

      {/* Right: controls */}
      <div className="flex items-center gap-1.5">
        <LanguageToggle />
        <ThemeToggle />
        <div className="w-px h-5 bg-border/60 mx-1.5" />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-accent/60 transition-all duration-200 border border-transparent hover:border-border/40 focus:outline-none"
            >
              <Avatar className="size-7 ring-2 ring-primary/20 ring-offset-1 ring-offset-background">
                <AvatarFallback className="text-xs font-semibold bg-gradient-to-br from-primary/20 to-blue-500/20 text-primary">
                  {getInitials(user?.full_name || "U")}
                </AvatarFallback>
              </Avatar>
              <span className="text-xs text-muted-foreground max-w-[80px] truncate hidden sm:inline">
                {user?.full_name}
              </span>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" sideOffset={8} className="w-48">
            <DropdownMenuLabel className="font-normal px-3 py-2">
              <p className="text-sm font-medium">{user?.full_name}</p>
              <p className="text-xs text-muted-foreground">{user?.email}</p>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="cursor-pointer" asChild>
              <Link to="/settings">
                <Settings className="size-4 mr-2" />
                {t("layout.accountSettings")}
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive focus:bg-destructive/15 focus:text-destructive cursor-pointer"
              onClick={logout}
            >
              <LogOut className="size-4 mr-2" />
              {t("layout.logout")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
