import { FormEvent, useState } from "react";

import { apiPost, setAuthToken } from "@/shared/api/client";
import { Button } from "@/shared/ui/button";
import { getStoredLanguage } from "@/shared/lib/i18n";
import { LoginRequest, LoginResponse } from "@/types/auth";

const TEXT = {
  es: {
    title: "StreamFuse Login",
    subtitle: "Se requiere acceso de administrador.",
    user: "Usuario",
    password: "Contrasena",
    signingIn: "Iniciando sesion...",
    signIn: "Iniciar sesion",
  },
  en: {
    title: "StreamFuse Login",
    subtitle: "Admin access required.",
    user: "User",
    password: "Password",
    signingIn: "Signing in...",
    signIn: "Sign in",
  },
} as const;

type LoginPageProps = {
  onAuthenticated: () => void;
};

export function LoginPage({ onAuthenticated }: LoginPageProps) {
  const tx = TEXT[getStoredLanguage()];

  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const payload: LoginRequest = { username, password };
      const response = await apiPost<LoginResponse, LoginRequest>("/auth/login", payload);
      setAuthToken(response.access_token);
      onAuthenticated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-app-gradient px-4 py-8 text-fg">
      <div className="mx-auto mt-10 w-full max-w-md rounded-2xl border border-white/10 bg-card p-6 shadow-premium">
        <h1 className="font-display text-3xl text-white">{tx.title}</h1>
        <p className="mt-1 text-sm text-fg-muted">{tx.subtitle}</p>

        {error ? <p className="mt-4 text-sm text-rose-300">{error}</p> : null}

        <form onSubmit={(event) => void onSubmit(event)} className="mt-5 space-y-4">
          <div>
            <label className="mb-1 block text-xs uppercase tracking-[0.12em] text-fg-muted">{tx.user}</label>
            <input
              className="w-full rounded-lg border border-white/15 bg-white/[0.03] px-3 py-2 text-sm text-fg outline-none transition placeholder:text-fg-muted/70 focus:border-primary/60 focus:ring-2 focus:ring-primary/30"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            />
          </div>

          <div>
            <label className="mb-1 block text-xs uppercase tracking-[0.12em] text-fg-muted">{tx.password}</label>
            <input
              type="password"
              className="w-full rounded-lg border border-white/15 bg-white/[0.03] px-3 py-2 text-sm text-fg outline-none transition placeholder:text-fg-muted/70 focus:border-primary/60 focus:ring-2 focus:ring-primary/30"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>

          <Button type="submit" variant="default" disabled={loading}>
            {loading ? tx.signingIn : tx.signIn}
          </Button>
        </form>
      </div>
    </div>
  );
}
