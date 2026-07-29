import type { ExecutionDetail, ExecutionSummary } from "../types";
import { API_BASE_URL, asJson } from "./client";

export async function listExecutions(workflowId: string): Promise<ExecutionSummary[]> {
  return asJson(await fetch(`${API_BASE_URL}/workflows/${workflowId}/executions`));
}

export async function getExecution(
  workflowId: string,
  executionId: string
): Promise<ExecutionDetail> {
  return asJson(
    await fetch(`${API_BASE_URL}/workflows/${workflowId}/executions/${executionId}`)
  );
}
