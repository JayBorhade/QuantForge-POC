import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
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

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} ${mono.variable} font-sans`}>
        {children}
      </body>
    </html>
  );
}
