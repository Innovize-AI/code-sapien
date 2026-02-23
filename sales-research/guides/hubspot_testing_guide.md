# HubSpot Integration Testing Guide

Follow these steps to set up your HubSpot environment and verify the integration features (Champions, Lost Deals, Competitor Discovery, and Bidirectional Sync).

## 1. Setup HubSpot Private App
To get an access token, you must create a Private App in your HubSpot portal:
1.  Go to **Settings** > **Integrations** > **Private Apps**.
2.  Click **Create a private app**.
3.  Under the **Scopes** tab, select the following:
    *   `crm.objects.contacts.read`
    *   `crm.objects.deals.read`
    *   `crm.objects.notes.write`
    *   `crm.objects.companies.read`
4.  Click **Create app** and copy the **Access Token**.

## 2. Seed Dummy Data
Create the following records in HubSpot to test specific logic:

### Test Case A: The "Past Champion"
Goal: Verify the AI identifies a lead who previously bought from you.
1.  **Create Contact**:
    *   **First Name**: Jane
    *   **Last Name**: Champion
    *   **Email**: `jane@previous.com`
    *   **LinkedIn URL**: `https://www.linkedin.com/in/jane-champion-test` (Add this as a custom property or ensure it's mapped).
2.  **Create Deal**:
    *   **Deal Name**: Previous Growth Deal
    *   **Stage**: `Closed Won`
    *   **Association**: Associate this deal with Jane Champion.

### Test Case B: The "Lost Deal" & Competitor Discovery
Goal: Verify AI knows why a deal was lost and identifies a competitor.
1.  **Create Contact**:
    *   **First Name**: Bob
    *   **Last Name**: Lost
    *   **Email**: `bob@targetcorp.com`
2.  **Create Deal**:
    *   **Deal Name**: Target Corp Expansion
    *   **Stage**: `Closed Lost`
    *   **Closed Lost Reason**: "User preferred **Clay** because of their native waterfall enrichment."
    *   **Association**: Associate this deal with Bob Lost.

## 3. Verify Features
Once the data is in HubSpot:
1.  **Configure Token**: Go to the **Integrations** page in our app and paste your token. Enable **Automated CRM Sync**.
2.  **Trigger Sync**: The sync runs every 12 hours. To trigger it immediately for testing, run this command in your terminal:
    ```bash
    cd sales-research/backend && python3 -c "from scheduler import hubspot_sync_job; import asyncio; asyncio.run(hubspot_sync_job())"
    ```
3.  **Check Research Context**:
    *   Run a research search for `jane@previous.com`.
    *   The AI should mention that Jane is a **Champion** from "Previous Growth Deal".
4.  **Check Bidirectional Sync**:
    *   Run research for `bob@targetcorp.com`.
    *   After completion, check Bob's contact record in HubSpot. You should see a new **Note** containing the research summary.
5.  **Check Competitor List**:
    *   Verify that "**Clay**" has been automatically added to your monitored competitors list (if not already present).
