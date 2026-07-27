import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Phishing Simulation & Benchmarking",
  description:
    "A web application for simulating phishing attacks and benchmarking detection models.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
