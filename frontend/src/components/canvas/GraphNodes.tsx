import { Handle, Position, type NodeProps } from "reactflow";
import { ELSE_BRANCH } from "../../lib/defaultGraph";
import type { IfElseBranch } from "../../types";
import { AgentIcon, EndIcon, IfElseIcon, StartIcon, StickyNoteIcon } from "./icons";

export function StartNode({ selected }: NodeProps) {
  return (
    <div className={`rf-node n-start${selected ? " selected" : ""}`}>
      <div className="rf-node-head">
        <span className="rf-node-icon">
          <StartIcon />
        </span>
        <div className="rf-node-title">Start</div>
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

export function AgentNode({ data, selected }: NodeProps) {
  const name = typeof data?.name === "string" && data.name.trim() ? data.name : "Agent";
  return (
    <div className={`rf-node n-agent${selected ? " selected" : ""}`}>
      <div className="rf-node-head">
        <span className="rf-node-icon">
          <AgentIcon />
        </span>
        <div className="rf-node-title">{name}</div>
      </div>
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

export function EndNode({ selected }: NodeProps) {
  return (
    <div className={`rf-node n-end${selected ? " selected" : ""}`}>
      <div className="rf-node-head">
        <span className="rf-node-icon">
          <EndIcon />
        </span>
        <div className="rf-node-title">End</div>
      </div>
      <Handle type="target" position={Position.Left} />
    </div>
  );
}

export function IfElseNode({ data, selected }: NodeProps) {
  const branches: IfElseBranch[] = Array.isArray(data?.branches) ? data.branches : [];
  const rows = [
    ...branches.map((b) => ({ id: b.id, label: b.label || "If" })),
    { id: ELSE_BRANCH, label: "Else" },
  ];
  return (
    <div className={`rf-node n-if-else${selected ? " selected" : ""}`}>
      <div className="rf-node-head">
        <span className="rf-node-icon">
          <IfElseIcon />
        </span>
        <div className="rf-node-title">If / else</div>
      </div>
      <Handle type="target" position={Position.Left} />
      <div className="if-else-rows">
        {rows.map((row) => (
          <div className="if-else-row" key={row.id}>
            <span className={`if-else-row-label${row.id === ELSE_BRANCH ? " is-else" : ""}`}>
              {row.label}
            </span>
            <Handle type="source" position={Position.Right} id={row.id} />
          </div>
        ))}
      </div>
    </div>
  );
}

export function StickyNoteNode({ data, selected }: NodeProps) {
  const text = typeof data?.text === "string" ? data.text : "";
  return (
    <div className={`rf-node n-sticky-note${selected ? " selected" : ""}`}>
      <span className="rf-node-icon">
        <StickyNoteIcon />
      </span>
      {text ? (
        <p className="sticky-note-text">{text}</p>
      ) : (
        <p className="sticky-note-placeholder">Click to add a note…</p>
      )}
    </div>
  );
}

export const nodeTypes = {
  start: StartNode,
  agent: AgentNode,
  end: EndNode,
  if_else: IfElseNode,
  sticky_note: StickyNoteNode,
};
