import { useEffect, useMemo, useState, type ReactNode } from "react";
import ReactFlow, {
  Controls,
  ReactFlowProvider,
  type Edge,
  useNodesState,
} from "reactflow";
import "reactflow/dist/style.css";
import { createWorkflow, listTools, updateWorkflow } from "../api/workflows";
import {
  AGENT_NODE_ID,
  END_NODE_ID,
  START_NODE_ID,
  agentDataOf,
  defaultGraph,
} from "../lib/defaultGraph";
import type { GraphNodeType, ToolInfo, Workflow } from "../types";
import { nodeTypes } from "./canvas/GraphNodes";
import {
  AgentIcon,
  BackIcon,
  CloseIcon,
  ConditionIcon,
  EditIcon,
  EmptyPanelIcon,
  EndIcon,
  RunIcon,
  StartIcon,
  toolIcon,
} from "./canvas/icons";
import { RunPanel } from "./canvas/RunPanel";
import "./WorkflowEditor.css";

interface WorkflowEditorProps {
  workflow: Workflow | null;
  onBack: () => void;
  onSaved: () => void;
}

function PanelShell({
  title,
  desc,
  onClose,
  children,
}: {
  title: string;
  desc: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <div className="panel-content">
      <div className="panel-head">
        <div>
          <div className="panel-head-title">{title}</div>
          <div className="panel-head-desc">{desc}</div>
        </div>
        <button type="button" className="panel-close" onClick={onClose} aria-label="Close">
          <CloseIcon />
        </button>
      </div>
      <div className="panel-content-inner">{children}</div>
    </div>
  );
}

