import type { Client, Product } from "../types";

type Props = {
  kind: "products" | "clients";
  items: Product[] | Client[];
  onDelete: (id: number) => Promise<void>;
};

export function RegistryList({ kind, items, onDelete }: Props) {
  const isProduct = kind === "products";

  return (
    <section className="list" aria-live="polite">
      {items.length === 0 && <p>Nenhum cadastro encontrado.</p>}
      {items.map((item) => (
        <article className="list-item" key={item.id}>
          <div>
            <strong>{item.name}</strong>
            {isProduct ? (
              <span>{(item as Product).category} · R$ {(item as Product).price.toFixed(2)} · Estoque: {(item as Product).stock}</span>
            ) : (
              <span>{(item as Client).email} · {(item as Client).city}</span>
            )}
          </div>
          <button className="danger" type="button" onClick={() => onDelete(item.id)}>Excluir</button>
        </article>
      ))}
    </section>
  );
}
