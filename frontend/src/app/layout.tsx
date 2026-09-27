import "./globals.css";

export const metadata = {
  title: "QuantForge POC",
  description: "Algorithmic trading research and paper-trading POC",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
