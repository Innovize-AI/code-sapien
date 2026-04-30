"use client";

import React, { createContext, useContext, useEffect, useState } from 'react';
import { getGlobalConfig } from '@/lib/api';

interface ConfigContextType {
    trialMode: boolean;
    environment: string;
    loading: boolean;
}

const ConfigContext = createContext<ConfigContextType>({
    trialMode: false,
    environment: 'dev',
    loading: true,
});

export const ConfigProvider = ({ children }: { children: React.ReactNode }) => {
    const [config, setConfig] = useState({
        trialMode: false,
        environment: 'dev',
        loading: true,
    });

    useEffect(() => {
        async function fetchConfig() {
            try {
                const data = await getGlobalConfig();
                setConfig({
                    trialMode: data.trial_mode,
                    environment: data.environment,
                    loading: false,
                });
            } catch (error) {
                console.error("Failed to fetch global config", error);
                setConfig(prev => ({ ...prev, loading: false }));
            }
        }
        fetchConfig();
    }, []);

    return (
        <ConfigContext.Provider value={config}>
            {children}
        </ConfigContext.Provider>
    );
};

export const useConfig = () => useContext(ConfigContext);
