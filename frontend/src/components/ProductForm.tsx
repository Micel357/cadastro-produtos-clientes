import { FormEvent, useState } from "react";
import type { Product } from "../types";

type Props = { onSave: (product: Omit<Product, "id">) => Promise<void> };

const initial = { name: "", category: "", price: "", stock: "", description: "" };

type FieldName = keyof typeof initial;

function validate(form: typeof initial): Partial<Record<FieldName, string>> {
  const errors: Partial<Record<FieldName, string>> = {};
  if (form.name.trim().length < 2 || form.name.length > 80) errors.name = "Informe entre 2 e 80 caracteres.";
  if (form.category.trim().length < 2 || form.category.length > 50) errors.category = "Informe entre 2 e 50 caracteres.";
  if (!form.price || Number(form.price) <= 0) errors.price = "O preço deve ser maior que zero.";
  if (!form.stock || Number(form.stock) < 0 || !Number.isInteger(Number(form.stock))) errors.stock = "Informe um estoque inteiro igual ou maior que zero.";
  if (form.description.length > 180) errors.description = "Use no máximo 180 caracteres.";
  return errors;
}

export function ProductForm({ onSave }: Props) {
  const [form, setForm] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [errors, setErrors] = useState<Partial<Record<FieldName, string>>>({});

  function update(field: FieldName, value: string) {
    const next = { ...form, [field]: value };
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
      await onSave({ ...form, price: Number(form.price), stock: Number(form.stock) });
      setForm(initial);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível cadastrar o produto.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="form-grid" noValidate>
      <label>Nome<input aria-describedby="product-name-error" aria-invalid={Boolean(errors.name)} maxLength={80} minLength={2} required value={form.name} onChange={(e) => update("name", e.target.value)} className={errors.name ? "field-invalid" : ""} />{errors.name && <small id="product-name-error">{errors.name}</small>}</label>
      <label>Categoria<input aria-describedby="product-category-error" aria-invalid={Boolean(errors.category)} maxLength={50} minLength={2} required value={form.category} onChange={(e) => update("category", e.target.value)} className={errors.category ? "field-invalid" : ""} />{errors.category && <small id="product-category-error">{errors.category}</small>}</label>
      <label>Preço<input aria-describedby="product-price-error" aria-invalid={Boolean(errors.price)} min="0.01" step="0.01" type="number" value={form.price} onChange={(e) => update("price", e.target.value)} className={errors.price ? "field-invalid" : ""} />{errors.price && <small id="product-price-error">{errors.price}</small>}</label>
      <label>Estoque<input aria-describedby="product-stock-error" aria-invalid={Boolean(errors.stock)} min="0" step="1" type="number" value={form.stock} onChange={(e) => update("stock", e.target.value)} className={errors.stock ? "field-invalid" : ""} />{errors.stock && <small id="product-stock-error">{errors.stock}</small>}</label>
      <label className="full">Descrição<input aria-describedby="product-description-error" aria-invalid={Boolean(errors.description)} maxLength={180} value={form.description} onChange={(e) => update("description", e.target.value)} className={errors.description ? "field-invalid" : ""} /><small>{form.description.length}/180 caracteres</small>{errors.description && <small id="product-description-error">{errors.description}</small>}</label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button disabled={saving} type="submit">{saving ? "Salvando..." : "Cadastrar produto"}</button>
    </form>
  );
}
