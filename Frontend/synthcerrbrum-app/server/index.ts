import "dotenv/config";
import express from "express";
import cors from "cors";
import { handleDemo } from "./routes/demo";
import fs from "fs";
import fsp from "fs/promises";
import path from "path";
import os from "os";
import { randomUUID } from "crypto";
// using global fetch (Node 18+)

const DATA_ROOT = path.resolve(process.cwd(), ".data");
const CONFIG_PATH = path.join(DATA_ROOT, "config.json");

interface AppConfig {
  modelsDir: string;
  dataDir: string;
  engine: {
    threads: number;
    gpuLayers: number;
    quantization: string;
  };
}

function ensureDirs(cfg: AppConfig) {
  if (!fs.existsSync(DATA_ROOT)) fs.mkdirSync(DATA_ROOT, { recursive: true });
  if (!fs.existsSync(cfg.modelsDir))
    fs.mkdirSync(cfg.modelsDir, { recursive: true });
  if (!fs.existsSync(cfg.dataDir))
    fs.mkdirSync(cfg.dataDir, { recursive: true });
}

function loadConfig(): AppConfig {
  let cfg: AppConfig;
  if (fs.existsSync(CONFIG_PATH)) {
    const raw = fs.readFileSync(CONFIG_PATH, "utf-8");
    cfg = JSON.parse(raw) as AppConfig;
  } else {
    cfg = {
      modelsDir: path.join(DATA_ROOT, "models"),
      dataDir: path.join(DATA_ROOT, "db"),
      engine: {
        threads: Math.max(1, os.cpus()?.length || 4),
        gpuLayers: 0,
        quantization: "auto",
      },
    };
  }
  ensureDirs(cfg);
  return cfg;
}

function saveConfig(cfg: AppConfig) {
  ensureDirs(cfg);
  fs.writeFileSync(CONFIG_PATH, JSON.stringify(cfg, null, 2), "utf-8");
}

