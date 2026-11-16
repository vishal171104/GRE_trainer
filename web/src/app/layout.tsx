import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "WordOrbit",
  description: "AI vocabulary trainer for GRE preparation.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
