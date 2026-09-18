import { FormEvent, useState } from "react";
import type { Client } from "../types";

type Props = { onSave: (client: Omit<Client, "id">) => Promise<void> };

const initial = { name: "", email: "", phone: "", city: "" };

type FieldName = keyof typeof initial;

function formatPhone(value: string): string {
  const digits = value.replace(/\D/g, "").slice(0, 11);
  if (digits.length <= 2) return digits;
  if (digits.length <= 6) return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
  if (digits.length <= 10) return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
  return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
}

function validate(form: typeof initial): Partial<Record<FieldName, string>> {
  const errors: Partial<Record<FieldName, string>> = {};
  if (form.name.trim().length < 2 || form.name.length > 80) errors.name = "Informe entre 2 e 80 caracteres.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email) || form.email.length > 254) errors.email = "Informe um e-mail válido.";
  if (![10, 11].includes(form.phone.replace(/\D/g, "").length)) errors.phone = "Digite DDD e telefone com 10 ou 11 dígitos.";
  if (form.city.trim().length < 2 || form.city.length > 60) errors.city = "Informe entre 2 e 60 caracteres.";
  return errors;
}

export function ClientForm({ onSave }: Props) {
  const [form, setForm] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [errors, setErrors] = useState<Partial<Record<FieldName, string>>>({});

  function update(field: FieldName, value: string) {
    const next = { ...form, [field]: field === "phone" ? formatPhone(value) : value };
    setForm(next);
    const validation = validate(next);
    setErrors((current) => ({ ...current, [field]: validation[field] }));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validation = validate(form);
    setErrors(validation);
    if (Object.keys(validation).length > 0) return;
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
    <form onSubmit={submit} className="form-grid" noValidate>
      <label>Nome<input aria-describedby="client-name-error" aria-invalid={Boolean(errors.name)} maxLength={80} minLength={2} required value={form.name} onChange={(e) => update("name", e.target.value)} className={errors.name ? "field-invalid" : ""} />{errors.name && <small id="client-name-error">{errors.name}</small>}</label>
      <label>E-mail<input aria-describedby="client-email-error" aria-invalid={Boolean(errors.email)} maxLength={254} required type="email" value={form.email} onChange={(e) => update("email", e.target.value)} className={errors.email ? "field-invalid" : ""} />{errors.email && <small id="client-email-error">{errors.email}</small>}</label>
      <label>Telefone<input aria-describedby="client-phone-error" aria-invalid={Boolean(errors.phone)} inputMode="numeric" maxLength={15} placeholder="(85) 99999-9999" required type="tel" value={form.phone} onChange={(e) => update("phone", e.target.value)} className={errors.phone ? "field-invalid" : ""} />{errors.phone && <small id="client-phone-error">{errors.phone}</small>}</label>
      <label>Cidade<input aria-describedby="client-city-error" aria-invalid={Boolean(errors.city)} maxLength={60} minLength={2} required value={form.city} onChange={(e) => update("city", e.target.value)} className={errors.city ? "field-invalid" : ""} />{errors.city && <small id="client-city-error">{errors.city}</small>}</label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button disabled={saving} type="submit">{saving ? "Salvando..." : "Cadastrar cliente"}</button>
    </form>
  );
}
