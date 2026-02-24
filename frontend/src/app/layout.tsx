import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Sidebar from "@/components/Sidebar";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Market Research Agent — AI-Powered Company Analysis",
  description:
    "Generate comprehensive market research reports with SWOT analysis, trends, and competitive insights in seconds. Powered by NVIDIA Nemotron on E2E Networks.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} antialiased flex h-screen overflow-hidden bg-background`}>
        <Sidebar />
        <div className="flex-1 overflow-y-auto relative">
          {children}
        </div>
      </body>
    </html>
  );
}
