import { useEffect, useState } from "react";
import { checkout, getPlans, getUsage, portal } from "../api/billing";
import { ApiError } from "../api/client";
import type { PlanOut, UsageOut } from "../types";

const limitLabel = (n: number | null) => (n === null ? "∞" : String(n));

// Statuses where the subscription is actually paid up (mirrors the backend).
const HEALTHY = new Set(["active", "trialing"]);

const STATUS_LABEL: Record<string, string> = {
  active: "активна",
  trialing: "пробный период",
  past_due: "платёж не прошёл",
  canceled: "отменена",
  incomplete: "не завершена",
  unpaid: "не оплачена",
};

const fmtDate = (iso: string | null) =>
  iso ? new Date(iso).toLocaleDateString("ru-RU") : null;

export default function BillingPage() {
  const [plans, setPlans] = useState<PlanOut[]>([]);
  const [usage, setUsage] = useState<UsageOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function refresh(): Promise<UsageOut> {
    const [p, u] = await Promise.all([getPlans(), getUsage()]);
    setPlans(p);
    setUsage(u);
    return u;
  }

  useEffect(() => {
    const status = new URLSearchParams(window.location.search).get("status");
    // Drop the query param so a reload doesn't replay the banner.
    if (status) window.history.replaceState({}, "", window.location.pathname);

    if (status === "cancel") setError("Оплата отменена.");

    if (status !== "success") {
      refresh().catch(() => undefined);
      return;
    }

    // Stripe redirects back the moment the card is charged, but the plan only
    // flips once the webhook lands — usually within a second, sometimes not.
    // Poll briefly instead of showing a stale "Free".
    let cancelled = false;
    setInfo("Оплата прошла, активируем подписку…");
    (async () => {
      for (let attempt = 0; attempt < 8 && !cancelled; attempt++) {
        const u = await refresh().catch(() => null);
        if (u && u.plan !== "free") {
          setInfo("Оплата прошла успешно. Спасибо!");
          return;
        }
        await new Promise((r) => setTimeout(r, 1500));
      }
      if (!cancelled)
        setInfo(
          "Оплата прошла. Подписка активируется в течение минуты — обновите страницу.",
        );
    })();
    return () => {
      cancelled = true;
    };
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

  async function onManage() {
    setError(null);
    setBusy("portal");
    try {
      const res = await portal();
      window.location.href = res.portal_url;
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Не удалось открыть портал",
      );
      setBusy(null);
    }
  }

  const periodEnd = fmtDate(usage?.current_period_end ?? null);

  return (
    <div className="page">
      <h1>Тариф и оплата</h1>

      {usage && (
        <div className="card">
          <div className="row between">
            <h3>
              Текущий тариф: <span className="badge level">{usage.plan}</span>
              {usage.status && (
                <span
                  className={
                    "badge status" + (HEALTHY.has(usage.status) ? "" : " warn")
                  }
                >
                  {STATUS_LABEL[usage.status] ?? usage.status}
                </span>
              )}
            </h3>
            {usage.manageable && (
              <button
                className="btn ghost"
                disabled={busy === "portal"}
                onClick={onManage}
              >
                {busy === "portal" ? "…" : "Управление подпиской"}
              </button>
            )}
          </div>

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

          {/* Only meaningful while the subscription is healthy: on past_due the
              date is a retry deadline, not a charge date. */}
          {periodEnd && HEALTHY.has(usage.status ?? "") && (
            <p className="muted small">
              {usage.cancel_at_period_end
                ? `Подписка отменена — Pro доступен до ${periodEnd}.`
                : `Следующее списание: ${periodEnd}`}
            </p>
          )}
        </div>
      )}

      {usage?.status === "past_due" && (
        <div className="alert warn">
          Платёж по подписке не прошёл: действуют лимиты тарифа Free. Обновите
          карту в разделе «Управление подпиской».
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

      {usage && !usage.stripe_enabled && (
        <p className="muted small">
          Ключ Stripe не задан: оплата работает в демо-режиме — мгновенный
          апгрейд без реального списания.
        </p>
      )}
      {/* The test card only works on sandbox keys — never advertise it in live
          mode, where Stripe would decline it and real cards are expected. */}
      {usage?.test_mode && (
        <p className="muted small">
          Тестовый режим Stripe: карта 4242 4242 4242 4242, любая будущая дата и
          любой CVC. Реальные карты здесь не принимаются.
        </p>
      )}
      {usage?.stripe_enabled && !usage.test_mode && (
        <p className="muted small">
          Оплата и хранение карты — на стороне Stripe. Данные карты не проходят
          через этот сервис.
        </p>
      )}
    </div>
  );
}
