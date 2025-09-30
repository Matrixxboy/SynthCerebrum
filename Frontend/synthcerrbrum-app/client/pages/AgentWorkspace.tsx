import { useEffect, useMemo, useRef, useState } from "react";
import { Layout } from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Paperclip, Send, File, Brain, Database, Files } from "lucide-react";
import { ingestFiles, type IngestionJob, type IngestionOptions } from "@/lib/ingestion";
import { listKnowledgeSets } from "@/lib/vectorStore";
import { processQuery } from "@/lib/localRagEngine";
import { ollamaGenerate } from "@/lib/api";
import JsonRenderer from "@/components/JsonRenderer";
import { saveSession } from "@/lib/sessions";

interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  structured?: unknown;
}

export default function AgentWorkspace() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [jobs, setJobs] = useState<IngestionJob[]>([]);
  const [useOllama, setUseOllama] = useState(false);
  const [useMemory, setUseMemory] = useState(true);
  const [useRag, setUseRag] = useState(true);
  const [knowledgeSet, setKnowledgeSet] = useState("default");
  const [availableSets, setAvailableSets] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState<string>(() => localStorage.getItem('current_session_id') || "");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    async function loadKnowledgeSets() {
      setAvailableSets(await listKnowledgeSets());
    }
    loadKnowledgeSets();
  }, []);

  useEffect(()=>{
    const handler = (e: any) => {
      const { messageId, rating } = e.detail || {};
      if (!messageId || !rating || !sessionId) return;
      fetch('/api/feedback', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ sessionId, messageId, rating }) });
    };
    window.addEventListener('feedback_click' as any, handler as any);
    return () => window.removeEventListener('feedback_click' as any, handler as any);
  }, [sessionId]);

  useEffect(()=>{
    if (!messages.length) return;
    const persist = async () => {
      const saved = await saveSession({ id: sessionId || undefined, title: messages[0]?.text?.slice(0, 60) || 'Session', messages });
      if (!sessionId) {
        setSessionId(saved.id);
        localStorage.setItem('current_session_id', saved.id);
      }
    };
    void persist();
  }, [messages]);

  const handleFiles = async (files: FileList) => {
    const fileArray = Array.from(files);
    const opts: IngestionOptions = { knowledgeSet, chunkSize: 800, embedImages: true };
    for await (const job of ingestFiles(fileArray, opts)) {
      setJobs((prev) => {
        const next = prev.filter((j) => j.id !== job.id);
        next.unshift(job);
        return next.slice(0, 25);
      });
    }
    setAvailableSets(await listKnowledgeSets());
  };

  const onSubmit = async () => {
    if (!input.trim()) return;
    setBusy(true);
    const userMsg: Message = { id: crypto.randomUUID(), role: "user", text: input };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    try {
      if (useOllama) {
        const res = await ollamaGenerate("llama2", userMsg.text);
        const assistantMsg: Message = { id: crypto.randomUUID(), role: "assistant", text: "" };
        setMessages((m) => [...m, assistantMsg]);

        const reader = res.body?.getReader();
        if (!reader) return;

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");

          for (let i = 0; i < lines.length - 1; i++) {
            const line = lines[i];
            if (line.trim() === "") continue;
            try {
              const chunk = JSON.parse(line);
              setMessages((m) => {
                const lastMsg = m[m.length - 1];
                if (lastMsg.id === assistantMsg.id) {
                  return [...m.slice(0, -1), { ...lastMsg, text: lastMsg.text + chunk.response }];
                }
                return m;
              });
            } catch (e) {
              console.error("Failed to parse stream chunk", e);
            }
          }
          buffer = lines[lines.length - 1];
        }
      } else {
        const res = await processQuery({ query: userMsg.text, knowledgeSet, useMemory, useRag, history: messages });
        const assistant: Message = { id: crypto.randomUUID(), role: "assistant", text: res.text, structured: res.structured };
        setMessages((m) => [...m, assistant]);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <Layout>
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-6">
        <Card className="overflow-hidden">
          <CardHeader className="border-b bg-gradient-to-r from-indigo-50 to-cyan-50 dark:from-indigo-950/30 dark:to-cyan-950/30">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-xl">
                <Brain className="size-5 text-primary"/> Agent Workspace
              </CardTitle>
              <button
                className="text-xs rounded-md border px-2 py-1 hover:bg-accent"
                onClick={() => {
                  setMessages([]);
                  setSessionId("");
                  localStorage.removeItem('current_session_id');
                }}
              >
                New session
              </button>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="h-[60vh] md:h-[64vh] overflow-y-auto p-4 space-y-4">
              {messages.length === 0 ? (
                <div className="h-full flex items-center justify-center text-center text-muted-foreground">
                  Ask a question or drop files to ground the answer with your knowledge.
                </div>
              ) : (
                messages.map((m) => (
                  <div key={m.id} className={cn("flex", m.role === "assistant" ? "justify-start" : "justify-end")}> 
                    <div className={cn("max-w-[85%] rounded-lg px-4 py-3 text-sm shadow", m.role === "assistant" ? "bg-accent/60" : "bg-primary text-primary-foreground")}
                    >
                      <div className="whitespace-pre-wrap">{m.text}</div>
                      {m.structured ? (
                        <div className="mt-3 rounded-md border bg-background p-2 text-foreground">
                          <JsonRenderer data={m.structured} />
                        </div>
                      ) : null}
                      {m.role === 'assistant' ? (
                        <div className="mt-2 flex gap-2 text-xs opacity-80">
                          <span>Feedback:</span>
                          <button className="rounded border px-1" onClick={()=>window.dispatchEvent(new CustomEvent('feedback_click', { detail: { messageId: m.id, rating: 'up' } }))}>👍</button>
                          <button className="rounded border px-1" onClick={()=>window.dispatchEvent(new CustomEvent('feedback_click', { detail: { messageId: m.id, rating: 'down' } }))}>👎</button>
                        </div>
                      ) : null}
                    </div>
                  </div>
                ))
              )}
            </div>
            <div className="border-t p-3">
              <div className="flex items-end gap-2">
                <div className="flex-1">
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Type your message..."
                    rows={3}
                    className="w-full resize-none rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                  <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
                    <button
                      className="inline-flex items-center gap-1 hover:text-foreground"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <Paperclip className="size-3.5"/> Attach files
                    </button>
                    <input ref={fileInputRef} type="file" multiple className="hidden" onChange={(e) => e.target.files && handleFiles(e.target.files)} />
                  </div>
                </div>
                <Button disabled={busy} onClick={onSubmit} className="shrink-0">
                  <Send className="mr-2"/> Send
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base"><Database className="size-4"/> Active Context</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <ToggleRow
                label="Memory Binding (Layer 1)"
                description="Include recent conversation history"
                enabled={useMemory}
                onToggle={() => setUseMemory((v) => !v)}
              />
              <ToggleRow
                label="RAG Context (Layer 2)"
                description="Ground answers with your knowledge base"
                enabled={useRag}
                onToggle={() => setUseRag((v) => !v)}
              />
              <ToggleRow
                label="Use Ollama"
                description="Use Ollama for response generation"
                enabled={useOllama}
                onToggle={() => setUseOllama((v) => !v)}
              />
              <div>
                <div className="text-xs text-muted-foreground mb-1">Knowledge Set</div>
                <select
                  value={knowledgeSet}
                  onChange={(e) => setKnowledgeSet(e.target.value)}
                  className="w-full rounded-md border bg-background px-2 py-1.5 text-sm"
                >
                  {["default", ...availableSets.filter((s) => s !== "default")].map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base"><Files className="size-4"/> File Insight</CardTitle>
            </CardHeader>
            <CardContent>
              {jobs.length === 0 ? (
                <div className="text-sm text-muted-foreground">No files ingested yet.</div>
              ) : (
                <ul className="space-y-2 text-sm">
                  {jobs.map((j) => (
                    <li key={j.id} className="flex items-center gap-2">
                      <File className="size-4 text-muted-foreground"/>
                      <span className="truncate" title={j.name}>{j.name}</span>
                      <span className={cn("ml-auto rounded px-1.5 py-0.5 text-[10px]", statusStyles(j.status))}>{j.status}</span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  );
}

function statusStyles(status: IngestionJob["status"]) {
  switch (status) {
    case "queued":
      return "bg-muted text-foreground/70";
    case "parsing":
      return "bg-amber-100 text-amber-900 dark:bg-amber-900/30 dark:text-amber-200";
    case "chunking":
      return "bg-blue-100 text-blue-900 dark:bg-blue-900/30 dark:text-blue-200";
    case "embedding":
      return "bg-indigo-100 text-indigo-900 dark:bg-indigo-900/30 dark:text-indigo-200";
    case "stored":
      return "bg-emerald-100 text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-200";
    case "error":
      return "bg-red-100 text-red-900 dark:bg-red-900/30 dark:text-red-200";
    default:
      return "bg-muted";
  }
}

function ToggleRow({ label, description, enabled, onToggle }: { label: string; description: string; enabled: boolean; onToggle: () => void }) {
  return (
    <div className="flex items-center gap-3">
      <button
        onClick={onToggle}
        className={cn(
          "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
          enabled ? "bg-primary" : "bg-muted"
        )}
        aria-pressed={enabled}
      >
        <span
          className={cn(
            "inline-block size-5 transform rounded-full bg-background transition-transform",
            enabled ? "translate-x-5" : "translate-x-1"
          )}
        />
      </button>
      <div>
        <div className="text-sm">{label}</div>
        <div className="text-xs text-muted-foreground">{description}</div>
      </div>
    </div>
  );
}