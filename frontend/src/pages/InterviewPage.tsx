import { type FormEvent, useEffect, useState } from "react";
import { ApiError } from "../api/client";
import { startInterview, submitAnswer } from "../api/interviews";
import { getCategories } from "../api/questions";
import type { AnswerFeedback, InterviewOut } from "../types";

export default function InterviewPage() {
  const [categories, setCategories] = useState<string[]>([]);
  const [levels, setLevels] = useState<string[]>(["junior", "middle", "senior"]);
  const [category, setCategory] = useState("FastAPI");
  const [level, setLevel] = useState("middle");
  const [num, setNum] = useState(3);

  const [interview, setInterview] = useState<InterviewOut | null>(null);
  const [currentId, setCurrentId] = useState<number | null>(null);
  const [answer, setAnswer] = useState("");
  const [feedbacks, setFeedbacks] = useState<Record<number, AnswerFeedback>>({});
  const [completed, setCompleted] = useState(false);
  const [totalScore, setTotalScore] = useState<number | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getCategories()
      .then((d) => {
        setCategories(d.categories);
        setLevels(d.levels);
      })
      .catch(() => undefined);
  }, []);

  async function onStart(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const iv = await startInterview(category, level, num);
      setInterview(iv);
      setCurrentId(iv.questions[0]?.id ?? null);
      setFeedbacks({});
      setCompleted(false);
      setTotalScore(null);
      setAnswer("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось начать интервью");
    } finally {
      setBusy(false);
    }
  }

  async function onAnswer(e: FormEvent) {
    e.preventDefault();
    if (!interview || currentId === null) return;
    setError(null);
    setBusy(true);
    try {
      const res = await submitAnswer(interview.id, currentId, answer);
      setFeedbacks((prev) => ({ ...prev, [currentId]: res.feedback }));
      setAnswer("");
      if (res.interview_completed) {
        setCompleted(true);
        setTotalScore(res.interview_total_score);
        setCurrentId(null);
      } else {
        setCurrentId(res.next_question?.id ?? null);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ошибка отправки ответа");
    } finally {
      setBusy(false);
    }
  }

  const current = interview?.questions.find((q) => q.id === currentId) ?? null;
  const answeredCount = interview
    ? interview.questions.filter((q) => feedbacks[q.id]).length
    : 0;

  if (!interview) {
    return (
      <div className="page">
        <h1>Mock-интервью</h1>
        <form className="card row wrap" onSubmit={onStart}>
          <label>
            Тема
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              {categories.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </label>
          <label>
            Уровень
            <select value={level} onChange={(e) => setLevel(e.target.value)}>
              {levels.map((l) => (
                <option key={l}>{l}</option>
              ))}
            </select>
          </label>
          <label>
            Вопросов
            <input
              type="number"
              min={1}
              max={20}
              value={num}
              onChange={(e) => setNum(Number(e.target.value))}
            />
          </label>
          <button className="btn primary" disabled={busy}>
            {busy ? "Готовим…" : "Начать"}
          </button>
        </form>
        {error && <div className="alert error">{error}</div>}
      </div>
    );
  }

  return (
    <div className="page">
      <div className="row between">
        <h1>
          {interview.category} · {interview.level}
        </h1>
        <button className="btn ghost" onClick={() => setInterview(null)}>
          Новое интервью
        </button>
      </div>
      <div className="progress muted">
        Отвечено {answeredCount} из {interview.questions.length}
      </div>
      {error && <div className="alert error">{error}</div>}

      {completed ? (
        <div className="card highlight">
          <h2>Интервью завершено 🎉</h2>
          <p>
            Итоговый балл: <strong>{totalScore ?? "—"}</strong> / 10
          </p>
        </div>
      ) : (
        current && (
          <form className="card" onSubmit={onAnswer}>
            <div className="muted small">
              Вопрос {current.order_index + 1} · {current.difficulty}
            </div>
            <p className="q-text big">{current.question_text}</p>
            <textarea
              rows={6}
              value={answer}
              placeholder="Ваш ответ…"
              onChange={(e) => setAnswer(e.target.value)}
              required
            />
            <button className="btn primary" disabled={busy || !answer.trim()}>
              {busy ? "Оцениваем…" : "Отправить ответ"}
            </button>
          </form>
        )
      )}

      {interview.questions
        .filter((q) => feedbacks[q.id])
        .map((q) => {
          const fb = feedbacks[q.id];
          return (
            <div key={q.id} className="card feedback">
              <div className="row between">
                <strong>Вопрос {q.order_index + 1}</strong>
                <span className={"score " + scoreClass(fb.score)}>{fb.score}/10</span>
              </div>
              <p className="muted small">{q.question_text}</p>
              <FbList title="Плюсы" items={fb.strengths} />
              <FbList title="Минусы" items={fb.weaknesses} />
              <FbList title="Чего не хватило" items={fb.missing_topics} />
              {fb.ideal_answer && (
                <details>
                  <summary>Эталонный ответ</summary>
                  <p className="muted">{fb.ideal_answer}</p>
                </details>
              )}
            </div>
          );
        })}
    </div>
  );
}

function scoreClass(score: number): string {
  if (score >= 7) return "ok";
  if (score >= 4) return "mid";
  return "low";
}

function FbList({ title, items }: { title: string; items: string[] }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="fb-list">
      <span className="fb-title">{title}:</span>
      <ul>
        {items.map((it, i) => (
          <li key={i}>{it}</li>
        ))}
      </ul>
    </div>
  );
}
