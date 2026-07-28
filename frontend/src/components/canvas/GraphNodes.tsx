import { Handle, Position, type NodeProps } from "reactflow";
import { AgentIcon, ConditionIcon, EndIcon, StartIcon } from "./icons";

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

export const nodeTypes = {
  start: StartNode,
  agent: AgentNode,
  condition: ConditionNode,
  end: EndNode,
};
