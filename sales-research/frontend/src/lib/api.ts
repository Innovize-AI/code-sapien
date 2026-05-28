import axios from 'axios';

// Dynamically determine API URL based on environment
const getApiUrl = () => {
    if (typeof window === 'undefined') return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    const hostname = window.location.hostname;

    // 1. Localhost Check
    if (hostname.includes('localhost') || hostname.includes('127.0.0.1')) {
        return 'http://localhost:8000';
    }

    // 2. Staging Check
    // Matches if hostname contains 'staging' (custom domain or cloud run URL)
    if (hostname.includes('staging')) {
        return 'https://glial-research-backend-service-staging-512561667165.us-central1.run.app';
    }

    // 3. Trial Check
    if (hostname.includes('trial')) {
        return 'https://glial-research-backend-service-trial-512561667165.us-central1.run.app';
    }

    // 4. Default to Production
    return 'https://glial-research-backend-service-512561667165.us-central1.run.app';
};

export const API_URL = getApiUrl();

// Configure axios defaults
axios.defaults.paramsSerializer = {
    serialize: (params) => {
        const searchParams = new URLSearchParams();
        for (const key of Object.keys(params)) {
            const param = params[key];
            if (Array.isArray(param)) {
                for (const p of param) {
                    searchParams.append(key, p);
                }
            } else if (param !== undefined && param !== null) {
                searchParams.append(key, String(param));
            }
        }
        return searchParams.toString();
    }
};

// Configure axios interceptor
axios.interceptors.request.use((config) => {
    const token = typeof window !== 'undefined' ? localStorage.getItem("accessToken") : null;
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Response interceptor to handle 401s
axios.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
                localStorage.removeItem("accessToken");
                localStorage.removeItem("user");
                window.location.href = "/login";
            }
        }
        return Promise.reject(error);
    }
);

const getAuthHeaders = (): Record<string, string> => {
    const token = typeof window !== 'undefined' ? localStorage.getItem("accessToken") : null;
    return token ? { 'Authorization': `Bearer ${token}` } : {};
};

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
            ...getAuthHeaders()
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
    industry?: string | string[];
    job_title?: string | string[];
    location?: string;
    company_size?: string | string[];
    provider?: 'tavily' | 'apollo' | 'competitor' | 'linkedin_keyword';
    keywords?: string[];
    // Person filters
    person_titles?: string[];
    include_similar_titles?: boolean;
    person_seniorities?: string[];
    contact_email_status?: string[];
    // Organization filters
    organization_ids?: string[];
    organization_domains?: string[];
    organization_locations?: string[];
    organization_num_employees_ranges?: string[];
    revenue_min?: number;
    revenue_max?: number;
    // Technology filters
    currently_using_all_of_technology_uids?: string[];
    currently_using_any_of_technology_uids?: string[];
    currently_not_using_any_of_technology_uids?: string[];
    // Job posting filters
    q_organization_job_titles?: string[];
    organization_job_locations?: string[];
    organization_num_jobs_range_min?: number;
    organization_num_jobs_range_max?: number;
    organization_job_posted_at_range_min?: string;
    organization_job_posted_at_range_max?: string;
    // General
    q_keywords?: string;
    page?: number;
    per_page?: number;
}

export const discoverLeads = async (data: LeadDiscoveryInput) => {
    const response = await axios.post(`${API_URL}/sales-research/discover`, data);
    return response.data;
};

export const enrichLeads = async (person_ids: string[]) => {
    const response = await axios.post(`${API_URL}/sales-research/enrich`, { person_ids });
    return response.data;
};

export const fetchHistory = async (
    skip: number = 0,
    limit: number = 50,
    search: string = "",
    status: string = "all",
    sort_by: string = "created_at",
    sort_order: string = "desc"
): Promise<{ items: any[], total: number }> => {
    const response = await axios.get(`${API_URL}/sales-research/history`, {
        params: { skip, limit, search, status, sort_by, sort_order }
    });
    return response.data;
};

export const fetchReport = async (id: string) => {
    const response = await axios.get(`${API_URL}/sales-research/history/${id}`);
    return response.data;
};

export const updateOutreachStatus = async (reportId: string, status: string) => {
    const response = await axios.put(`${API_URL}/sales-research/reports/${reportId}/outreach-status`, { status });
    return response.data;
};

export const updateExecutiveBlueprint = async (reportId: string, data: any) => {
    const response = await axios.put(`${API_URL}/sales-research/reports/${reportId}/executive-blueprint`, data);
    return response.data;
};

export const updateIntentAnalysis = async (reportId: string, data: any) => {
    const response = await axios.put(`${API_URL}/sales-research/reports/${reportId}/intent-analysis`, data);
    return response.data;
};

export const updateBuyerJourney = async (reportId: string, data: any) => {
    const response = await axios.put(`${API_URL}/sales-research/reports/${reportId}/buyer-journey`, data);
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
            ...getAuthHeaders()
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
    industry: string | string[];
    company_size?: string | string[];
    revenue?: string | string[];
    job_title: string | string[];
    value_proposition?: string;
}

