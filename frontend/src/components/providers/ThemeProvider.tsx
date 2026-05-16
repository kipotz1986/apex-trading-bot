"use client"

import * as React from "react"

export type Theme = "dark" | "light" | "cyberpunk" | "glass"

interface ThemeContextType {
  theme: Theme
  setTheme: (theme: Theme) => void
}

const ThemeContext = React.createContext<ThemeContextType | undefined>(undefined)

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = React.useState<Theme>("dark")

  React.useEffect(() => {
    const savedTheme = localStorage.getItem("apex-theme") as Theme
    if (savedTheme) {
      setThemeState(savedTheme)
    }
  }, [])

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme)
    localStorage.setItem("apex-theme", newTheme)
    
    // Update HTML class
    const root = window.document.documentElement
    root.classList.remove("dark", "light", "cyberpunk", "glass")
    root.classList.add(newTheme)
  }

  // Initialize class on first render
  React.useEffect(() => {
    const root = window.document.documentElement
    root.classList.remove("dark", "light", "cyberpunk", "glass")
    root.classList.add(theme)
  }, [theme])

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = React.useContext(ThemeContext)
  if (context === undefined) {
    throw new Error("useTheme must be used within a ThemeProvider")
  }
  return context
}
