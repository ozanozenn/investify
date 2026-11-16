"use client";

import { LogOut } from "lucide-react";
import { useEffect, useState } from "react";
import { clearToken, getToken } from "@/lib/auth";

/** Yalnızca giriş yapılmışsa görünür (geliştirme bypass'ında token yoktur). */
export function LogoutButton() {
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    setLoggedIn(getToken() !== null);
  }, []);

  if (!loggedIn) return null;

  return (
    <button
      type="button"
      onClick={() => {
        clearToken();
        window.location.assign("/giris");
      }}
      title="Çıkış yap"
      className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted hover:text-foreground"
    >
      <LogOut size={14} />
      Çıkış
    </button>
  );
}
