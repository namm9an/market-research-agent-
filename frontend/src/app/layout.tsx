import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Script from "next/script";
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

        {/* Matomo Analytics (Internal Sales Tracker) */}
        <Script id="matomo-tracking" strategy="afterInteractive">
          {`
            var _paq = window._paq = window._paq || [];
            /* tracker methods like "setCustomDimension" should be called before "trackPageView" */
            _paq.push(['trackPageView']);
            _paq.push(['enableLinkTracking']);
            (function() {
              var u="//localhost:8080/matomo/";
              _paq.push(['setTrackerUrl', u+'matomo.php']);
              _paq.push(['setSiteId', '1']);
              var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0];
              g.async=true; g.async=true; g.src=u+'matomo.js'; s.parentNode.insertBefore(g,s);
            })();
          `}
        </Script>
      </body>
    </html>
  );
}