export const getPersonalICP = async (): Promise<IdealProfileData | null> => {
    try {
        const response = await axios.get(`${API_URL}/api/settings/personal-icp`);
        return response.data;
    } catch (e: any) {
        if (e.response?.status === 401) {
            throw e; // Let auth provider handle it
        }
        return null;
    }
};

export const getGlobalICP = async (): Promise<IdealProfileData | null> => {
    try {
        const response = await axios.get(`${API_URL}/api/settings/global-icp`);
        return response.data;
    } catch (e: any) {
        if (e.response?.status === 401) {
            throw e; // Let auth provider handle it
        }
        return null;
    }
};

export const savePersonalICP = async (data: IdealProfileData) => {
    const response = await axios.post(`${API_URL}/api/settings/personal-icp`, data);
    return response.data;
};

export const saveGlobalICP = async (data: IdealProfileData) => {
    const response = await axios.post(`${API_URL}/api/settings/global-icp`, data);
    return response.data;
};

export interface UsageStats {
    used: number;
    limit: number;
    remaining: number;
}

export interface DashboardStats {
    total_leads: number;
    avg_lead_score: number;
    high_potential_leads: number;
    time_saved_hours: number;
    trial_mode: boolean;
    research_usage?: UsageStats;
    classification_usage?: UsageStats;
    lead_discovery_usage?: UsageStats;
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

export interface AnalyticsDataPoint {
    date: string;
    count: number;
}

export interface BreakdownItem {
    name: string;
    count: number;
}

export interface DashboardAnalytics {
    daily_trends: AnalyticsDataPoint[];
    lead_quality: Record<string, number>;
    competitor_breakdown: BreakdownItem[];
    keyword_breakdown: BreakdownItem[];
}

export const fetchDashboardAnalytics = async (): Promise<DashboardAnalytics | null> => {
    try {
        const response = await axios.get(`${API_URL}/api/dashboard/analytics`);
        return response.data;
    } catch (e) {
        console.error("Failed to fetch dashboard analytics", e);
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
    slack_webhook_url?: string;
    slack_user_id?: string;
    discovery_keywords?: string;
    apollo_search_config?: string;
    hubspot_access_token?: string;
    hubspot_sync_enabled?: boolean;
    million_verifier_api_key?: string;
    million_verifier_enabled?: boolean;
}


export const getIntegrations = async (): Promise<IntegrationSettings | null> => {
    try {
        const response = await axios.get(`${API_URL}/api/settings/integrations`);
        return response.data;
    } catch (e: any) {
        if (e.response?.status === 401) {
            throw e; // Let auth provider handle it
        }
        return null;
    }
};

export const saveIntegrations = async (data: IntegrationSettings) => {
    const response = await axios.post(`${API_URL}/api/settings/integrations`, data);
    return response.data;
};

export const getUsageStats = async (): Promise<any> => {
    const response = await axios.get(`${API_URL}/api/settings/usage`);
    return response.data;
};

export const getUserIntegrations = async (): Promise<{ user_linkedin_url: string | null, email_config: string | null, slack_user_id: string | null } | null> => {
    try {
        const response = await axios.get(`${API_URL}/api/settings/user-integrations`);
        return response.data;
    } catch (e) {
        return null;
    }
};

export const saveUserIntegrations = async (data: { user_linkedin_url?: string | null, email_config?: string | null, slack_user_id?: string | null }) => {
    const response = await axios.post(`${API_URL}/api/settings/user-integrations`, data);
    return response.data;
};

export interface ProductConfig {
    name: string;
    description: string;
    is_strategic_pivot?: boolean;
    target_roles?: string[];
    target_industries?: string[];
    relevant_files?: string[];
    rag_context?: string;
}

export interface SellingProfileConfig {
    company_name: string;
    description: string;
    business_model?: 'product' | 'service' | 'hybrid';
    products: ProductConfig[];
}

export const getSellingProfile = async (): Promise<SellingProfileConfig | null> => {
    try {
        const response = await axios.get(`${API_URL}/api/settings/selling-profile`);
        return response.data;
    } catch (e: any) {
        if (e.response?.status === 401) {
            throw e;
        }
        return null;
    }
};

export const saveSellingProfile = async (data: SellingProfileConfig) => {
    const response = await axios.post(`${API_URL}/api/settings/selling-profile`, data);
    return response.data;
};

export const getGlobalConfig = async (): Promise<{ trial_mode: boolean; environment: string }> => {
    const response = await axios.get(`${API_URL}/api/config`);
    return response.data;
};

export const getOnboardingStatus = async (): Promise<{ complete: boolean; migration_complete: boolean }> => {
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
    created_by_id?: string;
    creator_name?: string;
}

export interface AutopilotRule {
    id: string;
    type: 'keyword' | 'apollo_config';
    value: string;
    is_active: boolean;
    created_at: string;
    created_by_id: string;
    creator_name?: string;
}

export const getAutopilotRules = async (type?: string): Promise<AutopilotRule[]> => {
    const response = await axios.get(`${API_URL}/api/autopilot/rules`, { params: { type } });
    return response.data;
};

export const addAutopilotRule = async (data: Partial<AutopilotRule>) => {
    const response = await axios.post(`${API_URL}/api/autopilot/rules`, data);
    return response.data;
};

export const deleteAutopilotRule = async (id: string) => {
    const response = await axios.delete(`${API_URL}/api/autopilot/rules/${id}`);
    return response.data;
};

export const getCompetitors = async (): Promise<Competitor[]> => {
    const response = await axios.get(`${API_URL}/api/autopilot/competitors`);
    return response.data;
};

export const addCompetitor = async (data: { name?: string, linkedin_url: string }) => {
    const response = await axios.post(`${API_URL}/api/autopilot/competitors`, data);
    return response.data;
};

export const deleteCompetitor = async (id: string) => {
    const response = await axios.delete(`${API_URL}/api/autopilot/competitors/${id}`);
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
    website?: string;
    email?: string;
    email_verification_status?: string;
    company_id?: string;

    // Classification
    is_fit?: boolean;
    is_competitor?: boolean;
    is_decision_maker?: boolean;
    is_buy_signal?: boolean;
    is_strategic_seller?: boolean;
    fit_reasoning?: string;

    comment_history?: string; // JSON string
    source_posts?: string;    // JSON string
    interaction_history?: string; // JSON string
    last_interaction_at: string;
    profile_metadata?: string;
    latest_report_id?: string;
    rep_name?: string;
    touchpoint_count: number;
    outreach_status?: string;
    
    // New Intelligence Signals
    intent?: string;
    sentiment?: number;

    company?: {
        id: string;
        name: string;
        website?: string;
        industries?: string; // JSON string from backend
        employee_count?: number;
        revenue_estimate?: string;
        market_cap?: string;
        total_funding?: string;
        headquarters?: string;
        description?: string;
    };
}

export const getIdentifiedProfiles = async (
    skip: number = 0,
    limit: number = 100,
    search: string = "",
    status: string | string[] = "all",
    sort_by: string = "touchpoint_count",
    sort_order: string = "desc",
    date_start?: string,
    date_end?: string,
    source: string = "all",
): Promise<{ profiles: IdentifiedProfile[], total: number, tab_counts: Record<string, number> }> => {
    const response = await axios.get(`${API_URL}/api/competitor-analysis/profiles`, {
        params: { skip, limit, search, status, sort_by, sort_order, date_start, date_end, source }
    });
    return response.data;
};


export interface Activity {
    id: string;
    type: string;
    title: string;
    description?: string;
    metadata_json?: string;
    created_at: string;
}

export const fetchActivities = async (limit: number = 50): Promise<Activity[]> => {
    try {
        const response = await axios.get(`${API_URL}/api/activities?limit=${limit}`);
        return response.data;
    } catch (e) {
        console.error("Failed to fetch activities", e);
        return [];
    }
};

export interface NamespaceInfo {
    name: string;
    description: string;
    count: number;
}

export const fetchKnowledgeNamespaces = async (): Promise<NamespaceInfo[]> => {
    const response = await axios.get(`${API_URL}/api/knowledge/namespaces`);
    return response.data;
};

export const syncKnowledgeBase = async () => {
    const response = await axios.post(`${API_URL}/api/knowledge/sync-defaults`);
    return response.data;
};

export interface KnowledgeFile {
    id?: string;
    name: string;
    description?: string;
    path?: string;
    namespace?: string;
    storage_path?: string;
    asset_metadata?: Record<string, any>;
    size: number;
    modified: number | string;
}

export const fetchKnowledgeFiles = async (): Promise<KnowledgeFile[]> => {
    const response = await axios.get(`${API_URL}/api/knowledge/list-files`);
    return response.data.files;
};

export const ingestKnowledgeFile = async (filePath: string, namespace: string) => {
    const response = await axios.post(`${API_URL}/api/knowledge/ingest`, {
        file_path: filePath,
        namespace
    });
    return response.data;
};

export const fetchStrategy = async () => {
    const response = await axios.get(`${API_URL}/api/knowledge/strategy`);
    return response.data;
};

export const configureStrategy = async (config: any) => {
    const response = await axios.post(`${API_URL}/api/knowledge/configure-strategy`, config);
    return response.data;
};

export const deleteKnowledgeFile = async (assetId: string) => {
    const response = await axios.delete(`${API_URL}/api/knowledge/assets/${assetId}`);
    return response.data;
};

export const getKnowledgeFileContent = async (assetId: string) => {
    const response = await axios.get(`${API_URL}/api/knowledge/assets/${assetId}/content`);
    return response.data;
};

export const uploadKnowledgeFile = async (file: File, namespace: string) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('namespace', namespace);

    const response = await axios.post(`${API_URL}/api/knowledge/upload`, formData, {
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    });
    return response.data;
};
