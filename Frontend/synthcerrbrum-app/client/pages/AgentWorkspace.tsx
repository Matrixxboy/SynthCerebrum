import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Paperclip, Send, File, Brain, Database, Files, X } from "lucide-react";
import { listKnowledgeSets } from "@/lib/vectorStore";
import { processQuery } from "@/lib/localRagEngine";
import { ollamaGenerate } from "@/lib/api";
import JsonRenderer from "@/components/JsonRenderer";
import { getSession, saveSession, type ChatMessage } from "@/lib/sessions";

type Attachment =
  | { name: string; content: string; type: string }
  | { name: string; url: string; type: string };

export default function AgentWorkspace() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [attachment, setAttachment] = useState<Attachment | null>(null);
  const [useOllama, setUseOllama] = useState(false);
  const [useMemory, setUseMemory] = useState(true);
  const [useRag, setUseRag] = useState(true);
  const [knowledgeSet, setKnowledgeSet] = useState("default");
  const [availableSets, setAvailableSets] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const { id: sessionId } = useParams<{ id: string }>();
  const navigate = useNavigate();

  useEffect(() => {
    async function loadKnowledgeSets() {
      setAvailableSets(await listKnowledgeSets());
    }
    loadKnowledgeSets();
  }, []);

  useEffect(() => {
    if (sessionId) {
      getSession(sessionId).then((session) => {
        setMessages(session.messages);
      });
    } else {
      setMessages([]);
    }
  }, [sessionId]);

  useEffect(() => {
    if (!messages.length) return;
    const persist = async () => {
      const saved = await saveSession({
        id: sessionId,
        title: messages[0]?.text?.slice(0, 60) || "New Session",
        messages,
      });
      if (!sessionId) {
        navigate(`/session/${saved.id}`, { replace: true });
      }
      window.dispatchEvent(new Event("session_updated"));
    };
    void persist();
  }, [messages]);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setAttachment(null);

    if (file.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onload = (loadEvent) => {
        const dataUrl = loadEvent.target?.result as string;
        setAttachment({ name: file.name, url: dataUrl, type: file.type });
      };
      reader.readAsDataURL(file);
    } else {
      try {
        const content = await file.text();
        setAttachment({ name: file.name, content, type: file.type });
      } catch (err) {
        console.error("Failed to read file", err);
      }
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const onSubmit = async () => {
    const text = input.trim();
    if (!text && !attachment) return;
    setBusy(true);

    let promptText = text;
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      text: input,
    };

    if (attachment) {
      if ("content" in attachment) { // Text-based file
        promptText = `Using the following file as context:\n\n--- ${attachment.name} ---\n${attachment.content}\n\n---\n\nMy question is: ${text}`;
        userMsg.fileAttachment = { name: attachment.name, type: attachment.type };
      } else if ("url" in attachment) { // Image file
        userMsg.imageUrl = attachment.url;
      }
      setAttachment(null);
    }

    setMessages((m) => [...m, userMsg]);
    setInput("");

    try {
      if (useOllama) {
        const res = await ollamaGenerate("llama2", promptText);
        const assistantMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          text: "",
        };
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
                  return [
                    ...m.slice(0, -1),
                    { ...lastMsg, text: lastMsg.text + chunk.response },
                  ];
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
        const res = await processQuery({
          query: promptText,
          knowledgeSet,
          useMemory,
          useRag,
          history: messages,
        });
        const assistant: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          text: res.text,
          structured: res.structured,
        };
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
                <Brain className="size-5 text-primary" /> Agent Workspace
              </CardTitle>
              <button
                className="text-xs rounded-md border px-2 py-1 hover:bg-accent"
                onClick={() => navigate("/")}
              >
                New session
              </button>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="h-[60vh] md:h-[64vh] overflow-y-auto p-4 space-y-4">
              {messages.length === 0 ? (
                <div className="h-full flex items-center justify-center text-center text-muted-foreground">
                  Ask a question or attach a file to start.
                </div>
              ) : (
                messages.map((m) => (
                  <div
                    key={m.id}
                    className={cn(
                      "flex",
                      m.role === "assistant" ? "justify-start" : "justify-end"
                    )}
                  >
                    <div
                      className={cn(
                        "max-w-[85%] rounded-lg px-4 py-3 shadow",
                        m.role === "assistant"
                          ? "bg-accent/60"
                          : "bg-primary text-primary-foreground"
                      )}
                    >
                      {m.imageUrl && (
                        <img
                          src={m.imageUrl}
                          alt="User upload"
                          className="mb-2 rounded-md max-h-60"
                        />
                      )}
                      {m.fileAttachment && (
                        <div className="mb-2 flex items-center gap-2 rounded-md border bg-background/30 p-2">
                          <File className="size-6 text-foreground/70" />
                          <div className="truncate text-sm">
                            {m.fileAttachment.name}
                          </div>
                        </div>
                      )}
                      <div className="whitespace-pre-wrap">{m.text}</div>
                      {m.structured ? (
                        <div className="mt-3 rounded-md border bg-background p-2 text-foreground">
                          <JsonRenderer data={m.structured} />
                        </div>
                      ) : null}
                    </div>
                  </div>
                ))
              )}
            </div>
            <div className="border-t p-3">
              {attachment && (
                <div className="mb-2 flex items-center justify-between rounded-md border bg-accent/50 p-2 text-sm">
                  <div className="flex items-center gap-2 truncate">
                    <File className="size-4 flex-shrink-0" />
                    <span className="truncate">Attached: {attachment.name}</span>
                  </div>
                  <button
                    onClick={() => setAttachment(null)}
                    className="p-1 rounded-md hover:bg-destructive/20 hover:text-destructive"
                  >
                    <X className="size-4" />
                  </button>
                </div>
              )}
              <div className="flex gap-2">
                <div className="flex-1">
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Type your message..."
                    rows={3}
                    className="w-full h-full resize-none rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        onSubmit();
                      }
                    }}
                  />
                </div>
                <div className="m-0 flex flex-col gap-3 items-center justify-center">
                  <button
                    className="inline-flex items-center gap-1 hover:text-foreground border-4 rounded p-1 hover:bg-blue-950 text-sm"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <Paperclip className="size-4" /> Attach file
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    onChange={handleFileSelect}
                  />
                  <Button
                    disabled={busy}
                    onClick={onSubmit}
                    className="pr-4 pl-4 text-md"
                  >
                    <Send className="mr-2" /> Send
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Database className="size-4" /> Active Context
              </CardTitle>
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
                <div className="text-xs text-muted-foreground mb-1">
                  Knowledge Set
                </div>
                <select
                  value={knowledgeSet}
                  onChange={(e) => setKnowledgeSet(e.target.value)}
                  className="w-full rounded-md border bg-background px-2 py-1.5 text-sm"
                >
                  {[ 
                    "default",
                    ...availableSets.filter((s) => s !== "default"),
                  ].map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  );
}

function ToggleRow({
  label,
  description,
  enabled,
  onToggle,
}: {
  label: string;
  description: string;
  enabled: boolean;
  onToggle: () => void;
}) {
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
