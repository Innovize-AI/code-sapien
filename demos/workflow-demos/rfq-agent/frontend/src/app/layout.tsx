import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Inter, Libre_Baskerville } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const baskerville = Libre_Baskerville({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-baskerville",
});

export const metadata: Metadata = {
  title: "RFQ Agent — InnovizeAI",
  description: "AI-powered RFQ processing and quotation generation",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${baskerville.variable} font-sans`}>
        <Sidebar />
        <main className="ml-[240px] min-h-screen p-8 bg-brand-bg">
          {children}
        </main>
      </body>
    </html>
  );
}
