import { Github } from "lucide-react"

export function Footer() {
  const currentYear = new Date().getFullYear()

  return (
    <footer className="py-4 px-6 border-t border-border">
      <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
        <p className="text-muted-foreground text-sm">
          &copy; {currentYear} LLM4AD Team. All rights reserved.
        </p>
        <a
          href="https://github.com/Optima-CityU/LLM4AD"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="GitHub"
          className="text-muted-foreground hover:text-foreground transition-colors"
        >
          <Github className="size-5" />
        </a>
      </div>
    </footer>
  )
}
