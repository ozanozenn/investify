"use client";

import { LogIn } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Card, CardBody } from "@/components/ui/card";
import { login } from "@/lib/auth";

// Yalnızca aynı site içindeki yollara dön (açık yönlendirmeyi önler).
function safeNext(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/";
}

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      router.replace(safeNext(params.get("next")));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Giriş yapılamadı.");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <label className="block text-xs font-medium text-muted">
        E-posta
        <input
          type="email"
          autoComplete="username"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mt-1 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground outline-none focus:border-[var(--accent)]"
        />
      </label>
      <label className="block text-xs font-medium text-muted">
        Şifre
        <input
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-1 w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground outline-none focus:border-[var(--accent)]"
        />
      </label>
      {error && <p className="text-xs text-[var(--negative)]">{error}</p>}
      <button
        type="submit"
        disabled={submitting}
        className="flex w-full items-center justify-center gap-2 rounded-md border border-border bg-surface px-3 py-2 text-sm font-medium text-foreground hover:bg-surface-hover disabled:opacity-50"
      >
        <LogIn size={14} />
        {submitting ? "Giriş yapılıyor..." : "Giriş yap"}
      </button>
    </form>
  );
}

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-sm">
        <CardBody className="space-y-4">
          <div>
            <div className="text-sm font-semibold tracking-wide text-muted">INVESTIFY</div>
            <h1 className="mt-1 text-lg font-semibold text-foreground">Giriş yap</h1>
          </div>
          <Suspense fallback={null}>
            <LoginForm />
          </Suspense>
        </CardBody>
      </Card>
    </div>
  );
}
