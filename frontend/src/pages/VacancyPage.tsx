import { type FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../api/client";
import { listResumes } from "../api/resumes";
import {
  analyzeVacancy,
  compareWithResume,
  getRoadmap,
} from "../api/vacancies";
import type { GapAnalysis, ResumeOut, Roadmap, VacancyOut } from "../types";

function scoreClass(score: number): string {
  if (score >= 70) return "ok";
  if (score >= 40) return "mid";
  return "low";
}

export default function VacancyPage() {
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [description, setDescription] = useState("");

  const [vacancy, setVacancy] = useState<VacancyOut | null>(null);
  const [resumes, setResumes] = useState<ResumeOut[]>([]);
  const [resumeId, setResumeId] = useState<number | null>(null);
  const [gap, setGap] = useState<GapAnalysis | null>(null);
  const [roadmap, setRoadmap] = useState<Roadmap | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"analyze" | "compare" | "roadmap" | null>(null);

  useEffect(() => {
    listResumes()
      .then((rs) => {
        setResumes(rs);
        if (rs.length) setResumeId(rs[0].id);
      })
      .catch(() => undefined);
  }, []);

  function fail(err: unknown, fallback: string) {
    setError(err instanceof ApiError ? err.message : fallback);
  }

  async function onAnalyze(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy("analyze");
    setGap(null);
    setRoadmap(null);
    try {
      setVacancy(await analyzeVacancy(description, title, company));
    } catch (err) {
      fail(err, "Ошибка анализа вакансии");
    } finally {
      setBusy(null);
    }
  }

  async function onCompare() {
    if (!vacancy || resumeId === null) return;
    setError(null);
    setBusy("compare");
    setRoadmap(null);
    try {
      setGap(await compareWithResume(vacancy.id, resumeId));
    } catch (err) {
      fail(err, "Ошибка сравнения");
    } finally {
      setBusy(null);
    }
  }

  async function onRoadmap() {
    if (!vacancy || resumeId === null) return;
    setError(null);
    setBusy("roadmap");
    try {
      setRoadmap(await getRoadmap(vacancy.id, resumeId, 4));
    } catch (err) {
      fail(err, "Ошибка построения плана");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="page">
      <h1>Вакансия: gap-анализ и план</h1>
      <p className="muted">
        Вставьте описание вакансии — получите требования, сравнение с резюме и
        персональный план подготовки.
      </p>

      {/* 1. Analyze */}
      <form className="card" onSubmit={onAnalyze}>
        <div className="row wrap">
          <label style={{ flex: 1 }}>
            Должность
            <input value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label style={{ flex: 1 }}>
            Компания
            <input value={company} onChange={(e) => setCompany(e.target.value)} />
          </label>
        </div>
        <label>
          Описание вакансии
          <textarea
            rows={6}
            value={description}
            placeholder="Требования, обязанности, стек…"
            onChange={(e) => setDescription(e.target.value)}
            required
            minLength={20}
          />
        </label>
        <button className="btn primary" disabled={busy === "analyze"}>
          {busy === "analyze" ? "Анализируем…" : "Анализировать вакансию"}
        </button>
      </form>

      {error && <div className="alert error">{error}</div>}

      {/* Vacancy result + compare controls */}
      {vacancy && (
        <div className="card">
          <h3>{vacancy.title || "Требования вакансии"}</h3>
          {vacancy.ai_summary && <p className="muted">{vacancy.ai_summary}</p>}
          {vacancy.required_skills && vacancy.required_skills.length > 0 && (
            <div className="chips">
              {vacancy.required_skills.map((s) => (
                <span key={s} className="chip">
                  {s}
                </span>
              ))}
            </div>
          )}

          <div className="row wrap" style={{ marginTop: "1rem" }}>
            {resumes.length === 0 ? (
              <p className="muted">
                Нет резюме для сравнения. <Link to="/resume">Загрузить резюме</Link>
              </p>
            ) : (
              <>
                <label>
                  Резюме
                  <select
                    value={resumeId ?? ""}
                    onChange={(e) => setResumeId(Number(e.target.value))}
                  >
                    {resumes.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.filename}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  className="btn primary"
                  onClick={onCompare}
                  disabled={busy === "compare"}
                >
                  {busy === "compare" ? "Сравниваем…" : "Сравнить с резюме"}
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* Gap analysis */}
      {gap && (
        <div className="card">
          <div className="row between">
            <h3>Gap-анализ</h3>
            <span className={"score " + scoreClass(gap.match_score)}>
              {gap.match_score}% соответствие
            </span>
          </div>
          {gap.summary && <p>{gap.summary}</p>}

          {gap.matched_skills.length > 0 && (
            <>
              <h4>Совпадает</h4>
              <div className="chips">
                {gap.matched_skills.map((s) => (
                  <span key={s} className="chip">
                    {s}
                  </span>
                ))}
              </div>
            </>
          )}
          {gap.missing_skills.length > 0 && (
            <>
              <h4>Не хватает</h4>
              <div className="chips">
                {gap.missing_skills.map((s) => (
                  <span key={s} className="chip missing">
                    {s}
                  </span>
                ))}
              </div>
            </>
          )}
          {gap.topics_to_study.length > 0 && (
            <>
              <h4>Что учить</h4>
              <ul>
                {gap.topics_to_study.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            </>
          )}

          <button
            className="btn primary"
            onClick={onRoadmap}
            disabled={busy === "roadmap"}
          >
            {busy === "roadmap" ? "Строим план…" : "Построить план подготовки"}
          </button>
        </div>
      )}

      {/* Roadmap */}
      {roadmap && (
        <div className="card highlight">
          <h3>План подготовки · {roadmap.level}</h3>
          {roadmap.summary && <p className="muted">{roadmap.summary}</p>}
          {roadmap.weeks.map((w) => (
            <div key={w.week} className="week">
              <strong>
                Неделя {w.week}: {w.focus}
              </strong>
              {w.resources.length > 0 && (
                <p className="muted small">{w.resources.join(" · ")}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
