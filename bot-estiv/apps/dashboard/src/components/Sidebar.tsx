"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  MessageSquare,
  Calendar,
  CheckSquare,
  Target,
  LineChart,
  Image as ImageIcon,
  FolderOpen,
  FileText,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/cn";

const items = [
  { href: "/", label: "Panel", icon: LayoutDashboard },
  { href: "/inbox", label: "Inbox", icon: MessageSquare },
  { href: "/calendar", label: "Calendario", icon: Calendar },
  { href: "/approvals", label: "Aprobaciones", icon: CheckSquare },
  { href: "/posts", label: "Posts", icon: FileText },
  { href: "/campaigns", label: "Meta Ads", icon: Target },
  { href: "/analytics", label: "Analytics", icon: LineChart },
  { href: "/library", label: "Biblioteca obras", icon: FolderOpen },
  { href: "/assets", label: "Assets generados", icon: ImageIcon },
  { href: "/settings", label: "Configuración", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-64 min-h-screen bg-carbon text-bone flex flex-col">
      <div className="px-6 py-8 border-b border-bone/10">
        <h1 className="font-heading text-2xl leading-tight">Bot Estiv</h1>
        <p className="text-xs text-bone/60 mt-1">Gardens Wood</p>
      </div>
      <nav className="flex-1 py-4">
        {items.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-6 py-3 text-sm transition-colors",
                active
                  ? "bg-bone/10 text-bone border-l-2 border-fire"
                  : "text-bone/70 hover:bg-bone/5 hover:text-bone",
              )}
            >
              <Icon size={18} />
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="px-6 py-4 text-xs text-bone/40 border-t border-bone/10">
        Diseñado para Durar.
        <br />
        Creado para Unir.
      </div>
    </aside>
  );
}
