"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "./api-client";

interface AuthUser {
  id: string;
  email: string;
  display_name: string;
  role: "user" | "admin";
}

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<AuthUser>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const stored = sessionStorage.getItem("access_token");
    if (!stored) {
      setIsLoading(false);
      return;
    }
    setToken(stored);
    api.auth
      .me()
      .then((u) => setUser({ id: u.id, email: u.email, display_name: u.display_name, role: u.role as "user" | "admin" }))
      .catch(() => {
        sessionStorage.removeItem("access_token");
        setToken(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.auth.login(email, password);
    sessionStorage.setItem("access_token", res.access_token);
    setToken(res.access_token);
    const me = await api.auth.me();
    const userObj = { id: me.id, email: me.email, display_name: me.display_name, role: me.role as "user" | "admin" };
    setUser(userObj);
    return userObj;
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem("access_token");
    setToken(null);
    setUser(null);
  }, []);

  return <AuthContext.Provider value={{ user, token, isLoading, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
