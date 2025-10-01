import { Layout } from "@/components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ThumbsUp, ThumbsDown, History, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import {
  listSessions,
  getSession,
  deleteSession,
  sendFeedback,
  type ChatSession,
} from "@/lib/sessions";

export default function LearningFeedback() {
  const [sessions, setSessions] = useState<
    { id: string; title: string; createdAt: number; updatedAt: number }[]
  >([]);
  const [selected, setSelected] = useState<ChatSession | null>(null);
  const [loading, setLoading] = useState(false);

  async function refresh() {
    const l = await listSessions();
    setSessions(l.sessions || []);
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function openSession(id: string) {
    setLoading(true);
    try {
      setSelected(await getSession(id));
    } finally {
      setLoading(false);
    }
  }

  async function removeSession(id: string) {
    if (!confirm("Delete this session?")) return;
    await deleteSession(id);
    if (selected?.id === id) setSelected(null);
    await refresh();
  }

  async function rate(messageId: string, rating: "up" | "down") {
    if (!selected) return;
    await sendFeedback(selected.id, messageId, rating);
    alert("Feedback recorded");
  }

  return (
    <Layout>
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <History className="size-4" /> Interaction History
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <ul className="max-h-[60vh] overflow-auto space-y-2 text-sm">
              {sessions.length ? (
                sessions.map((s) => (
                  <li
                    key={s.id}
                    className="flex items-center gap-2 rounded border p-2"
                  >
                    <button
                      onClick={() => openSession(s.id)}
                      className="text-left flex-1 truncate"
                    >
                      <div className="font-medium truncate">
                        {s.title || s.id}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {new Date(s.updatedAt).toLocaleString()}
                      </div>
                    </button>
                    <button
                      onClick={() => removeSession(s.id)}
                      className="rounded border p-1 hover:bg-accent"
                      title="Delete"
                    >
                      <Trash2 className="size-4" />
                    </button>
                  </li>
                ))
              ) : (
                <li className="text-muted-foreground">No sessions yet</li>
              )}
            </ul>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              Feedback & Review
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-sm text-muted-foreground">Loading...</div>
            ) : !selected ? (
              <div className="text-sm text-muted-foreground">
                Select a session to review and provide feedback.
              </div>
            ) : (
              <div className="space-y-3">
                <div className="text-sm font-medium">
                  {selected.title || selected.id}
                </div>
                <div className="max-h-[58vh] overflow-auto space-y-3">
                  {selected.messages.map((m) => (
                    <div key={m.id} className="rounded border p-2">
                      <div className="text-xs uppercase tracking-wide text-muted-foreground">
                        {m.role}
                      </div>
                      <div className="whitespace-pre-wrap text-sm">
                        {m.text}
                      </div>
                      {m.role === "assistant" && (
                        <div className="mt-2 flex gap-2 text-xs">
                          <button
                            className="rounded border px-2 py-1 hover:bg-accent inline-flex items-center gap-1"
                            onClick={() => rate(m.id, "up")}
                          >
                            <ThumbsUp className="size-3" /> Good
                          </button>
                          <button
                            className="rounded border px-2 py-1 hover:bg-accent inline-flex items-center gap-1"
                            onClick={() => rate(m.id, "down")}
                          >
                            <ThumbsDown className="size-3" /> Bad
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
