import axios from 'axios';

const API_URL = 'http://localhost:8000';

export interface LeadData {
    linkedin_url: string;
    website: string;
    email?: string;
    lead_source?: string;
    download_marketing_material?: boolean;
    demo_requested?: boolean;
    referral_partner_introduction?: boolean;
    project_urgency?: number; // 1: Low, 2: Medium, 3: High
}

export const generateResearch = async (
    data: LeadData,
    onUpdate?: (status: string) => void
) => {
    const params = new URLSearchParams();
    params.append('linkedin_url', data.linkedin_url);
    params.append('website', data.website);
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

    if (reader) {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            // Split by double newline as per SSE spec
            const parts = chunk.split('\n\n');

            for (const part of parts) {
                if (part.startsWith('data: ')) {
                    const jsonStr = part.replace('data: ', '');
                    try {
                        const data = JSON.parse(jsonStr);
                        if (data.status === 'Done') {
                            finalResult = data.result;
                        } else if (onUpdate) {
                            onUpdate(data.status);
                        }
                    } catch (e) {
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
    provider?: 'tavily' | 'apollo';
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
