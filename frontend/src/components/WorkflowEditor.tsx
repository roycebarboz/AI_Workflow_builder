import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent, type ReactNode } from "react";
import ReactFlow, {
  addEdge,
  Controls,
  reconnectEdge,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type ReactFlowInstance,
} from "reactflow";
import "reactflow/dist/style.css";
import { createWorkflow, listTools, updateWorkflow } from "../api/workflows";
import {
  AGENT_NODE_ID,
  END_NODE_ID,
  START_NODE_ID,
  agentDataOf,
  defaultDataFor,
  defaultGraph,
  newNodeId,
} from "../lib/defaultGraph";
import type { GraphNode, GraphNodeType, ToolInfo, Workflow } from "../types";
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

function stringField(data: Record<string, unknown>, key: string): string {
  return typeof data[key] === "string" ? (data[key] as string) : "";
}

function initialNodeData(node: GraphNode): Record<string, unknown> {
  if (node.type === "condition") {
    return { keyword: stringField(node.data, "keyword") };
  }
  if (node.type === "end") {
    return { message: stringField(node.data, "message") };
  }
  return {};
}

function PanelShell({
  title,
  desc,
  onClose,
  onDelete,
  children,
}: {
  title: string;
  desc: string;
  onClose: () => void;
  onDelete?: () => void;
  children: ReactNode;
}) {
  return (
    <div className="panel-content">
      <div className="panel-head">
        <div>
          <div className="panel-head-title">{title}</div>
          <div className="panel-head-desc">{desc}</div>
        </div>
        <div className="panel-head-actions">
          {onDelete && (
            <button type="button" className="panel-delete" onClick={onDelete}>
              Delete
            </button>
          )}
          <button type="button" className="panel-close" onClick={onClose} aria-label="Close">
            <CloseIcon />
          </button>
        </div>
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

  const [nodes, setNodes, onNodesChange] = useNodesState(
    initialGraph.nodes.map((n) => ({
      id: n.id,
      type: n.type,
      position: n.position,
      data: initialNodeData(n),
      deletable: n.id !== START_NODE_ID && n.id !== AGENT_NODE_ID && n.id !== END_NODE_ID,
    }))
  );
  const [edges, setEdges, onEdgesChange] = useEdgesState(
    initialGraph.edges.map((e) => ({ ...e, type: "smoothstep" }))
  );
  const rfInstance = useRef<ReactFlowInstance | null>(null);

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

  function updateNodeData(nodeId: string, patch: Record<string, unknown>) {
    setNodes((nds) => nds.map((n) => (n.id === nodeId ? { ...n, data: { ...n.data, ...patch } } : n)));
  }

  function deleteNode(nodeId: string) {
    setNodes((nds) => nds.filter((n) => n.id !== nodeId));
    setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
    setSelectedNodeId(null);
  }

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => addEdge({ ...connection, type: "smoothstep" }, eds));
    },
    [setEdges]
  );

  // While an existing edge's endpoint is being dragged, its own (still-current) wiring
  // must not count against the "source already has an outgoing edge" validity rule below —
  // otherwise every reconnect target would be rejected, including valid ones.
  const reconnectingEdgeId = useRef<string | null>(null);

  const onReconnectStart = useCallback((_event: unknown, edge: Edge) => {
    reconnectingEdgeId.current = edge.id;
  }, []);

  const onReconnectEnd = useCallback(() => {
    reconnectingEdgeId.current = null;
  }, []);

  const onReconnect = useCallback(
    (oldEdge: Edge, newConnection: Connection) => {
      setEdges((eds) => reconnectEdge(oldEdge, newConnection, eds));
    },
    [setEdges]
  );

  const isValidConnection = useCallback(
    (connection: Connection | Edge) => {
      const { source, target, sourceHandle } = connection;
      if (!source || !target || source === target) return false;
      const sourceNode = nodes.find((n) => n.id === source);
      const targetNode = nodes.find((n) => n.id === target);
      if (!sourceNode || !targetNode) return false;
      if (sourceNode.type === "agent" && targetNode.type !== "end") return false;
      if (sourceNode.type === "start" && targetNode.type === "end") return false;
      const handleKey = sourceHandle ?? null;
      const alreadyWired = edges.some(
        (e) =>
          e.id !== reconnectingEdgeId.current &&
          e.source === source &&
          (e.sourceHandle ?? null) === handleKey
      );
      return !alreadyWired;
    },
    [nodes, edges]
  );

  const onDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      const type = event.dataTransfer.getData("application/reactflow") as GraphNodeType | "";
      if (!type || !rfInstance.current) return;
      const position = rfInstance.current.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });
      const id = newNodeId(type);
      setNodes((nds) => [
        ...nds,
        { id, type, position, data: defaultDataFor(type), deletable: true },
      ]);
      setSelectedNodeId(id);
    },
    [setNodes]
  );

  function onPaletteDragStart(event: DragEvent<HTMLDivElement>, type: GraphNodeType) {
    event.dataTransfer.setData("application/reactflow", type);
    event.dataTransfer.effectAllowed = "move";
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
          nodes: nodes.map((n) => {
            let data: Record<string, unknown> = {};
            if (n.id === AGENT_NODE_ID) {
              data = { system_prompt: systemPrompt, enabled_tools: Array.from(enabledTools) };
            } else if (n.type === "condition") {
              data = { keyword: stringField(n.data, "keyword") };
            } else if (n.type === "end") {
              const message = stringField(n.data, "message").trim();
              data = message ? { message } : {};
            }
            return {
              id: n.id,
              type: n.type as GraphNodeType,
              position: n.position,
              data,
            };
          }),
          edges: edges.map((e) => ({
            id: e.id,
            source: e.source,
            target: e.target,
            ...(e.sourceHandle ? { sourceHandle: e.sourceHandle } : {}),
          })),
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
  const selectedNode = nodes.find((n) => n.id === selectedNodeId) ?? null;

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
          <div
            className="palette-item draggable"
            draggable
            onDragStart={(e) => onPaletteDragStart(e, "condition")}
            title="Drag onto the canvas"
          >
            <span className="pal-icon cond">
              <ConditionIcon />
            </span>
            Condition
          </div>
          <div
            className="palette-item draggable"
            draggable
            onDragStart={(e) => onPaletteDragStart(e, "end")}
            title="Drag onto the canvas"
          >
            <span className="pal-icon end">
              <EndIcon />
            </span>
            End
          </div>
        </div>

        <div className="canvas-wrap" onDragOver={onDragOver} onDrop={onDrop}>
          {mode === "run" && <div className="run-dim" />}
          <ReactFlowProvider>
            <ReactFlow
              nodes={nodesWithSelection}
              edges={edges}
              nodeTypes={nodeTypes}
              onInit={(instance) => (rfInstance.current = instance)}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onReconnect={onReconnect}
              onReconnectStart={onReconnectStart}
              onReconnectEnd={onReconnectEnd}
              isValidConnection={isValidConnection}
              onNodeClick={(_, node) => mode === "edit" && setSelectedNodeId(node.id)}
              onPaneClick={() => setSelectedNodeId(null)}
              nodesDraggable={mode === "edit"}
              nodesConnectable={mode === "edit"}
              elementsSelectable={mode === "edit"}
              edgesUpdatable={mode === "edit"}
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

            {selectedNode?.type === "condition" && (
              <PanelShell
                title="Condition"
                desc="Checks the user's latest message for a keyword and routes down the True or False branch accordingly."
                onClose={() => setSelectedNodeId(null)}
                onDelete={() => deleteNode(selectedNode.id)}
              >
                <div className="field">
                  <div className="field-label">Keyword to match</div>
                  <input
                    className="text-input"
                    value={stringField(selectedNode.data, "keyword")}
                    onChange={(e) => updateNodeData(selectedNode.id, { keyword: e.target.value })}
                    placeholder="e.g. urgent"
                  />
                </div>
                <p className="info-note">
                  Wire the <b>True</b> handle to where matching messages should go, and{" "}
                  <b>False</b> to where everything else should go.
                </p>
              </PanelShell>
            )}

            {selectedNode?.type === "end" && (
              <PanelShell
                title="End"
                desc="Terminal node."
                onClose={() => setSelectedNodeId(null)}
                onDelete={selectedNode.id !== END_NODE_ID ? () => deleteNode(selectedNode.id) : undefined}
              >
                <p className="info-note">
                  When this path is reached after the agent, the run finishes and the agent's
                  last message becomes the final response shown in chat.
                </p>
                <div className="field">
                  <div className="field-label">Canned message (optional)</div>
                  <textarea
                    className="ta"
                    value={stringField(selectedNode.data, "message")}
                    onChange={(e) => updateNodeData(selectedNode.id, { message: e.target.value })}
                    placeholder="Only used if this end is reached without going through the agent, e.g. from a condition's branch."
                  />
                </div>
              </PanelShell>
            )}
          </div>
        ) : (
          currentWorkflow && (
            <RunPanel
              key={currentWorkflow.id}
              workflowId={currentWorkflow.id}
              workflowVersionId={currentWorkflow.current_version_id}
            />
          )
        )}
      </div>
    </div>
  );
}
