import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PACE | Training, with intention",
  description: "A focused space for your training history and progress.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
