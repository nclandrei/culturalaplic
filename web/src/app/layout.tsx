import type { Metadata } from "next";
import { DM_Sans } from "next/font/google";
import { SpeedInsights } from "@vercel/speed-insights/next";
import { Analytics } from "@vercel/analytics/next";
import { PostHogProvider } from "./providers";
import "./globals.css";

const dmSans = DM_Sans({
  variable: "--font-dm-sans",
  subsets: ["latin"],
  weight: ["400", "500", "700"],
});

export const metadata: Metadata = {
  title: "Cultură la plic",
  description: "Evenimente culturale în București",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ro">
      <body className={`${dmSans.variable} antialiased`}>
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:bg-main focus:px-4 focus:py-2 focus:font-bold focus:rounded-base focus:border-2 focus:border-border"
        >
          Salt la conținut
        </a>
        <PostHogProvider>{children}</PostHogProvider>
        <SpeedInsights />
        <Analytics />
      </body>
    </html>
  );
}
