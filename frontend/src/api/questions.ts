import { api } from "./client";
import type { QuestionGenResponse } from "../types";

export function getCategories(): Promise<{ categories: string[]; levels: string[] }> {
  return api("/api/questions/categories");
}

export function generateQuestions(
  category: string,
  level: string,
  count: number,
): Promise<QuestionGenResponse> {
  return api<QuestionGenResponse>("/api/questions/generate", {
    method: "POST",
    body: JSON.stringify({ category, level, count }),
  });
}
