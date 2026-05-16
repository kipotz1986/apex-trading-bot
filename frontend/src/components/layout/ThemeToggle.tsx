"use client"

import * as React from "react"
import { Moon, Sun, Monitor, GlassWater, Zap } from "lucide-react"
import { useTheme, Theme } from "@/components/providers/ThemeProvider"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  const themes: { id: Theme; label: string; icon: React.ReactNode }[] = [
    { id: "light", label: "Light", icon: <Sun className="h-4 w-4" /> },
    { id: "dark", label: "Dark", icon: <Moon className="h-4 w-4" /> },
    { id: "glass", label: "Glass", icon: <GlassWater className="h-4 w-4" /> },
    { id: "cyberpunk", label: "Cyberpunk", icon: <Zap className="h-4 w-4" /> },
  ]

  const currentTheme = themes.find((t) => t.id === theme) || themes[1]

  return (
    <DropdownMenu>
      <DropdownMenuTrigger>
        <Button variant="ghost" size="icon" className="relative h-9 w-9 rounded-full glass-button">
          {currentTheme.icon}
          <span className="sr-only">Toggle theme</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="glass-card">
        {themes.map((t) => (
          <DropdownMenuItem
            key={t.id}
            onClick={() => setTheme(t.id)}
            className={`flex items-center gap-2 cursor-pointer ${
              theme === t.id ? "bg-primary/20 text-primary" : ""
            }`}
          >
            {t.icon}
            <span>{t.label}</span>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
