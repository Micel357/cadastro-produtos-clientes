import type { Dashboard } from "../types";

type Props = { dashboard: Dashboard };

const currency = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

export function DashboardStats({ dashboard }: Props) {
  const cards = [
    ["Produtos", dashboard.products],
    ["Clientes", dashboard.clients],
    ["Unidades em estoque", dashboard.stock],
    ["Valor em estoque", currency.format(dashboard.inventory_value)],
  ];

  return (
    <section className="stats" aria-label="Resumo do cadastro">
      {cards.map(([label, value]) => <article className="stat" key={label}>{label}<strong>{value}</strong></article>)}
    </section>
  );
}
