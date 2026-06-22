import { api } from "./client";
import type { AnswerResponse, InterviewListItem, InterviewOut } from "../types";

export function startInterview(
  category: string,
  level: string,
  num_questions: number,
): Promise<InterviewOut> {
  return api<InterviewOut>("/api/interviews/start", {
    method: "POST",
    body: JSON.stringify({ category, level, num_questions }),
  });
}

export function submitAnswer(
  interviewId: number,
  question_id: number,
  answer: string,
): Promise<AnswerResponse> {
  return api<AnswerResponse>(`/api/interviews/${interviewId}/answer`, {
    method: "POST",
    body: JSON.stringify({ question_id, answer }),
  });
}

export function getHistory(): Promise<InterviewListItem[]> {
  return api<InterviewListItem[]>("/api/interviews/history");
}
