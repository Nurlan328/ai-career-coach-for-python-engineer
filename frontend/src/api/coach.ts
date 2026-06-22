import { api, apiBase, getToken } from "./client";
import type { ChatTurn, RagResponse } from "../types";

export interface AskResponse {
  question: string;
  answer: string;
  source: string;
  model: string | null;
}

/** Ask grounded in the knowledge base; returns the answer + cited sources. */
export function askRag(
  question: string,
  history: ChatTurn[] = [],
): Promise<RagResponse> {
  return api<RagResponse>("/api/coach/rag", {
    method: "POST",
    body: JSON.stringify({ question, history }),
  });
}

export function ask(
  question: string,
  history: ChatTurn[] = [],
  category?: string,
): Promise<AskResponse> {
  return api<AskResponse>("/api/coach/ask", {
    method: "POST",
    body: JSON.stringify({ question, history, category: category || null }),
  });
}

/** Stream the answer; onChunk fires for each incremental text piece. */
export async function askStream(
  question: string,
  history: ChatTurn[],
  onChunk: (text: string) => void,
  signal?: AbortSignal,
  category?: string,
): Promise<void> {
  const res = await fetch(`${apiBase}/api/coach/ask/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken() ?? ""}`,
    },
    body: JSON.stringify({ question, history, category: category || null }),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`Stream failed: ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    onChunk(decoder.decode(value, { stream: true }));
  }
}
