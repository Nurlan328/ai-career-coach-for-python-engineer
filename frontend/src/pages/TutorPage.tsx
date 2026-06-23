import { type FormEvent, useEffect, useRef, useState } from "react";
import { askRag, askStream } from "../api/coach";
import { apiBase } from "../api/client";
import { useSpeech } from "../hooks/useSpeech";
import type { ChatTurn, RagSource } from "../types";

type Msg = ChatTurn & { sources?: RagSource[] };

export default function TutorPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [ragMode, setRagMode] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [llmEnabled, setLlmEnabled] = useState<boolean | null>(null);
  const [readAloud, setReadAloud] = useState(false);
  const speech = useSpeech("ru-RU");
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch(`${apiBase}/`)
      .then((r) => r.json())
      .then((d) => setLlmEnabled(Boolean(d.llm_enabled)))
      .catch(() => setLlmEnabled(null));
  }, []);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages]);

  function history(): ChatTurn[] {
    return messages.map(({ role, content }) => ({ role, content }));
  }

  async function onSend(e: FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (!question || streaming) return;
    const prior = history();
    setInput("");
    setError(null);
    setStreaming(true);

    if (ragMode) {
      setMessages((p) => [...p, { role: "user", content: question }]);
      try {
        const resp = await askRag(question, prior);
        setMessages((p) => [
          ...p,
          { role: "assistant", content: resp.answer, sources: resp.sources },
        ]);
        if (readAloud) speech.speak(resp.answer);
      } catch {
        setError("Ошибка запроса к базе знаний. Запущен ли бэкенд?");
      } finally {
        setStreaming(false);
      }
      return;
    }

    // Free-form streaming chat.
    setMessages((p) => [
      ...p,
      { role: "user", content: question },
      { role: "assistant", content: "" },
    ]);
    let full = "";
    try {
      await askStream(question, prior, (chunk) => {
        full += chunk;
        setMessages((p) => {
          const copy = p.slice();
          const last = copy[copy.length - 1];
          copy[copy.length - 1] = { ...last, content: last.content + chunk };
          return copy;
        });
      });
      if (readAloud) speech.speak(full);
    } catch {
      setError("Ошибка стрима. Запущен ли бэкенд на " + apiBase + "?");
      setMessages((p) => {
        const copy = p.slice();
        const last = copy[copy.length - 1];
        if (last && last.role === "assistant" && !last.content) copy.pop();
        return copy;
      });
    } finally {
      setStreaming(false);
    }
  }

  return (
    <div className="page chat-page">
      <h1>AI-тьютор</h1>
      <div className="row wrap">
        <label className="rag-toggle">
          <input
            type="checkbox"
            checked={ragMode}
            onChange={(e) => setRagMode(e.target.checked)}
          />
          Отвечать по базе знаний (с источниками)
        </label>
        {speech.supported.tts && (
          <label className="rag-toggle">
            <input
              type="checkbox"
              checked={readAloud}
              onChange={(e) => setReadAloud(e.target.checked)}
            />
            🔊 Озвучивать ответы
          </label>
        )}
      </div>

      {llmEnabled === false && (
        <div className="alert warn">
          AI отключён: не задан <code>ANTHROPIC_API_KEY</code>. В обычном режиме
          ответ будет заглушкой; в режиме базы знаний вернутся релевантные фрагменты.
        </div>
      )}

      <div className="chat" ref={listRef}>
        {messages.length === 0 && (
          <div className="muted center chat-empty">
            Задайте вопрос по Python / backend.
            <br />
            Режим «по базе знаний» отвечает с цитатами из встроенной базы.
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={"msg " + m.role}>
            <div className={"bubble " + m.role}>
              {m.content || (streaming && i === messages.length - 1 ? "…" : "")}
            </div>
            {m.role === "assistant" && m.sources && m.sources.length > 0 && (
              <details className="sources">
                <summary>Источники ({m.sources.length})</summary>
                {m.sources.map((s, j) => (
                  <div key={j} className="source">
                    <div className="source-head">
                      <span>{s.title}</span>
                      <span className="muted small">
                        {s.source} · {s.score}
                      </span>
                    </div>
                    <p className="muted small">{s.snippet}</p>
                  </div>
                ))}
              </details>
            )}
          </div>
        ))}
      </div>

      {error && <div className="alert error">{error}</div>}

      <form className="chat-input" onSubmit={onSend}>
        {speech.supported.stt && (
          <button
            type="button"
            title="Голосовой ввод"
            className={"btn ghost mic-btn" + (speech.listening ? " mic-on" : "")}
            onClick={() =>
              speech.listening
                ? speech.stopListening()
                : speech.startListening((t) =>
                    setInput((v) => (v ? v + " " : "") + t),
                  )
            }
          >
            🎤
          </button>
        )}
        <input
          type="text"
          value={input}
          placeholder={
            speech.listening
              ? "Говорите…"
              : ragMode
                ? "Вопрос по базе знаний…"
                : "Спросите голосом или текстом…"
          }
          onChange={(e) => setInput(e.target.value)}
          disabled={streaming}
        />
        <button className="btn primary" disabled={streaming || !input.trim()}>
          {streaming ? "…" : "Отправить"}
        </button>
      </form>
    </div>
  );
}
