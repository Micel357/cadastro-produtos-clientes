import type { Client, Dashboard, Product } from "../types";

const baseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Não foi possível concluir a operação.");
  }

  return response.status === 204 ? (undefined as T) : response.json() as Promise<T>;
}

export const api = {
  dashboard: () => request<Dashboard>("/api/dashboard"),
  products: () => request<Product[]>("/api/products"),
  clients: () => request<Client[]>("/api/clients"),
  addProduct: (product: Omit<Product, "id">) => request<Product>("/api/products", { method: "POST", body: JSON.stringify(product) }),
  addClient: (client: Omit<Client, "id">) => request<Client>("/api/clients", { method: "POST", body: JSON.stringify(client) }),
  deleteProduct: (id: number) => request<void>(`/api/products/${id}`, { method: "DELETE" }),
  deleteClient: (id: number) => request<void>(`/api/clients/${id}`, { method: "DELETE" }),
};
