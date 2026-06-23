import { useEffect, useState } from "react";
import { checkout, getPlans, getUsage } from "../api/billing";
import { ApiError } from "../api/client";
import type { PlanOut, UsageOut } from "../types";

const limitLabel = (n: number | null) => (n === null ? "∞" : String(n));

export default function BillingPage() {
  const [plans, setPlans] = useState<PlanOut[]>([]);
  const [usage, setUsage] = useState<UsageOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function refresh() {
    const [p, u] = await Promise.all([getPlans(), getUsage()]);
    setPlans(p);
    setUsage(u);
  }

  useEffect(() => {
    refresh().catch(() => undefined);
    const status = new URLSearchParams(window.location.search).get("status");
    if (status === "success") setInfo("Оплата прошла успешно. Спасибо!");
    if (status === "cancel") setError("Оплата отменена.");
  }, []);

  async function onUpgrade(plan: string) {
    setError(null);
    setInfo(null);
    setBusy(plan);
    try {
      const res = await checkout(plan);
      if (res.checkout_url) {
        window.location.href = res.checkout_url; // Stripe Checkout
        return;
      }
      setInfo(`Тариф «${plan}» активирован (демо-режим без Stripe).`);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ошибка оплаты");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="page">
      <h1>Тариф и оплата</h1>

      {usage && (
        <div className="card">
          <h3>
            Текущий тариф: <span className="badge level">{usage.plan}</span>
          </h3>
          <p className="muted">
            Интервью в этом месяце: {usage.interviews_used} /{" "}
            {limitLabel(usage.interviews_limit)}
          </p>
          {usage.interviews_limit !== null && (
            <div className="meter">
              <div
                className="meter-fill"
                style={{
                  width: `${Math.min(100, (100 * usage.interviews_used) / usage.interviews_limit)}%`,
                }}
              />
            </div>
          )}
        </div>
      )}

      {info && <div className="alert ok-alert">{info}</div>}
      {error && <div className="alert error">{error}</div>}

      <div className="card-grid">
        {plans.map((p) => (
          <div key={p.id} className="card plan-card">
            <h3>{p.label}</h3>
            <div className="plan-price">
              {p.price_usd === 0 ? "Бесплатно" : `$${p.price_usd}/мес`}
            </div>
            <ul>
              <li>Интервью в месяц: {limitLabel(p.interviews_per_month)}</li>
              <li>Анализ резюме и вакансий</li>
              <li>AI-тьютор и база знаний</li>
            </ul>
            {usage?.plan === p.id ? (
              <button className="btn ghost" disabled>
                Текущий тариф
              </button>
            ) : p.id === "free" ? (
              <span className="muted small">Базовый тариф</span>
            ) : (
              <button
                className="btn primary"
                disabled={busy === p.id}
                onClick={() => onUpgrade(p.id)}
              >
                {busy === p.id ? "…" : `Перейти на ${p.label}`}
              </button>
            )}
          </div>
        ))}
      </div>

      <p className="muted small">
        Без ключа Stripe оплата работает в демо-режиме: мгновенный апгрейд без
        реального списания.
      </p>
    </div>
  );
}
