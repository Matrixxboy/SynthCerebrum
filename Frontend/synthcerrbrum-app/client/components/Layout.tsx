import { NavLink, Link } from "react-router-dom";
import { cn } from "@/lib/utils";
import { ReactNode } from "react";
import {
  Bot,
  Database,
  Settings,
  BrainCircuit,
  User as UserIcon,
} from "lucide-react";
import { SessionHistory } from "./SessionHistory";

export function Layout({ children }: { children: ReactNode }) {
  if (typeof document !== "undefined") {
    const pref = localStorage.getItem("theme") as
      | "light"
      | "dark"
      | "system"
      | null;
    if (pref === "dark") document.documentElement.classList.add("dark");
    if (pref === "light") document.documentElement.classList.remove("dark");
    if (!pref || pref === "system") {
      const mql = window.matchMedia("(prefers-color-scheme: dark)");
      document.documentElement.classList.toggle("dark", mql.matches);
    }
  }
  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted">
      <header className="sticky top-0 z-40 w-full border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto max-w-7xl px-4 py-3 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="size-8 rounded-md bg-gradient-to-br from-indigo-500 to-cyan-500"></div>
            <span className="text-lg font-semibold tracking-tight">
              Aegis Local AI
            </span>
          </Link>
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <span className="hidden sm:inline">Engine:</span>
            <span className="px-2 py-1 rounded-md bg-secondary text-secondary-foreground">
              Offline
            </span>
          </div>
        </div>
      </header>
      <div className="mx-auto max-w-7xl px-4 py-6 grid grid-cols-1 lg:grid-cols-[240px_1fr] gap-6">
        <aside className="lg:sticky lg:top-16 lg:self-start">
          <nav className="rounded-lg border bg-card/60 backdrop-blur p-2 text-sm">
            <NavItem
              to="/"
              icon={<Bot className="size-4" />}
              label="Agent Workspace"
            />
            <NavItem
              to="/rag"
              icon={<Database className="size-4" />}
              label="Knowledge Base"
            />
            <NavItem
              to="/engine"
              icon={<Settings className="size-4" />}
              label="Model & Engine"
            />
            <NavItem
              to="/feedback"
              icon={<BrainCircuit className="size-4" />}
              label="Learning & Feedback"
            />
            <NavItem
              to="/settings"
              icon={<UserIcon className="size-4" />}
              label="User Settings"
            />
          </nav>
          <SessionHistory />
        </aside>
        <main className="min-w-0">{children}</main>
      </div>
      <footer className="border-t bg-background/50">
        <div className="mx-auto max-w-7xl px-4 py-6 text-xs text-muted-foreground">
          Offline-first • Electron-ready • RAG + Agent Orchestrator
        </div>
      </footer>
    </div>
  );
}

function NavItem({
  to,
  icon,
  label,
}: {
  to: string;
  icon: ReactNode;
  label: string;
}) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        cn(
          "flex items-center gap-2 rounded-md px-3 py-2 hover:bg-accent hover:text-accent-foreground",
          isActive && "bg-primary/10 text-primary",
        )
      }
    >
      {icon}
      <span>{label}</span>
    </NavLink>
  );
}