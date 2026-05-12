/**
 * Locale-aware date/time formatters.
 * All functions accept a UTC ISO string from the backend and render in the
 * client's local timezone using the browser's navigator.language.
 */
const locale = typeof navigator !== "undefined" ? navigator.language : undefined

/** "15:30:45" */
export function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString(locale, {
    hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
  })
}

/** "15:30:45.123" */
export function fmtTimeMs(iso: string): string {
  const d = new Date(iso)
  const ms = String(d.getMilliseconds()).padStart(3, "0")
  return d.toLocaleTimeString(locale, {
    hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
  }) + "." + ms
}

/** "2026-05-11 15:30" */
export function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString(locale, {
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", hour12: false,
  })
}

/** "2026-05-11 15:30:45" */
export function fmtDateTimeSec(iso: string): string {
  return new Date(iso).toLocaleString(locale, {
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
  })
}

/** "May 11" (locale-aware month name) */
export function fmtDateShort(iso: string): string {
  return new Date(iso).toLocaleDateString(locale, { month: "short", day: "numeric" })
}

/** "May 11, 2026" */
export function fmtDateLong(iso: string): string {
  return new Date(iso).toLocaleDateString(locale, {
    month: "short", day: "numeric", year: "numeric",
  })
}

/** "May 11, 15:30" */
export function fmtDateShortTime(iso: string): string {
  return new Date(iso).toLocaleString(locale, {
    month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit", hour12: false,
  })
}

/** "2026-05-11" — stable ISO date portion in local TZ (for filenames) */
export function fmtDateISO(date: Date = new Date()): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, "0")
  const d = String(date.getDate()).padStart(2, "0")
  return `${y}-${m}-${d}`
}
