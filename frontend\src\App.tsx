import { useEffect, useState } from "react";
import { ClientForm } from "./components/ClientForm";
import { DashboardStats } from "./components/DashboardStats";
import { ProductForm } from "./components/ProductForm";
import { RegistryList } from "./components/RegistryList";
import { api } from "./services/api";
import type { Client, Dashboard, Product } from "./types";

const emptyDashboard: Dashboard = { products: 0, clients: 0, stock: 0, inventory_value: 0 };

export default function App() {
  const [tab, setTab] = useState<"products" | "clients">("products");
  const [dashboard, setDashboard] = useState(emptyDashboard);
  const [products, setProducts] = useState<Product[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [message, setMessage] = useState("Carregando cadastros...");

  async function loadData() {
    try {
      const [nextDashboard, nextProducts, nextClients] = await Promise.all([api.dashboard(), api.products(), api.clients()]);
      setDashboard(nextDashboard);
      setProducts(nextProducts);
      setClients(nextClients);
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível acessar a API.");
    }
  }

  useEffect(() => { void loadData(); }, []);

  async function addProduct(product: Omit<Product, "id">) {
    await api.addProduct(product);
    await loadData();
  }

  async function addClient(client: Omit<Client, "id">) {
    await api.addClient(client);
    await loadData();
  }

  async function deleteProduct(id: number) {
    await api.deleteProduct(id);
    await loadData();
  }

  async function deleteClient(id: number) {
    await api.deleteClient(id);
    await loadData();
  }

  const productsActive = tab === "products";

  return (
    <main className="shell">
      <header><p className="eyebrow">PAPELARIA HORIZONTE</p><h1>Vitrine & Clientes</h1><p>Cadastros simples, rápidos e sem banco de dados.</p></header>
      <DashboardStats dashboard={dashboard} />
      <nav aria-label="Tipo de cadastro"><button className={productsActive ? "active" : ""} onClick={() => setTab("products")}>Produtos</button><button className={!productsActive ? "active" : ""} onClick={() => setTab("clients")}>Clientes</button></nav>
      {message && <p className="message">{message}</p>}
      <section className="panel">
        <div><h2>{productsActive ? "Cadastrar produto" : "Cadastrar cliente"}</h2><p>Preencha os dados abaixo para incluir um novo registro.</p></div>
        {productsActive ? <ProductForm onSave={addProduct} /> : <ClientForm onSave={addClient} />}
      </section>
      <section className="panel"><h2>{productsActive ? "Produtos cadastrados" : "Clientes cadastrados"}</h2><RegistryList kind={tab} items={productsActive ? products : clients} onDelete={productsActive ? deleteProduct : deleteClient} /></section>
    </main>
  );
}
