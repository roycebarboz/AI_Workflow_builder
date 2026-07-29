import { Handle, Position, type NodeProps } from "reactflow";
import { ELSE_BRANCH } from "../../lib/defaultGraph";
import type { IfElseBranch } from "../../types";
import { AgentIcon, ConditionIcon, EndIcon, IfElseIcon, StartIcon, StickyNoteIcon } from "./icons";

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

export function AgentNode({ selected }: NodeProps) {
  return (
    <div className={`rf-node n-agent${selected ? " selected" : ""}`}>
      <div className="rf-node-head">
        <span className="rf-node-icon">
          <AgentIcon />
        </span>
        <div className="rf-node-title">Agent</div>
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

export function ConditionNode({ selected }: NodeProps) {
  return (
    <div className={`rf-node n-condition${selected ? " selected" : ""}`}>
      <div className="rf-node-head">
        <span className="rf-node-icon">
          <ConditionIcon />
        </span>
        <div className="rf-node-title">Condition</div>
      </div>
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} id="true" style={{ top: "38%" }} />
      <span className="rf-node-branch-label branch-true" style={{ top: "38%" }}>
        True
      </span>
      <Handle type="source" position={Position.Right} id="false" style={{ top: "72%" }} />
      <span className="rf-node-branch-label branch-false" style={{ top: "72%" }}>
        False
      </span>
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
  condition: ConditionNode,
  end: EndNode,
  if_else: IfElseNode,
  sticky_note: StickyNoteNode,
};
