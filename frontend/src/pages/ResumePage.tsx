import { type FormEvent, useState } from "react";
import { ApiError } from "../api/client";
import { uploadResume } from "../api/resumes";
import type { ResumeOut } from "../types";

export default function ResumePage() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ResumeOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setError(null);
    setBusy(true);
    setResult(null);
    try {
      setResult(await uploadResume(file));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ошибка загрузки");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <h1>Анализ резюме</h1>
      <p className="muted">Поддерживаются PDF, DOCX, TXT, MD.</p>

      <form className="card row" onSubmit={onSubmit}>
        <input
          type="file"
          accept=".pdf,.docx,.txt,.md"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <button className="btn primary" disabled={!file || busy}>
          {busy ? "Анализируем…" : "Загрузить и проанализировать"}
        </button>
      </form>

      {error && <div className="alert error">{error}</div>}

      {result && (
        <div className="card">
          <div className="resume-head">
            <h3>{result.filename}</h3>
            {result.detected_level && (
              <span className="badge level">{result.detected_level}</span>
            )}
          </div>
          {result.ai_summary && <p>{result.ai_summary}</p>}

          {result.skills && result.skills.length > 0 && (
            <>
              <h4>Навыки</h4>
              <div className="chips">
                {result.skills.map((s) => (
                  <span key={s} className="chip">
                    {s}
                  </span>
                ))}
              </div>
            </>
          )}

          <Section title="Сильные стороны" items={result.strengths} />
          <Section title="Слабые стороны" items={result.weaknesses} />
          <Section title="Рекомендации" items={result.recommendations} />
        </div>
      )}
    </div>
  );
}

function Section({ title, items }: { title: string; items: string[] | null }) {
  if (!items || items.length === 0) return null;
  return (
    <>
      <h4>{title}</h4>
      <ul>
        {items.map((it, i) => (
          <li key={i}>{it}</li>
        ))}
      </ul>
    </>
  );
}
