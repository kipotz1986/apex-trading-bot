import type { Metadata } from "next";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

// Temporarily using system fonts to bypass Google Fonts fetch error in Docker build
const geistSans = { variable: "font-sans" };
const geistMono = { variable: "font-mono" };

export const metadata: Metadata = {
  title: "APEX AI Trading Bot",
  description: "Next-generation institutional crypto trading bot powered by multi-agent AI.",
};

import QueryProvider from "@/components/providers/QueryProvider";
import AuthGuard from "@/components/providers/AuthGuard";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <QueryProvider>
          <AuthGuard>
            {children}
          </AuthGuard>
        </QueryProvider>
        <Toaster theme="dark" position="top-right" richColors />
      </body>
    </html>
  );
}
