import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "PolicyChangeGate | GenLayer", description: "Challengeable, consensus-backed authorization for policy changes." };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
