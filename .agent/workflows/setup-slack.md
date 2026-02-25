---
description: SOP for setting up Slack notifications and interactions for Staging and Production
---

# Slack Setup SOP (Staging & Production) 💬

To enable Slack notifications (alerts) and interactions (buttons) for your Research tool, follow these steps for **both** environments.

> [!NOTE]
> It is highly recommended to create **two separate Slack Apps** (e.g., "Glial - Staging" and "Glial - Production") so that interactive buttons work correctly in both environments.

## 1. Create Slack Apps
1. Go to the [Slack App Dashboard](https://api.slack.com/apps).
2. Click **Create New App** -> **From Scratch**.
3. Name it `Sales Research (Staging)` and `Sales Research (Prod)`.
4. Select your workspace.

## 2. Setup Notifications (Webhooks) 🔔
1. In the Slack App settings, go to **Incoming Webhooks**.
2. Toggle **Activate Incoming Webhooks** to **On**.
3. Click **Add New Webhook to Workspace**.
4. Select the channel where you want alerts (e.g., `#alerts-staging` or `#alerts-prod`).
5. Copy the **Webhook URL**.

## 3. Setup Interactions (Buttons) 🖱️
1. In the Slack App settings, go to **Interactivity & Shortcuts**.
2. Toggle **Interactivity** to **On**.
3. Set the **Request URL** for each app:
   - **Staging**: `https://[your-staging-backend-url]/slack/interactions`
   - **Production**: `https://[your-prod-backend-url]/slack/interactions`
4. Click **Save Changes**.

## 4. Final Bot Permissions
1. Go to **OAuth & Permissions**.
2. Ensure the following **Bot Token Scopes** are added (they usually are automatically added via the steps above):
   - `incoming-webhook`
   - `chat:write`
3. If you added any new scopes, click **Reinstall to Workspace** at the top of the page.

## 5. Configure the Backend ⚙️
Once you have the Webhook URLs, you need to save them in the database for each environment.

### Option A: Via UI (Recommended)
1. Log into your Sales Research Dashboard (Staging or Prod).
2. Go to **Settings** -> **Integrations**.
3. Paste the respective Slack Webhook URL into the **Slack Webhook URL** field.
4. Click **Save**.

### Option B: Via SQL (Emergency/Provisioning)
Run this in your database (e.g., via Supabase SQL Editor) for the correct schema:
```sql
UPDATE organization_settings 
SET slack_webhook_url = 'https://hooks.slack.com/services/...'
LIMIT 1;
```

---

## Verification ✅
1. Trigger a research task or high-potential lead event.
2. Check your Slack channel for the notification.
3. Try clicking the **"Analyze Lead"** button in Slack to verify interactivity is working!
