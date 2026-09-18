import { FormEvent, useState } from "react";
import type { Product } from "../types";

type Props = { onSave: (product: Omit<Product, "id">) => Promise<void> };

const initial = { name: "", category: "", price: "", stock: "", description: "" };

export function ProductForm({ onSave }: Props) {
  const [form, setForm] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await onSave({ ...form, price: Number(form.price), stock: Number(form.stock) });
      setForm(initial);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível cadastrar o produto.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="form-grid">
      <label>Nome<input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
      <label>Categoria<input required value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} /></label>
      <label>Preço<input required min="0.01" step="0.01" type="number" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} /></label>
      <label>Estoque<input required min="0" type="number" value={form.stock} onChange={(e) => setForm({ ...form, stock: e.target.value })} /></label>
      <label className="full">Descrição<input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button disabled={saving} type="submit">{saving ? "Salvando..." : "Cadastrar produto"}</button>
    </form>
  );
}
