import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getHistory } from "../api/interviews";
import { useAuth } from "../auth/AuthContext";
import type { InterviewListItem } from "../types";

const CARDS = [
  { to: "/resume", title: "Анализ резюме", desc: "Загрузите резюме — получите уровень и рекомендации." },
  { to: "/questions", title: "Генерация вопросов", desc: "Вопросы по 14 темам Python backend." },
  { to: "/interview", title: "Mock-интервью", desc: "Текстовое интервью с оценкой ответов." },
  { to: "/tutor", title: "AI-тьютор", desc: "Задайте любой вопрос по Python — с потоковым ответом." },
];

export default function DashboardPage() {
  const { user } = useAuth();
  const [history, setHistory] = useState<InterviewListItem[]>([]);

  useEffect(() => {
    getHistory().then(setHistory).catch(() => undefined);
  }, []);

  return (
    <div className="page">
      <h1>Привет, {user?.full_name || user?.email} 👋</h1>
      <p className="muted">Выберите, с чего начать подготовку.</p>

      <div className="card-grid">
        {CARDS.map((c) => (
          <Link key={c.to} to={c.to} className="card feature-card">
            <h3>{c.title}</h3>
            <p className="muted">{c.desc}</p>
          </Link>
        ))}
      </div>

      <h2>Последние интервью</h2>
      {history.length === 0 ? (
        <p className="muted">Пока нет пройденных интервью.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Тема</th>
              <th>Уровень</th>
              <th>Статус</th>
              <th>Балл</th>
            </tr>
          </thead>
          <tbody>
            {history.slice(0, 8).map((i) => (
              <tr key={i.id}>
                <td>{i.category}</td>
                <td>{i.level}</td>
                <td>
                  <span className={"badge " + (i.status === "completed" ? "ok" : "")}>
                    {i.status}
                  </span>
                </td>
                <td>{i.total_score ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
