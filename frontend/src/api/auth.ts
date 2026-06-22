import { api, apiForm, setToken } from "./client";
import type { User } from "../types";

interface TokenResponse {
  access_token: string;
  token_type: string;
}

export async function login(email: string, password: string): Promise<void> {
  // OAuth2PasswordRequestForm expects 'username' / 'password'.
  const data = await apiForm<TokenResponse>("/api/auth/login", {
    username: email,
    password,
  });
  setToken(data.access_token);
}

export function register(
  email: string,
  password: string,
  full_name?: string,
): Promise<User> {
  return api<User>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, full_name: full_name || null }),
  });
}

export function me(): Promise<User> {
  return api<User>("/api/auth/me");
}
