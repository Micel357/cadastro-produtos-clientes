import type { Client, Dashboard, Product, Session } from "../types";

const baseUrl = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

let refreshing: Promise<boolean> | null = null;
async function renew(): Promise<boolean> {
  if (!refreshing) {
    refreshing = fetch(`${baseUrl}/api/auth/refresh`, { method: "POST", credentials: "include" })
      .then(response => response.ok).catch(() => false).finally(() => { refreshing = null; });
  }
  return refreshing;
}

async function request<T>(path: string, options?: RequestInit, retry = true): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (response.status === 401 && retry && await renew()) return request<T>(path, options, false);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(body.detail ?? "Não foi possível concluir a operação.", response.status);
  }
  return response.status === 204 ? (undefined as T) : response.json() as Promise<T>;
}

export const api = {
  session: () => request<Session>("/api/auth/session"),
  login: (email: string, password: string) => request<Session>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }, false),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }, false),
  dashboard: () => request<Dashboard>("/api/dashboard"),
  products: () => request<Product[]>("/api/products"),
  clients: () => request<Client[]>("/api/clients"),
  addProduct: (product: Omit<Product, "id">) => request<Product>("/api/products", { method: "POST", body: JSON.stringify(product) }),
  addClient: (client: Omit<Client, "id">) => request<Client>("/api/clients", { method: "POST", body: JSON.stringify(client) }),
  deleteProduct: (id: number) => request<void>(`/api/products/${id}`, { method: "DELETE" }),
  deleteClient: (id: number) => request<void>(`/api/clients/${id}`, { method: "DELETE" }),
};
