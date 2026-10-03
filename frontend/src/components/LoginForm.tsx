import { useState, type FormEvent } from "react";
import { api } from "../services/api";
import type { Session } from "../types";

export function LoginForm({ onLogin }: { onLogin: (session: Session) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try { onLogin(await api.login(email, password)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível entrar."); }
    finally { setBusy(false); }
  }
  return <section className="panel">
    <h2>Entrar na sua conta</h2>
    <p>Use a conta fornecida pelo responsável pela loja.</p>
    <form className="form-grid" onSubmit={submit}>
      <label>E-mail<input type="email" autoComplete="username" required value={email} onChange={e => setEmail(e.target.value)} /></label>
      <label>Senha<input type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} /></label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button type="submit" disabled={busy}>{busy ? "Entrando..." : "Entrar"}</button>
    </form>
  </section>;
}
