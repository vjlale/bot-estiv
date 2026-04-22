import "./globals.css";
import type { Metadata } from "next";
import { Sidebar } from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "Bot Estiv — Gardens Wood",
  description: "Director de Marketing Digital para Gardens Wood.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <div className="max-w-7xl mx-auto px-8 py-10">{children}</div>
        </main>
      </body>
    </html>
  );
}