export function WorkflowEditor({ workflow, onBack, onSaved }: WorkflowEditorProps) {
  const initialGraph = useMemo(
    () => (workflow?.graph?.nodes?.length ? workflow.graph : defaultGraph()),
    [workflow]
  );

  const [nodes, , onNodesChange] = useNodesState(
    initialGraph.nodes.map((n) => ({
      id: n.id,
      type: n.type,
      position: n.position,
      data: {},
    }))
  );
  const [edges] = useState<Edge[]>(
    initialGraph.edges.map((e) => ({ ...e, type: "smoothstep" }))
  );

  const initialAgentData = useMemo(() => agentDataOf(initialGraph), [initialGraph]);
  const [name, setName] = useState(workflow?.name ?? "");
  const [systemPrompt, setSystemPrompt] = useState(initialAgentData.system_prompt);
  const [enabledTools, setEnabledTools] = useState<Set<string>>(
    new Set(initialAgentData.enabled_tools)
  );
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [mode, setMode] = useState<"edit" | "run">("edit");
  const [currentWorkflow, setCurrentWorkflow] = useState(workflow);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listTools()
      .then(setTools)
      .catch((err) => setError((err as Error).message));
  }, []);

  function toggleTool(toolName: string) {
    setEnabledTools((prev) => {
      const next = new Set(prev);
      if (next.has(toolName)) next.delete(toolName);
      else next.add(toolName);
      return next;
    });
  }

  async function handleSave(): Promise<Workflow | null> {
    if (!name.trim()) {
      setError("Name is required before saving.");
      return null;
    }
    setIsSaving(true);
    setError(null);
    try {
      const input = {
        name: name.trim(),
        graph: {
          nodes: nodes.map((n) => ({
            id: n.id,
            type: n.type as GraphNodeType,
            position: n.position,
            data:
              n.id === AGENT_NODE_ID
                ? { system_prompt: systemPrompt, enabled_tools: Array.from(enabledTools) }
                : {},
          })),
          edges: edges.map((e) => ({ id: e.id, source: e.source, target: e.target })),
        },
      };
      const saved = currentWorkflow
        ? await updateWorkflow(currentWorkflow.id, input)
        : await createWorkflow(input);
      setCurrentWorkflow(saved);
      onSaved();
      return saved;
    } catch (err) {
      setError((err as Error).message);
      return null;
    } finally {
      setIsSaving(false);
    }
  }

  async function handleModeChange(next: "edit" | "run") {
    if (next === "run") {
      const saved = await handleSave();
      if (!saved) return;
    }
    setMode(next);
  }

  const nodesWithSelection = nodes.map((n) => ({ ...n, selected: n.id === selectedNodeId }));

  return (
    <div className="editor-app">
      <div className="topbar">
        <button type="button" className="icon-btn" aria-label="Back" onClick={onBack}>
          <BackIcon />
        </button>
        <input
          className="topbar-title-input"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Untitled workflow"
        />
        <div className="topbar-spacer" />
        {error && <span className="topbar-error">{error}</span>}
        <button
          type="button"
          className="btn-secondary save-btn"
          onClick={() => void handleSave()}
          disabled={isSaving || !name.trim()}
        >
          {isSaving ? "Saving…" : "Save"}
        </button>
        <div className="mode-pill">
          <button
            type="button"
            className={`edit-label${mode === "edit" ? " active" : ""}`}
            onClick={() => setMode("edit")}
            title="Edit"
          >
            <EditIcon />
          </button>
          <button
            type="button"
            className={`run-label${mode === "run" ? " active" : ""}`}
            onClick={() => void handleModeChange("run")}
            title="Run"
          >
            <RunIcon />
            Run
          </button>
        </div>
      </div>

      <div className="main">
        <div className="sidebar">
          <h4>Nodes</h4>
          <div className="palette-item">
            <span className="pal-icon start">
              <StartIcon />
            </span>
            Start
          </div>
          <div className="palette-item">
            <span className="pal-icon agent">
              <AgentIcon />
            </span>
            Agent
          </div>
          <div className="palette-item disabled" title="Coming soon">
            <span className="pal-icon cond">
              <ConditionIcon />
            </span>
            Condition
          </div>
          <div className="palette-item">
            <span className="pal-icon end">
              <EndIcon />
            </span>
            End
          </div>
        </div>

        <div className="canvas-wrap">
          {mode === "run" && <div className="run-dim" />}
          <ReactFlowProvider>
            <ReactFlow
              nodes={nodesWithSelection}
              edges={edges}
              nodeTypes={nodeTypes}
              onNodesChange={onNodesChange}
              onNodeClick={(_, node) => mode === "edit" && setSelectedNodeId(node.id)}
              onPaneClick={() => setSelectedNodeId(null)}
              nodesDraggable={mode === "edit"}
              nodesConnectable={false}
              elementsSelectable={mode === "edit"}
              fitView
              proOptions={{ hideAttribution: true }}
              defaultEdgeOptions={{ style: { stroke: "#3a3a42", strokeWidth: 1.6 } }}
            >
              <Controls showInteractive={false} />
            </ReactFlow>
          </ReactFlowProvider>
        </div>

        {mode === "edit" ? (
          <div className="panel">
            {selectedNodeId === null && (
              <div className="panel-empty">
                <EmptyPanelIcon />
                <b>No node selected</b>
                <span>Click any node on the canvas to view and edit its configuration here.</span>
              </div>
            )}

            {selectedNodeId === START_NODE_ID && (
              <PanelShell
                title="Start"
                desc="Entry point for the workflow."
                onClose={() => setSelectedNodeId(null)}
              >
                <p className="info-note">
                  A run begins when the user sends a message in chat with this workflow.
                  There's nothing to configure here.
                </p>
              </PanelShell>
            )}

            {selectedNodeId === AGENT_NODE_ID && (
              <PanelShell
                title="Agent"
                desc="System prompt and tools. The agent decides which enabled tools to call, looping until it produces a final answer."
                onClose={() => setSelectedNodeId(null)}
              >
                <div className="field">
                  <div className="field-label">System prompt</div>
                  <textarea
                    className="ta"
                    value={systemPrompt}
                    onChange={(e) => setSystemPrompt(e.target.value)}
                    placeholder="You are a helpful assistant that..."
                  />
                </div>
                <div className="field">
                  <div className="field-label">Tools</div>
                  <div className="tool-list">
                    {tools.map((tool) => (
                      <div className="tool-row" key={tool.name}>
                        <span className="tool-row-icon">{toolIcon(tool.name)}</span>
                        <div className="tool-row-text">
                          <div className="tool-row-name">{tool.name}</div>
                          <div className="tool-row-desc">{tool.description}</div>
                        </div>
                        <label className="switch">
                          <input
                            type="checkbox"
                            checked={enabledTools.has(tool.name)}
                            onChange={() => toggleTool(tool.name)}
                          />
                          <span className="track">
                            <span className="thumb" />
                          </span>
                        </label>
                      </div>
                    ))}
                  </div>
                </div>
              </PanelShell>
            )}

            {selectedNodeId === END_NODE_ID && (
              <PanelShell
                title="End"
                desc="Terminal node."
                onClose={() => setSelectedNodeId(null)}
              >
                <p className="info-note">
                  When this path is reached, the run finishes and the agent's last message
                  becomes the final response shown in chat.
                </p>
              </PanelShell>
            )}
          </div>
        ) : (
          currentWorkflow && <RunPanel key={currentWorkflow.id} workflowId={currentWorkflow.id} />
        )}
      </div>
    </div>
  );
}