export function createServer() {
  const app = express();

  // Middleware
  app.use(cors());
  app.use(express.json({ limit: "25mb" }));
  app.use(express.urlencoded({ extended: true }));
  app.use(express.static(path.resolve(process.cwd(), "public")));

  // Example API routes
  app.get("/api/ping", (_req, res) => {
    const ping = process.env.PING_MESSAGE ?? "ping";
    res.json({ message: ping });
  });

  app.get("/api/demo", handleDemo);

  // Config endpoints
  app.get("/api/config", (_req, res) => {
    res.json(loadConfig());
  });
  app.post("/api/config", async (req, res) => {
    const curr = loadConfig();
    const next: AppConfig = {
      ...curr,
      ...("modelsDir" in req.body ? { modelsDir: req.body.modelsDir } : {}),
      ...("dataDir" in req.body ? { dataDir: req.body.dataDir } : {}),
      engine: { ...curr.engine, ...(req.body.engine || {}) },
    };
    saveConfig(next);
    res.json(next);
  });

  // List local models (simple scan)
  app.get("/api/models/local", async (_req, res) => {
    const cfg = loadConfig();
    const files = await fsp.readdir(cfg.modelsDir).catch(() => []);
    res.json({ models: files });
  });

  // Ollama proxy
  app.get("/api/ollama/tags", async (_req, res) => {
    try {
      const r = await fetch("http://127.0.0.1:11434/api/tags");
      const j = await r.json();
      res.json(j);
    } catch (e: any) {
      res.status(500).json({ error: e?.message || String(e) });
    }
  });

  app.post("/api/ollama/generate", async (req, res) => {
    try {
      const { model, prompt } = req.body || {};
      if (!model || !prompt)
        return res.status(400).json({ error: "model and prompt required" });
      const r = await fetch("http://127.0.0.1:11434/api/generate", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ model, prompt, stream: true }),
      });
      res.setHeader("Content-Type", "application/octet-stream");
      if (r.body) {
        // Convert web ReadableStream to Node.js stream
        const reader = r.body.getReader();
        const { Writable } = require("stream");
        const writable = new Writable({
          write(chunk: any, _encoding: any, callback: any) {
            res.write(chunk);
            callback();
          }
        });
        async function pump() {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            writable.write(value);
          }
          writable.end();
          res.end();
        }
        pump();
      } else {
        res.status(500).json({ error: "No response body" });
      }
    } catch (e: any) {
      res.status(500).json({ error: e?.message || String(e) });
    }
  });

  // Hugging Face download
  app.post("/api/hf/download", async (req, res) => {
    const { repoId, file, dest = "models" } = req.body || {};
    if (!repoId || !file)
      return res.status(400).json({ error: "repoId and file required" });
    const cfg = loadConfig();
    const destDir = dest === "data" ? cfg.dataDir : cfg.modelsDir;
    const url = `https://huggingface.co/${repoId}/resolve/main/${file}`;
    try {
      const resp = await fetch(url);
      if (!resp.ok || !resp.body)
        throw new Error(
          `Failed to download: ${resp.status} ${resp.statusText}`,
        );
      const outPath = path.join(destDir, path.basename(file));
      await fsp.mkdir(path.dirname(outPath), { recursive: true });
      const fileStream = fs.createWriteStream(outPath);
      await new Promise((resolve, reject) => {
        (resp.body as any).pipe(fileStream);
        (resp.body as any).on("error", reject);
        fileStream.on("finish", resolve);
      });
      res.json({ saved: outPath });
    } catch (e: any) {
      res.status(500).json({ error: e?.message || String(e) });
    }
  });

  // Generic URL download
  app.post("/api/models/download-url", async (req, res) => {
    const { url, dest = "models", filename } = req.body || {};
    if (!url) return res.status(400).json({ error: "url required" });
    const cfg = loadConfig();
    const destDir = dest === "data" ? cfg.dataDir : cfg.modelsDir;
    try {
      const resp = await fetch(url);
      if (!resp.ok || !resp.body)
        throw new Error(`Failed: ${resp.status} ${resp.statusText}`);
      const outPath = path.join(
        destDir,
        filename || path.basename(new URL(url).pathname),
      );
      await fsp.mkdir(path.dirname(outPath), { recursive: true });
      const fileStream = fs.createWriteStream(outPath);
      await new Promise((resolve, reject) => {
        (resp.body as any).pipe(fileStream);
        (resp.body as any).on("error", reject);
        fileStream.on("finish", resolve);
      });
      res.json({ saved: outPath });
    } catch (e: any) {
      res.status(500).json({ error: e?.message || String(e) });
    }
  });

  // Data dir file management
  app.get("/api/db/list", async (_req, res) => {
    const cfg = loadConfig();
    const files = await fsp.readdir(cfg.dataDir).catch(() => []);
    res.json({ files });
  });
  app.post("/api/db/uploadFile", async (req, res) => {
    const { name, contentBase64 } = req.body || {};
    if (!name || !contentBase64)
      return res.status(400).json({ error: "name and contentBase64 required" });
    const cfg = loadConfig();
    const outPath = path.join(cfg.dataDir, path.basename(name));
    const buf = Buffer.from(contentBase64, "base64");
    await fsp.writeFile(outPath, buf);
    res.json({ saved: outPath });
  });

  // Sessions persistence (JSON files under DATA_ROOT/sessions)
  app.get("/api/sessions", async (_req, res) => {
    const dir = path.join(DATA_ROOT, "sessions");
    await fsp.mkdir(dir, { recursive: true });
    const files = await fsp.readdir(dir).catch(() => []);
    const sessions = [] as any[];
    for (const f of files) {
      if (!f.endsWith(".json")) continue;
      try {
        const raw = await fsp.readFile(path.join(dir, f), "utf-8");
        const s = JSON.parse(raw);
        sessions.push({
          id: s.id,
          title: s.title,
          createdAt: s.createdAt,
          updatedAt: s.updatedAt,
        });
      } catch {}
    }
    sessions.sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
    res.json({ sessions });
  });
  app.get("/api/sessions/:id", async (req, res) => {
    const dir = path.join(DATA_ROOT, "sessions");
    const file = path.join(dir, `${req.params.id}.json`);
    try {
      const raw = await fsp.readFile(file, "utf-8");
      res.json(JSON.parse(raw));
    } catch {
      res.status(404).json({ error: "not found" });
    }
  });
  app.post("/api/sessions", async (req, res) => {
    const dir = path.join(DATA_ROOT, "sessions");
    await fsp.mkdir(dir, { recursive: true });
    const s = req.body || {};
    const id = s.id || randomUUID();
    const now = Date.now();
    const session = {
      id,
      title: s.title || `Session ${new Date().toLocaleString()}}`,
      messages: s.messages || [],
      createdAt: s.createdAt || now,
      updatedAt: now,
    };
    const file = path.join(dir, `${id}.json`);
    await fsp.writeFile(file, JSON.stringify(session, null, 2), "utf-8");
    res.json(session);
  });
  app.delete("/api/sessions/:id", async (req, res) => {
    const dir = path.join(DATA_ROOT, "sessions");
    const file = path.join(dir, `${req.params.id}.json`);
    try {
      await fsp.unlink(file);
    } catch {}
    res.json({ ok: true });
  });

  // Feedback logging
  app.post("/api/feedback", async (req, res) => {
    const { sessionId, messageId, rating, note } = req.body || {};
    if (!sessionId || !messageId || !rating)
      return res
        .status(400)
        .json({ error: "sessionId, messageId, rating required" });
    const file = path.join(DATA_ROOT, "feedback.json");
    let arr: any[] = [];
    if (fs.existsSync(file)) {
      try {
        arr = JSON.parse(await fsp.readFile(file, "utf-8"));
      } catch {}
    }
    const entry = {
      id: randomUUID(),
      sessionId,
      messageId,
      rating,
      note,
      ts: Date.now(),
    };
    arr.push(entry);
    await fsp.writeFile(file, JSON.stringify(arr, null, 2), "utf-8");
    res.json(entry);
  });

  return app;
}
