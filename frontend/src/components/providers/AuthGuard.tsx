"use client"

import { useEffect, useState } from "react"
import { useRouter, usePathname } from "next/navigation"
import { Loader2 } from "lucide-react"

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null)

  useEffect(() => {
    const token = localStorage.getItem("token")
    if (!token && pathname !== "/login") {
      router.push("/login")
    } else {
      setIsAuthenticated(true)
    }
  }, [pathname, router])

  if (isAuthenticated === null && pathname !== "/login") {
    return (
      <div className="min-h-screen bg-[#020504] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-emerald-500 animate-spin" />
      </div>
    )
  }

  return <>{children}</>
}
