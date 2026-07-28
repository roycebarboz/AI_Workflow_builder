import type { ToolInfo, Workflow, WorkflowGraph } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface WorkflowInput {
  name: string;
  graph: WorkflowGraph;
}

async function asJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function listWorkflows(): Promise<Workflow[]> {
  return asJson(await fetch(`${API_BASE_URL}/workflows`));
}

export async function getWorkflow(id: string): Promise<Workflow> {
  return asJson(await fetch(`${API_BASE_URL}/workflows/${id}`));
}

export async function createWorkflow(input: WorkflowInput): Promise<Workflow> {
  return asJson(
    await fetch(`${API_BASE_URL}/workflows`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    })
  );
}

export async function updateWorkflow(id: string, input: WorkflowInput): Promise<Workflow> {
  return asJson(
    await fetch(`${API_BASE_URL}/workflows/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    })
  );
}

export async function listTools(): Promise<ToolInfo[]> {
  return asJson(await fetch(`${API_BASE_URL}/tools`));
}
