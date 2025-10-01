import "./global.css";

import { Toaster } from "@/components/ui/toaster";
import { createRoot } from "react-dom/client";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import AgentWorkspace from "./pages/AgentWorkspace";
import RAGManager from "./pages/RAGManager";
import EngineControl from "./pages/EngineControl";
import LearningFeedback from "./pages/LearningFeedback";
import UserSettings from "./pages/UserSettings";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AgentWorkspace />} />
          <Route path="/session/:id" element={<AgentWorkspace />} />
          <Route path="/rag" element={<RAGManager />} />
          <Route path="/engine" element={<EngineControl />} />
          <Route path="/feedback" element={<LearningFeedback />} />
          <Route path="/settings" element={<UserSettings />} />
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

createRoot(document.getElementById("root")!).render(<App />);
