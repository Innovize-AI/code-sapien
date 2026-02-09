import axios from 'axios';

const API_URL = 'http://localhost:8000';

export interface LeadData {
    linkedin_url?: string;
    website?: string;
    email?: string;
    lead_source?: string;
    download_marketing_material?: boolean;
    demo_requested?: boolean;
    referral_partner_introduction?: boolean;
    project_urgency?: number; // 1: Low, 2: Medium, 3: High
    refresh?: boolean;
}

export const checkExistingReports = async (leads: { linkedin_url?: string; url?: string; email?: string }[]) => {
    try {
        const response = await axios.post(`${API_URL}/sales-research/check-existing`, { leads });
        return response.data;
    } catch (error) {
        console.error("Error checking existing reports:", error);
        return {};
    }
};

export const generateResearch = async (
    data: LeadData,
    onUpdate?: (status: string) => void
) => {
    const params = new URLSearchParams();
    if (data.linkedin_url) params.append('linkedin_url', data.linkedin_url);
    if (data.website) params.append('website', data.website);
    if (data.email) {
        params.append('email', data.email);
    }

    const { linkedin_url, website, email, ...body } = data;

    const response = await fetch(`${API_URL}/sales-research/?${params.toString()}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
    });

    if (!response.ok) {
        throw new Error('Failed to generate research');
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let finalResult = null;
    let buffer = '';

    if (reader) {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const parts = buffer.split('\n\n');
            buffer = parts.pop() || ''; // Keep the incomplete part in the buffer

            for (const part of parts) {
                if (part.trim().startsWith('data: ')) {
                    const jsonStr = part.replace(/^data: /, '').trim();
                    try {
                        const data = JSON.parse(jsonStr);
                        if (data.status === 'Done') {
                            finalResult = data.result;
                        } else if (data.status === 'Error') {
                            throw new Error(data.message || 'An error occurred during research');
                        } else if (onUpdate) {
                            onUpdate(data.status);
                        }
                    } catch (e) {
                        // Only log if it's not a syntax error from incomplete JSON (which shouldn't happen with correct buffering)
                        console.error('Error parsing SSE data', e);
                    }
                }
            }
        }
    }

    return finalResult;
};

export interface LeadDiscoveryInput {
    industry: string;
    job_title: string;
    location?: string;
    company_size?: string;
    provider?: 'tavily' | 'apollo' | 'competitor' | 'linkedin_keyword';
    keywords?: string[];
}

export const discoverLeads = async (data: LeadDiscoveryInput) => {
    const response = await axios.post(`${API_URL}/sales-research/discover`, data);
    return response.data;
};

export const fetchHistory = async () => {
    const response = await axios.get(`${API_URL}/sales-research/history`);
    return response.data;
};

export const fetchReport = async (id: string) => {
    const response = await axios.get(`${API_URL}/sales-research/history/${id}`);
    return response.data;
};

export const bulkAnalyzeLeads = async (
    leads: { url?: string, website?: string }[],
    options: Omit<LeadData, 'linkedin_url' | 'website' | 'email'>,
    onUpdate?: (data: { status: string, url?: string }) => void
) => {
    const response = await fetch(`${API_URL}/sales-research/bulk`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            leads,
            options
        }),
    });

    if (!response.ok) {
        throw new Error('Failed to start bulk analysis');
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let results = [];
    let buffer = '';

    if (reader) {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const parts = buffer.split('\n\n');
            buffer = parts.pop() || ''; // Keep the incomplete part in the buffer

            for (const part of parts) {
                if (part.trim().startsWith('data: ')) {
                    const jsonStr = part.replace(/^data: /, '').trim();
                    try {
                        const data = JSON.parse(jsonStr);
                        if (data.status === 'Done') {
                            results = data.results;
                        } else if (data.status === 'Error') {
                            throw new Error(data.message || 'An error occurred during research');
                        } else if (onUpdate) {
                            // Backend sends { status: string, url?: string } for progress
                            onUpdate({ status: data.status, url: data.url });
                        }
                    } catch (e) {
                        console.error('Error parsing SSE data', e);
                    }
                }
            }
        }
    }

    return results;
};

export interface IdealProfileData {
    industry: string;
    company_size?: string;
    revenue?: string;
    job_title: string;
    value_proposition?: string;
}

export const getICP = async (): Promise<IdealProfileData | null> => {
    try {
        const response = await axios.get(`${API_URL}/api/settings/icp`);
        return response.data;
    } catch (e) {
        return null;
    }
};

export const saveICP = async (data: IdealProfileData) => {
    const response = await axios.post(`${API_URL}/api/settings/icp`, data);
    return response.data;
};

export interface DashboardStats {
    total_leads: number;
    avg_lead_score: number;
    high_potential_leads: number;
    time_saved_hours: number;
}

export const fetchDashboardStats = async (): Promise<DashboardStats | null> => {
    try {
        const response = await axios.get(`${API_URL}/api/dashboard/stats`);
        return response.data;
    } catch (e) {
        console.error("Failed to fetch dashboard stats", e);
        return null;
    }
};
export interface IntegrationSettings {
    tavily_api_key?: string;
    apollo_api_key?: string;
    user_linkedin_url?: string;
    company_linkedin_url?: string;
    email_config?: string;
    integrations_config?: string;
    kit_api_key?: string;
    kit_api_secret?: string;
}


export const getIntegrations = async (): Promise<IntegrationSettings | null> => {
    try {
        const response = await axios.get(`${API_URL}/api/settings/integrations`);
        return response.data;
    } catch (e) {
        return null;
    }
};

export const saveIntegrations = async (data: IntegrationSettings) => {
    const response = await axios.post(`${API_URL}/api/settings/integrations`, data);
    return response.data;
};

export const getOnboardingStatus = async (): Promise<{ complete: boolean }> => {
    const response = await axios.get(`${API_URL}/api/settings/onboarding-status`);
    return response.data;
};

export const setOnboardingComplete = async () => {
    const response = await axios.post(`${API_URL}/api/settings/onboarding-complete`);
    return response.data;
};

export const fetchKitForms = async () => {
    const response = await axios.get(`${API_URL}/api/integrations/kit/forms`);
    return response.data;
};
    
export const analyzeCompetitors = async (urls: string[]) => {
    const response = await axios.post(`${API_URL}/api/competitor-analysis/analyze`, { urls });
    return response.data;
};

export interface Competitor {
    id: string;
    name?: string;
    linkedin_url: string;
    created_at: string;
}

export const getCompetitors = async (): Promise<Competitor[]> => {
    const response = await axios.get(`${API_URL}/api/competitors/`);
    return response.data;
};

export const addCompetitor = async (data: { name?: string, linkedin_url: string }) => {
    const response = await axios.post(`${API_URL}/api/competitors/`, data);
    return response.data;
};

export const deleteCompetitor = async (id: string) => {
    const response = await axios.delete(`${API_URL}/api/competitors/${id}`);
    return response.data;
};

export interface CompetitorLead {
    name: string;
    linkedin_url: string | null;
    comment_text: string;
    source_post: string;
    source_post_url?: string;
    competitor: string;
    headline?: string;
    is_fit?: boolean;
    is_competitor?: boolean;
    is_decision_maker?: boolean;
    fit_reasoning?: string;
}

export const discoverCompetitorLeads = async (urls: string[]): Promise<{ leads: CompetitorLead[] }> => {
    const response = await axios.post(`${API_URL}/api/competitor-analysis/leads`, { urls });
    return response.data;
};

export interface IdentifiedProfile {
    id: string;
    name?: string;
    headline?: string;
    linkedin_url: string;

    // Classification
    is_fit?: boolean;
    is_competitor?: boolean;
    is_decision_maker?: boolean;
    fit_reasoning?: string;

    comment_history?: string; // JSON string
    source_posts?: string;    // JSON string
    interaction_history?: string; // JSON string
    last_interaction_at: string;
    profile_metadata?: string;
    latest_report_id?: string;
}

export const getIdentifiedProfiles = async (skip: number = 0, limit: number = 100): Promise<{ profiles: IdentifiedProfile[], total: number }> => {
    const response = await axios.get(`${API_URL}/api/competitor-analysis/profiles?skip=${skip}&limit=${limit}`);
    return response.data;
};
