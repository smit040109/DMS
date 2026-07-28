import React, { useState } from "react";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import AiAssistant from "@/components/ai/AiAssistant";

export default function AppShell({ children }) {
  const [collapsed, setCollapsed] = useState(false);
  const [aiOpen, setAiOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-canvas" data-testid="app-shell">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar onOpenAi={() => setAiOpen(true)} />
        <main className="flex-1 p-6 md:p-8 max-w-[1600px] w-full mx-auto">{children}</main>
      </div>
      <AiAssistant open={aiOpen} onOpenChange={setAiOpen} />
    </div>
  );
}
