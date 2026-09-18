import { FormEvent, useState } from "react";
import type { Client } from "../types";

type Props = { onSave: (client: Omit<Client, "id">) => Promise<void> };

const initial = { name: "", email: "", phone: "", city: "" };

export function ClientForm({ onSave }: Props) {
  const [form, setForm] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await onSave(form);
      setForm(initial);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível cadastrar o cliente.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="form-grid">
      <label>Nome<input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
      <label>E-mail<input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
      <label>Telefone<input required value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></label>
      <label>Cidade<input required value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} /></label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button disabled={saving} type="submit">{saving ? "Salvando..." : "Cadastrar cliente"}</button>
    </form>
  );
}
