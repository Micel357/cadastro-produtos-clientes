import { useEffect, useState } from "react";
import { ClientForm } from "./components/ClientForm";
import { DashboardStats } from "./components/DashboardStats";
import { LoginForm } from "./components/LoginForm";
import { ProductForm } from "./components/ProductForm";
import { RegistryList } from "./components/RegistryList";
import { api, ApiError } from "./services/api";
import type { Client, Dashboard, Product, Session } from "./types";

const emptyDashboard: Dashboard = { products: 0, clients: 0, stock: 0, inventory_value: 0 };

function Registry({ session, onExpired }: { session: Session; onExpired: () => void }) {
  const [tab, setTab] = useState<"products" | "clients">("products");
  const [dashboard, setDashboard] = useState(emptyDashboard);
  const [products, setProducts] = useState<Product[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [message, setMessage] = useState("Carregando cadastros...");
  const canWrite = session.access_role === "operator";

  async function loadData() {
    try {
      const [nextDashboard, nextProducts, nextClients] = await Promise.all([api.dashboard(), api.products(), api.clients()]);
      setDashboard(nextDashboard); setProducts(nextProducts); setClients(nextClients); setMessage("");
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) onExpired();
      else setMessage(error instanceof Error ? error.message : "Não foi possível acessar a API.");
    }
  }
  useEffect(() => { void loadData(); }, []);

  async function addProduct(product: Omit<Product, "id">) { await api.addProduct(product); await loadData(); }
  async function addClient(client: Omit<Client, "id">) { await api.addClient(client); await loadData(); }
  async function deleteProduct(id: number) { await api.deleteProduct(id); await loadData(); }
  async function deleteClient(id: number) { await api.deleteClient(id); await loadData(); }
  const productsActive = tab === "products";

  return <>
    <DashboardStats dashboard={dashboard} />
    {!canWrite && <p className="message">Perfil de consulta. Os dados de contato aparecem protegidos.</p>}
    <nav aria-label="Tipo de cadastro"><button className={productsActive ? "active" : ""} onClick={() => setTab("products")}>Produtos</button><button className={!productsActive ? "active" : ""} onClick={() => setTab("clients")}>Clientes</button></nav>
    {message && <p className="message" role="status">{message} <button onClick={() => void loadData()}>Atualizar</button></p>}
    {canWrite && <section className="panel">
      <div><h2>{productsActive ? "Cadastrar produto" : "Cadastrar cliente"}</h2><p>Preencha os dados abaixo para incluir um novo registro.</p></div>
      {productsActive ? <ProductForm onSave={addProduct} /> : <ClientForm onSave={addClient} />}
    </section>}
    <section className="panel"><h2>{productsActive ? "Produtos cadastrados" : "Clientes cadastrados"}</h2><RegistryList key={tab} kind={tab} items={productsActive ? products : clients} onDelete={canWrite ? (productsActive ? deleteProduct : deleteClient) : undefined} /></section>
  </>;
}

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  async function restoreSession() {
    setLoading(true); setError("");
    try { setSession(await api.session()); }
    catch (reason) { if (!(reason instanceof ApiError && reason.status === 401)) setError(reason instanceof Error ? reason.message : "Não foi possível acessar o serviço."); }
    finally { setLoading(false); }
  }
  useEffect(() => { void restoreSession(); }, []);
  async function logout() {
    try { await api.logout(); setSession(null); setError(""); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível sair."); }
  }
  return <main className="shell">
    <header><p className="eyebrow">PAPELARIA HORIZONTE</p><h1>Vitrine & Clientes</h1><p>Cadastros simples e rápidos.</p>
      {session && <p>{session.email} <button onClick={() => void logout()}>Sair</button></p>}
    </header>
    {error && <p className="message" role="alert">{error} <button onClick={() => void restoreSession()}>Tentar novamente</button></p>}
    {loading ? <p role="status">Verificando sessão...</p> : session
      ? <Registry key={session.email} session={session} onExpired={() => setSession(null)} />
      : <LoginForm onLogin={setSession} />}
  </main>;
}
