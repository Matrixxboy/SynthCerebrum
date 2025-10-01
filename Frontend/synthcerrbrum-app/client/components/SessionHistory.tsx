import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { listSessions, deleteSession } from "@/lib/sessions";
import { cn } from "@/lib/utils";
import { MessageSquare, Trash2 } from "lucide-react";

export function SessionHistory() {
  const [sessions, setSessions] = useState<{ id: string; title: string }[]>([]);

  async function load() {
    const { sessions: s } = await listSessions();
    setSessions(s);
  }

  useEffect(() => {
    load();
    window.addEventListener("session_updated", load);
    return () => window.removeEventListener("session_updated", load);
  }, []);

  async function handleDelete(id: string) {
    if (confirm("Are you sure you want to delete this session?")) {
      await deleteSession(id);
      window.dispatchEvent(new Event("session_updated"));
    }
  }

  return (
    <div className="rounded-lg border bg-card/60 backdrop-blur p-2 text-sm mt-4">
      <h2 className="px-3 py-2 text-xs font-semibold text-muted-foreground">Sessions</h2>
      <div className="space-y-1">
        {sessions.map((s) => (
          <NavLink
            key={s.id}
            to={`/session/${s.id}`}
            className={({ isActive }) =>
              cn(
                "flex items-center justify-between gap-2 rounded-md px-3 py-2 hover:bg-accent hover:text-accent-foreground",
                isActive && "bg-primary/10 text-primary",
              )
            }
          >
            <div className="flex items-center gap-2 truncate">
              <MessageSquare className="size-4" />
              <span className="truncate">{s.title}</span>
            </div>
            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                handleDelete(s.id);
              }}
              className="p-1 rounded-md hover:bg-destructive/20 hover:text-destructive opacity-60 hover:opacity-100"
            >
              <Trash2 className="size-4" />
            </button>
          </NavLink>
        ))}
      </div>
    </div>
  );
}
