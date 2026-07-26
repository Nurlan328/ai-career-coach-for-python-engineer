import { api } from "./client";
import type {
  CheckoutResponse,
  PlanOut,
  PortalResponse,
  UsageOut,
} from "../types";

export function getPlans(): Promise<PlanOut[]> {
  return api<PlanOut[]>("/api/billing/plans");
}

export function getUsage(): Promise<UsageOut> {
  return api<UsageOut>("/api/billing/me");
}

export function checkout(plan: string): Promise<CheckoutResponse> {
  return api<CheckoutResponse>("/api/billing/checkout", {
    method: "POST",
    body: JSON.stringify({ plan }),
  });
}

/** Ask the backend to re-read subscription state from Stripe. */
export function syncBilling(): Promise<UsageOut> {
  return api<UsageOut>("/api/billing/sync", { method: "POST" });
}

/** One-time link into the Stripe customer portal (cancel / change card). */
export function portal(): Promise<PortalResponse> {
  return api<PortalResponse>("/api/billing/portal", { method: "POST" });
}
