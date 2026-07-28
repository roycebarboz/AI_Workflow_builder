import { useState } from "react";
import { Chat } from "./components/Chat";
import { WorkflowForm } from "./components/WorkflowForm";
import { WorkflowsList } from "./components/WorkflowsList";
import type { Workflow } from "./types";
import "./App.css";

type View =
  | { name: "list" }
  | { name: "form"; workflow: Workflow | null }
  | { name: "chat"; workflow: Workflow };

function App() {
  const [view, setView] = useState<View>({ name: "list" });
  const [refreshKey, setRefreshKey] = useState(0);

  if (view.name === "form") {
    return (
      <WorkflowForm
        workflow={view.workflow}
        onCancel={() => setView({ name: "list" })}
        onSaved={() => {
          setRefreshKey((k) => k + 1);
          setView({ name: "list" });
        }}
      />
    );
  }

  if (view.name === "chat") {
    return (
      <div className="app">
        <Chat
          workflowId={view.workflow.id}
          workflowName={view.workflow.name}
          onBack={() => setView({ name: "list" })}
        />
      </div>
    );
  }

  return (
    <WorkflowsList
      refreshKey={refreshKey}
      onNew={() => setView({ name: "form", workflow: null })}
      onEdit={(workflow) => setView({ name: "form", workflow })}
      onChat={(workflow) => setView({ name: "chat", workflow })}
    />
  );
}

export default App;
