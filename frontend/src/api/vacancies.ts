import { api } from "./client";
import type { GapAnalysis, Roadmap, VacancyOut } from "../types";

export function analyzeVacancy(
  description: string,
  title?: string,
  company?: string,
): Promise<VacancyOut> {
  return api<VacancyOut>("/api/vacancies/analyze", {
    method: "POST",
    body: JSON.stringify({
      description,
      title: title || null,
      company: company || null,
    }),
  });
}

export function compareWithResume(
  vacancy_id: number,
  resume_id: number,
): Promise<GapAnalysis> {
  return api<GapAnalysis>("/api/vacancies/compare-with-resume", {
    method: "POST",
    body: JSON.stringify({ vacancy_id, resume_id }),
  });
}

export function getRoadmap(
  vacancy_id: number,
  resume_id: number,
  weeks = 4,
): Promise<Roadmap> {
  return api<Roadmap>("/api/vacancies/roadmap", {
    method: "POST",
    body: JSON.stringify({ vacancy_id, resume_id, weeks }),
  });
}
