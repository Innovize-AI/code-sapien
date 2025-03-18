"use client"
import { emailSchema } from '@/components/ui/inbox/data/schema';
import React, { createContext, useContext, useState, ReactNode, useEffect } from 'react';
import { z } from 'zod';
import { usePathname, useRouter } from "next/navigation"; // Import useRouter for route change detection

// Infer the type from the schema
export type EmailData = z.infer<typeof emailSchema>;

// Define the shape of the context value
interface RowContextValue {
  row: EmailData | null;
  setRow: React.Dispatch<React.SetStateAction<EmailData | null>>;
}

// Create the context
const RowContext = createContext<RowContextValue | undefined>(undefined);

// Provider props interface
interface RowProviderProps {
  children: ReactNode;
}

// Create the provider
export const RowProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [row, setRow] = useState<EmailData | null>(() => {
    // Initialize state from localStorage if available
    if (typeof window !== "undefined") {
      const storedRow = localStorage.getItem("row");
      return storedRow ? JSON.parse(storedRow) : null;
    }
    return null;
  });
  const pathname = usePathname(); // Get the current route pathname

  // Save row data to localStorage whenever it changes
  useEffect(() => {
    if (row) {
      localStorage.setItem("row", JSON.stringify(row));
    } else {
      localStorage.removeItem("row"); // Clean up if row is cleared
    }
  }, [row]);

  useEffect(() => {
    // Reset context only on refresh
    if (typeof window !== "undefined") {
      const isRefreshed = sessionStorage.getItem("isRefreshed");
      if (!isRefreshed) {
        setRow(null); // Reset row on initial page load (refresh)
        sessionStorage.setItem("isRefreshed", "true"); // Mark as loaded
      }
    }
  }, []);


  return (
    <RowContext.Provider value={{ row, setRow }}>
      {children}
    </RowContext.Provider>
  );
};


// Custom hook to use the context
export function useRow(): RowContextValue {
  const context = React.useContext(RowContext);
  if (!context) {
    throw new Error('useRow must be used within a RowProvider');
  }
  return context
};