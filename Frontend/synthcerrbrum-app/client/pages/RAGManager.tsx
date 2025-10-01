import React from "react";
import { Layout } from "@/components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useEffect, useRef, useState } from "react";
import { ingestFiles, IngestionJob, IngestionOptions } from "@/lib/ingestion";
import {
  listKnowledgeSets,
  createKnowledgeSet,
  deleteKnowledgeSet,
  countItems,
} from "@/lib/vectorStore";
import { Database, UploadCloud, LibrarySquare } from "lucide-react";
import { getConfig, setConfig, dbUploadFile, dbList } from "@/lib/api";

function KnowledgeSetCard({
  name,
  refreshKey,
}: {
  name: string;
  refreshKey: any;
}) {
  console.log(`KnowledgeSetCard: rendering ${name}`);
  const [count, setCount] = useState(0);

  useEffect(() => {
    async function load() {
      setCount(await countItems(name));
    }
    load();
  }, [name, refreshKey]);

  return (
    <div className="rounded-md border p-3">
      <div className="font-medium">{name}</div>
      <div className="text-xs text-muted-foreground">Items: {count}</div>
    </div>
  );
}

export default function RAGManager() {
  const [jobs, setJobs] = useState<IngestionJob[]>([]);
  const [knowledgeSet, setKnowledgeSet] = useState("default");
  const [availableSets, setAvailableSets] = useState<string[]>([]);
  const [chunkSize, setChunkSize] = useState(800);
  const [embedImages, setEmbedImages] = useState(true);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const uploadRef = useRef<HTMLInputElement | null>(null);
  const [cfg, setCfg] = useState<any>(null);
  const [serverFiles, setServerFiles] = useState<string[]>([]);
  const [refreshCounter, setRefreshCounter] = useState(0);

  useEffect(() => {
    console.log("RAGManager: useEffect");
    async function load() {
      setAvailableSets(await listKnowledgeSets());
      const c = await getConfig();
      setCfg(c);
      const l = await dbList();
      setServerFiles(l.files || []);
    }
    load();
  }, []);

  const handleFiles = async (files: FileList) => {
    console.log("RAGManager: handleFiles");
    const fileArray = Array.from(files);
    const opts: IngestionOptions = { knowledgeSet, chunkSize, embedImages };
    for await (const job of ingestFiles(fileArray, opts)) {
      setJobs((prev) => {
        const next = prev.filter((j) => j.id !== job.id);
        next.unshift(job);
        return next.slice(0, 50);
      });
      if (job.status === "stored") {
        setRefreshCounter((prev) => prev + 1);
      }
    }
  };

  const onCreateSet = async () => {
    console.log("RAGManager: onCreateSet");
    const name = prompt("New knowledge set name");
    if (!name) return;
    await createKnowledgeSet(name);
    setAvailableSets(await listKnowledgeSets());
    setKnowledgeSet(name);
  };

  const onDeleteSet = async () => {
    console.log("RAGManager: onDeleteSet");
    if (knowledgeSet === "default") return alert("Cannot delete default set");
    if (!confirm(`Delete knowledge set "${knowledgeSet}"?`)) return;
    await deleteKnowledgeSet(knowledgeSet);
    setAvailableSets(await listKnowledgeSets());
    setKnowledgeSet("default");
  };

  async function saveDataDir() {
    if (!cfg?.dataDir) return;
    const saved = await setConfig({ dataDir: cfg.dataDir });
    setCfg(saved);
  }

  async function onUploadToDataDir(files: FileList) {
    for (const f of Array.from(files)) {
      const buf = await f.arrayBuffer();
      await dbUploadFile(f.name, buf);
    }
    const l = await dbList();
    setServerFiles(l.files || []);
  }

  return (
    <>
      <Layout>
        <div className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <UploadCloud className="size-4" /> Data Sources Ingestion
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <div className="text-xs text-muted-foreground mb-1">
                  Knowledge Set
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={knowledgeSet}
                    onChange={(e) => setKnowledgeSet(e.target.value)}
                    className="rounded-md border bg-background px-2 py-1.5 text-sm"
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
                  <button
                    onClick={onCreateSet}
                    className="text-xs rounded-md border px-2 py-1 hover:bg-accent"
                  >
                    Create
                  </button>
                  <button
                    onClick={onDeleteSet}
                    className="text-xs rounded-md border px-2 py-1 hover:bg-accent"
                  >
                    Delete
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <label className="text-xs text-muted-foreground">
                  Chunk size
                  <input
                    type="number"
                    value={chunkSize}
                    onChange={(e) =>
                      setChunkSize(parseInt(e.target.value || "800"))
                    }
                    className="mt-1 w-full rounded-md border bg-background px-2 py-1.5 text-sm"
                  />
                </label>
                <label className="text-xs text-muted-foreground">
                  Embed images
                  <select
                    value={String(embedImages)}
                    onChange={(e) => setEmbedImages(e.target.value === "true")}
                    className="mt-1 w-full rounded-md border bg-background px-2 py-1.5 text-sm"
                  >
                    <option value="true">Yes</option>
                    <option value="false">No</option>
                  </select>
                </label>
              </div>
              <div className="rounded-md border border-dashed p-6 text-center">
                <div className="flex justify-center mb-2">
                  <LibrarySquare className="size-6 text-muted-foreground" />
                </div>
                <div className="text-sm mb-2">
                  Drop files here or{" "}
                  <button
                    onClick={() => inputRef.current?.click()}
                    className="underline"
                  >
                    browse
                  </button>
                </div>
                <input
                  ref={inputRef}
                  type="file"
                  multiple
                  className="hidden"
                  onChange={(e) =>
                    e.target.files && handleFiles(e.target.files)
                  }
                />
                <div className="text-xs text-muted-foreground">
                  PDF, DOCX, TXT, CSV, JSON, PNG, JPG, and more.
                </div>
              </div>
              <div className="rounded-md border p-4">
                <div className="text-sm font-medium mb-2">Data directory</div>
                <div className="flex items-center gap-2 mb-2">
                  <input
                    value={cfg?.dataDir || ""}
                    onChange={(e) =>
                      setCfg((p: any) => ({ ...p, dataDir: e.target.value }))
                    }
                    className="flex-1 rounded-md border bg-background px-2 py-1.5 text-sm"
                  />
                  <button
                    onClick={saveDataDir}
                    className="text-xs rounded-md border px-2 py-1 hover:bg-accent"
                  >
                    Save
                  </button>
                </div>
                <div className="text-xs text-muted-foreground mb-1">
                  Upload files into data directory
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => uploadRef.current?.click()}
                    className="text-xs rounded-md border px-2 py-1 hover:bg-accent"
                  >
                    Add files
                  </button>
                  <input
                    ref={uploadRef}
                    type="file"
                    multiple
                    className="hidden"
                    onChange={(e) =>
                      e.target.files && onUploadToDataDir(e.target.files)
                    }
                  />
                </div>
                <div className="text-xs mt-2">
                  Server files: {serverFiles.length ? "" : "none"}
                </div>
                {serverFiles.length ? (
                  <ul className="mt-1 max-h-24 overflow-auto text-xs list-disc pl-4">
                    {serverFiles.map((f) => (
                      <li key={f} className="truncate" title={f}>
                        {f}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">
                  Ingestion Queue
                </div>
                <ul className="space-y-2 text-sm max-h-56 overflow-auto">
                  {jobs.length === 0 ? (
                    <li className="text-muted-foreground">No items</li>
                  ) : (
                    jobs.map((j) => (
                      <li key={j.id} className="flex items-center gap-2">
                        <span className="truncate" title={j.name}>
                          {j.name}
                        </span>
                        <span className="ml-auto rounded bg-muted px-1.5 py-0.5 text-[10px]">
                          {j.status}
                        </span>
                      </li>
                    ))
                  )}
                </ul>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Database className="size-4" /> Vector Store
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 gap-3 text-sm">
                {availableSets.map((s) => (
                  <KnowledgeSetCard
                    key={s}
                    name={s}
                    refreshKey={refreshCounter}
                  />
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </Layout>
    </>
  );
}
