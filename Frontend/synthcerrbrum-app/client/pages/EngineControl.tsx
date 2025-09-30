import { Layout } from "@/components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Cpu, Layers } from "lucide-react";
import { useEffect, useState } from "react";
import { getConfig, setConfig, listLocalModels, getOllamaTags, pullOllamaModel, hfDownload, downloadFromUrl } from "@/lib/api";

export default function EngineControl(){
  const [cfg, setCfg] = useState<any>(null);
  const [models, setModels] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [ollamaName, setOllamaName] = useState("");
  const [hfRepo, setHfRepo] = useState("");
  const [hfFile, setHfFile] = useState("");
  const [url, setUrl] = useState("");

  useEffect(()=>{ refresh(); },[]);

  async function refresh(){
    const c = await getConfig();
    setCfg(c);
    const m = await listLocalModels();
    setModels(m.models || []);
  }

  async function saveCfg(next: any){
    setSaving(true);
    try {
      const saved = await setConfig(next);
      setCfg(saved);
    } finally { setSaving(false); }
  }

  return (
    <Layout>
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base"><Layers className="size-4"/> Model Library & Downloads</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div>
              <div className="text-xs text-muted-foreground mb-1">Models directory</div>
              <div className="flex items-center gap-2">
                <input value={cfg?.modelsDir||''} onChange={(e)=>setCfg((p:any)=>({...p, modelsDir:e.target.value}))} className="flex-1 rounded-md border bg-background px-2 py-1.5"/>
                <button disabled={saving} onClick={()=>saveCfg({ modelsDir: cfg.modelsDir })} className="rounded-md border px-2 py-1 hover:bg-accent">Save</button>
              </div>
            </div>
            <div>
              <div className="font-medium">Local Models</div>
              <ul className="mt-1 grid grid-cols-2 gap-2">
                {models.length? models.map((m)=> <li key={m} className="rounded border p-2 truncate" title={m}>{m}</li>): <li className="text-muted-foreground">No models found</li>}
              </ul>
              <button onClick={refresh} className="mt-2 text-xs underline">Refresh</button>
            </div>
            <div className="grid gap-3">
              <label className="text-xs text-muted-foreground">Pull from Ollama
                <div className="mt-1 flex gap-2">
                  <input value={ollamaName} onChange={(e)=>setOllamaName(e.target.value)} placeholder="e.g. mistral:7b" className="flex-1 rounded-md border bg-background px-2 py-1.5"/>
                  <button onClick={async()=>{ if(!ollamaName) return; await pullOllamaModel(ollamaName); setOllamaName(""); }} className="rounded-md border px-2 py-1 hover:bg-accent">Pull</button>
                </div>
              </label>
              <label className="text-xs text-muted-foreground">Download from Hugging Face
                <div className="mt-1 grid grid-cols-2 gap-2">
                  <input value={hfRepo} onChange={(e)=>setHfRepo(e.target.value)} placeholder="repoId, e.g. TheBloke/Mistral-7B-GGUF" className="rounded-md border bg-background px-2 py-1.5"/>
                  <input value={hfFile} onChange={(e)=>setHfFile(e.target.value)} placeholder="file path, e.g. mistral.Q4_K_M.gguf" className="rounded-md border bg-background px-2 py-1.5"/>
                </div>
                <button onClick={async()=>{ if(!hfRepo||!hfFile) return; await hfDownload(hfRepo, hfFile, 'models'); setHfRepo(''); setHfFile(''); }} className="mt-2 rounded-md border px-2 py-1 hover:bg-accent">Download</button>
              </label>
              <label className="text-xs text-muted-foreground">Download by URL
                <div className="mt-1 flex gap-2">
                  <input value={url} onChange={(e)=>setUrl(e.target.value)} placeholder="https://.../model.gguf" className="flex-1 rounded-md border bg-background px-2 py-1.5"/>
                  <button onClick={async()=>{ if(!url) return; await downloadFromUrl(url, 'models'); setUrl(''); }} className="rounded-md border px-2 py-1 hover:bg-accent">Download</button>
                </div>
              </label>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base"><Cpu className="size-4"/> Core Engine & Database</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="grid grid-cols-3 gap-2">
              <label className="text-xs text-muted-foreground">Threads
                <input type="number" value={cfg?.engine?.threads||1} onChange={(e)=>setCfg((p:any)=>({ ...p, engine:{...p.engine, threads: parseInt(e.target.value||'1')}}))} className="mt-1 w-full rounded-md border bg-background px-2 py-1.5"/>
              </label>
              <label className="text-xs text-muted-foreground">GPU Layers
                <input type="number" value={cfg?.engine?.gpuLayers||0} onChange={(e)=>setCfg((p:any)=>({ ...p, engine:{...p.engine, gpuLayers: parseInt(e.target.value||'0')}}))} className="mt-1 w-full rounded-md border bg-background px-2 py-1.5"/>
              </label>
              <label className="text-xs text-muted-foreground">Quantization
                <select value={cfg?.engine?.quantization||'auto'} onChange={(e)=>setCfg((p:any)=>({ ...p, engine:{...p.engine, quantization: e.target.value}}))} className="mt-1 w-full rounded-md border bg-background px-2 py-1.5">
                  <option value="auto">auto</option>
                  <option value="Q2">Q2</option>
                  <option value="Q4">Q4</option>
                  <option value="Q5">Q5</option>
                  <option value="Q8">Q8</option>
                </select>
              </label>
            </div>
            <button disabled={saving} onClick={()=>saveCfg({ engine: cfg.engine })} className="rounded-md border px-2 py-1 hover:bg-accent">Save engine</button>
            <div>
              <div className="text-xs text-muted-foreground mb-1">Data directory (knowledge base root)</div>
              <div className="flex items-center gap-2">
                <input value={cfg?.dataDir||''} onChange={(e)=>setCfg((p:any)=>({...p, dataDir:e.target.value}))} className="flex-1 rounded-md border bg-background px-2 py-1.5"/>
                <button disabled={saving} onClick={()=>saveCfg({ dataDir: cfg.dataDir })} className="rounded-md border px-2 py-1 hover:bg-accent">Save</button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
