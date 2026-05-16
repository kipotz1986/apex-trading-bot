"use client"

import { useEffect, useState } from "react"
import { useRouter, usePathname } from "next/navigation"
import { Loader2 } from "lucide-react"
import { api } from "@/lib/api"

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null)

  useEffect(() => {
    if (pathname === "/login") {
      setIsAuthenticated(true)
      return
    }
    api.get("/auth/me")
      .then(() => setIsAuthenticated(true))
      .catch(() => {
        setIsAuthenticated(false)
        router.push("/login")
      })
  }, [pathname, router])

  if (isAuthenticated === null) {
    return (
      <div className="min-h-dvh bg-[#020504] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    )
  }

  return <>{children}</>
}
