import { useState } from "react";
import type { Client, Product } from "../types";

type Props = {
  kind: "products" | "clients";
  items: Product[] | Client[];
  onDelete?: (id: number) => Promise<void>;
};

export function RegistryList({ kind, items, onDelete }: Props) {
  const [removing, setRemoving] = useState<number | null>(null);
  const [error, setError] = useState("");
  async function remove(id: number) {
    if (!onDelete) return;
    setRemoving(id);
    setError("");
    try { await onDelete(id); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível excluir."); }
    finally { setRemoving(null); }
  }
  return (
    <section className="list" aria-live="polite">
      {error && <p className="form-error" role="alert">{error}</p>}
      {items.length === 0 && <p>Nenhum cadastro encontrado.</p>}
      {items.map(item => <article className="list-item" key={item.id}>
        <div>
          <strong>{item.name}</strong>
          {kind === "products" ? <span>{(item as Product).category} · R$ {(item as Product).price.toFixed(2)} · Estoque: {(item as Product).stock}</span>
            : <span>{(item as Client).email} · {(item as Client).city}</span>}
        </div>
        {onDelete && <button className="danger" type="button" disabled={removing !== null} onClick={() => void remove(item.id)}>{removing === item.id ? "Excluindo..." : "Excluir"}</button>}
      </article>)}
    </section>
  );
}
