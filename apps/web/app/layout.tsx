import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "RiskRoom | Thesis Fracture Lab", description: "Look through the portfolio. Find the shock that reaches your loss limit. Challenge the thesis before the market does." };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
