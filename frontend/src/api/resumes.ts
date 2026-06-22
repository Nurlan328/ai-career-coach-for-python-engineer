import { api } from "./client";
import type { ResumeOut } from "../types";

export function uploadResume(file: File): Promise<ResumeOut> {
  const fd = new FormData();
  fd.append("file", file);
  return api<ResumeOut>("/api/resumes/upload", { method: "POST", body: fd });
}

export function listResumes(): Promise<ResumeOut[]> {
  return api<ResumeOut[]>("/api/resumes");
}
