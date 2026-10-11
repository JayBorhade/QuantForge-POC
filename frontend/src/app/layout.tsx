import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import Script from "next/script";
import { ProductUxControls } from "@/components/layout/product-ux-controls";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-geist-sans",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
});

export const metadata: Metadata = {
  title: "QuantForge — Build, Backtest, Automate, Scale",
  description:
    "Production-grade algorithmic trading infrastructure. Backtest strategies, deploy bots, and scale your trading operation.",
  keywords: ["algo trading", "backtesting", "quantitative finance", "trading bots"],
};

const themeInitScript = `(() => {
  try {
    const saved = localStorage.getItem("quantforge-theme");
    const theme = saved === "light" || saved === "dark"
      ? saved
      : (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
    document.documentElement.classList.toggle("dark", theme === "dark");
    document.documentElement.style.colorScheme = theme;
  } catch (_) {}
})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <Script id="quantforge-theme-init" strategy="beforeInteractive">{themeInitScript}</Script>
      </head>
      <body className={`${inter.variable} ${mono.variable} font-sans`}>
        <ProductUxControls />
        <div id="main-content" tabIndex={-1} className="outline-none">
          {children}
        </div>
      </body>
    </html>
  );
}
