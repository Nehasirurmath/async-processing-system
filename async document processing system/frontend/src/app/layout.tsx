import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Async CSV Profiling Workflow",
  description: "ProcessVenue async CSV profiling workspace",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
