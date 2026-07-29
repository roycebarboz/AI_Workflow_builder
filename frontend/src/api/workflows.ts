import type { ToolInfo, Workflow, WorkflowGraph } from "../types";
import { API_BASE_URL, asJson } from "./client";

export interface WorkflowInput {
  name: string;
  graph: WorkflowGraph;
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
