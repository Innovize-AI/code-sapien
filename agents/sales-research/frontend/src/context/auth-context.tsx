"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import axios from "axios";
import { API_URL } from "@/lib/api";

interface User {
  id: string;
  email: string;
  role?: string;
  full_name?: string | null;
}

interface AuthContextType {
  user: User | null;
  isOnboarded: boolean;
  isMigrated: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  checkOnboarding: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    if (typeof window !== "undefined") {
      try {
        const stored = localStorage.getItem("user");
        return stored ? JSON.parse(stored) : null;
      } catch (e) {
        return null;
      }
    }
    return null;
  });
  const [isOnboarded, setIsOnboarded] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("onboarding_complete") === "true";
    }
    return false;
  });
  const [isMigrated, setIsMigrated] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("migration_complete") === "true";
    }
    return false;
  });
  const [loading, setLoading] = useState(() => {
    if (typeof window !== "undefined") {
      // If we have a token, we consider the initial state "loaded" from cache
      return !localStorage.getItem("accessToken");
    }
    return true;
  });
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // This now just handles secondary sync if needed
    const token = localStorage.getItem("accessToken");
    if (!token && user) {
        setUser(null);
        setIsOnboarded(false);
    }
    setLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    try {
      // Updated to point to backend auth route
      const response = await axios.post(`${API_URL}/api/auth/login`, {
        email,
        password,
      });

      const { access_token, user } = response.data;

      localStorage.setItem("accessToken", access_token);
      localStorage.setItem("user", JSON.stringify(user));
      setUser(user);
      router.push("/"); // Redirect to root dashboard
    } catch (error) {
      console.error("Login failed", error);
      throw error;
    }
  };

  const checkOnboarding = async () => {
    try {
      const { getOnboardingStatus } = await import("@/lib/api");
      const status = await getOnboardingStatus();
      if (status.complete) {
        localStorage.setItem("onboarding_complete", "true");
        setIsOnboarded(true);
      } else {
        localStorage.removeItem("onboarding_complete");
        setIsOnboarded(false);
      }
      
      if (status.migration_complete) {
        localStorage.setItem("migration_complete", "true");
        setIsMigrated(true);
      } else {
        localStorage.removeItem("migration_complete");
        setIsMigrated(false);
      }

      return status.complete;
    } catch (e) {
      console.error("Failed to check onboarding status", e);
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("user");
    localStorage.removeItem("onboarding_complete");
    localStorage.removeItem("migration_complete");
    setUser(null);
    setIsOnboarded(false);
    setIsMigrated(false);
    router.push("/login");
  };

  // Protect routes - simple client-side check
  useEffect(() => {
    const publicPaths = ["/login"];
    if (!loading && !user && !publicPaths.includes(pathname)) {
      router.push("/login");
    }
  }, [user, loading, pathname, router]);

  return (
    <AuthContext.Provider value={{ user, isOnboarded, isMigrated, loading, login, logout, checkOnboarding }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
