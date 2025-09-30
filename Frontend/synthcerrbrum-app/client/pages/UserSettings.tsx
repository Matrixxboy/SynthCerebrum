import { Layout } from "@/components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Sun, Moon, MonitorCog } from "lucide-react";
import { useEffect, useState } from "react";

function applyTheme(mode: 'light'|'dark'|'system'){
  const root = document.documentElement;
  if (mode === 'system'){
    const mql = window.matchMedia('(prefers-color-scheme: dark)');
    const set = () => { root.classList.toggle('dark', mql.matches); };
    set();
    return;
  }
  root.classList.toggle('dark', mode === 'dark');
}

export default function UserSettings(){
  const [theme, setTheme] = useState<'light'|'dark'|'system'>(() => (localStorage.getItem('theme') as any) || 'system');
  useEffect(()=>{ applyTheme(theme); localStorage.setItem('theme', theme); }, [theme]);

  return (
    <Layout>
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base"><MonitorCog className="size-4"/> User Preferences</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div>
              <div className="text-xs text-muted-foreground mb-1">Theme</div>
              <div className="flex gap-2">
                <button onClick={()=>setTheme('light')} className={`rounded-md border px-2 py-1 inline-flex items-center gap-1 ${theme==='light'?'bg-accent':''}`}><Sun className="size-4"/> Light</button>
                <button onClick={()=>setTheme('dark')} className={`rounded-md border px-2 py-1 inline-flex items-center gap-1 ${theme==='dark'?'bg-accent':''}`}><Moon className="size-4"/> Dark</button>
                <button onClick={()=>setTheme('system')} className={`rounded-md border px-2 py-1 inline-flex items-center gap-1 ${theme==='system'?'bg-accent':''}`}><MonitorCog className="size-4"/> System</button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
