import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Phishing Simulation & Benchmarking",
  description:
    "A web application for simulating phishing attacks and benchmarking detection models.",
};

const navLinks = [
  { href: "/", label: "Home" },
  { href: "/scenarios", label: "Scenarios" },
  { href: "/human-baseline", label: "Human Baseline" },
  { href: "/dashboard", label: "Dashboard" },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50">
        <nav className="border-b border-gray-200 bg-white">
          <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-3">
            <span className="text-sm font-semibold text-gray-900">
              🎣 Phishing Benchmark
            </span>
            <div className="flex gap-4">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="text-sm text-gray-600 hover:text-gray-900"
                >
                  {link.label}
                </Link>
              ))}
            </div>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
