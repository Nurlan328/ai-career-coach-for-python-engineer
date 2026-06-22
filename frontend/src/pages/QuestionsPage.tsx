import { type FormEvent, useEffect, useState } from "react";
import { ApiError } from "../api/client";
import { generateQuestions, getCategories } from "../api/questions";
import type { QuestionGenResponse } from "../types";

export default function QuestionsPage() {
  const [categories, setCategories] = useState<string[]>([]);
  const [levels, setLevels] = useState<string[]>(["junior", "middle", "senior"]);
  const [category, setCategory] = useState("Async Python");
  const [level, setLevel] = useState("middle");
  const [count, setCount] = useState(5);
  const [result, setResult] = useState<QuestionGenResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getCategories()
      .then((d) => {
        setCategories(d.categories);
        setLevels(d.levels);
        if (d.categories.length) setCategory(d.categories[0]);
      })
      .catch(() => undefined);
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      setResult(await generateQuestions(category, level, count));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ошибка генерации");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <h1>Генерация вопросов</h1>

      <form className="card row wrap" onSubmit={onSubmit}>
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
          Кол-во
          <input
            type="number"
            min={1}
            max={20}
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
          />
        </label>
        <button className="btn primary" disabled={busy}>
          {busy ? "Генерируем…" : "Сгенерировать"}
        </button>
      </form>

      {error && <div className="alert error">{error}</div>}

      {result && (
        <div className="card">
          <div className="muted small">
            Источник: {result.source === "ai" ? "Claude" : "встроенный банк вопросов"}
          </div>
          <ol className="questions">
            {result.questions.map((q, i) => (
              <li key={i}>
                <div className="q-text">{q.question_text}</div>
                {q.expected_answer && (
                  <details>
                    <summary>Ожидаемый ответ</summary>
                    <p className="muted">{q.expected_answer}</p>
                  </details>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
