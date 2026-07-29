import { useState } from "react";
import { Chat } from "./components/Chat";
import { ExecutionHistory } from "./components/ExecutionHistory";
import { WorkflowEditor } from "./components/WorkflowEditor";
import { WorkflowsList } from "./components/WorkflowsList";
import type { Workflow } from "./types";
import "./App.css";

type View =
  | { name: "list" }
  | { name: "editor"; workflow: Workflow | null }
  | { name: "chat"; workflow: Workflow }
  | { name: "history"; workflow: Workflow };

function App() {
  const [view, setView] = useState<View>({ name: "list" });
  const [refreshKey, setRefreshKey] = useState(0);

  if (view.name === "editor") {
    return (
      <WorkflowEditor
        workflow={view.workflow}
        onBack={() => {
          setRefreshKey((k) => k + 1);
          setView({ name: "list" });
        }}
        onSaved={() => setRefreshKey((k) => k + 1)}
      />
    );
  }

  if (view.name === "chat") {
    return (
      <div className="app">
        <Chat
          workflowId={view.workflow.id}
          workflowVersionId={view.workflow.current_version_id}
          workflowName={view.workflow.name}
          onBack={() => setView({ name: "list" })}
        />
      </div>
    );
  }

  if (view.name === "history") {
    return (
      <ExecutionHistory
        workflowId={view.workflow.id}
        workflowName={view.workflow.name}
        onBack={() => setView({ name: "list" })}
      />
    );
  }

  return (
    <WorkflowsList
      refreshKey={refreshKey}
      onNew={() => setView({ name: "editor", workflow: null })}
      onEdit={(workflow) => setView({ name: "editor", workflow })}
      onChat={(workflow) => setView({ name: "chat", workflow })}
      onHistory={(workflow) => setView({ name: "history", workflow })}
    />
  );
}

export default App;
