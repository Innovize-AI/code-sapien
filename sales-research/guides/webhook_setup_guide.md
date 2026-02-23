# Webhook Integration Guide

This guide explains how to connect external services (HubSpot, Email Providers) to your local `sales-research` backend using Webhooks.

## prerequisites
- **Backend Running**: Ensure your backend is running on `http://localhost:8000`.
- **ngrok Installed**: You have `ngrok` installed (`ngrok --version` confirmed).

---

## 1. Expose Localhost to the Internet
Since HubSpot and Email providers cannot reach `localhost`, you must create a secure tunnel.

1.  **Start ngrok**:
    ```bash
    ngrok http 8000
    ```
2.  **Copy the Forwarding URL**: It will look like `https://<random-id>.ngrok-free.app`.
    *   *Note: This URL changes every time you restart ngrok unless you have a paid static domain.*

---

## 2. HubSpot Webhook Setup (CRM Update)
Trigger the research graph when a Contact property changes or a Deal stage moves.

### Step A: Create a Workflow in HubSpot
1.  Go to **Automation > Workflows**.
2.  Click **Create workflow** > **Contact-based** (or Deal-based).
3.  **Set Enrollment Triggers**:
    *   Example: `Lifecycle Stage` is known OR `Lead Status` changes to "Open".
4.  **Add Action**:
    *   Search for **"Trigger a Webhook"** (available in Operations Hub Pro/Enterprise) OR use "Send a Webhook" if available.
    *   **Method**: `POST`
    *   **Webhook URL**: `https://<your-ngrok-url>/api/webhooks/crm-updated`
    *   **Request Body**: Customize the JSON payload.
        ```json
        {
          "contact_email": "{{ contact.email }}",
          "change_type": "lifecycle_change",
          "deal_id": "{{ deal.hs_object_id }}" 
        }
        ```
        *(Note: HubSpot's default webhook payload sends everything. You might need a serverless function middleman if you can't customize the body in your tier, OR update `backend/routes/webhooks.py` to parse HubSpot's default format.)*

### Step B: Test
1.  Manually enroll a test contact in the workflow.
2.  Check your local terminal (where `uvicorn` is running) for the incoming request.

---

## 3. Email Webhook Setup (Inbound Parsing)
To trigger research when you receive an email (e.g., a reply from a lead), you need an **Inbound Parse** provider like SendGrid, Mailgun, or Postmark.

### Example: SendGrid Inbound Parse
1.  **Go to Settings > Inbound Parse**.
2.  **Add Host & URL**:
    *   **Subdomain**: `parse.yourdomain.com` (you must configure MX records).
    *   **Destination URL**: `https://<your-ngrok-url>/api/webhooks/email-received`
3.  **Validation**:
    *   SendGrid will POST a multipart/form-data request to your URL whenever an email hits that subdomain.
    *   *Note: The current `backend/routes/webhooks.py` expects JSON. You will need to update it to handle `Form` data if using SendGrid directly.*

### Simulating Email Locally (Easier)
Instead of setting up DNS/MX records for development, just use **cURL**:

```bash
curl -X POST "http://localhost:8000/api/webhooks/email-received" \
     -H "Content-Type: application/json" \
     -d '{
           "email_id": "target_lead@example.com",
           "subject": "Re: Meeting next week",
           "snippet": "I am not interested. Please stop contacting me."
         }'
```

---

## 4. Gmail Integration (Personal/GSuite)
Since Gmail doesn't have native webhooks, you have two options.

### Option A: Google Apps Script (Recommended - 2 mins)
This mimics a webhook by running a script inside your Gmail account that "pushes" emails to your webhook.

1.  **Go to**: [script.google.com](https://script.google.com/) > New Project.
2.  **Paste Code**:
    ```javascript
    function sendToWebhook(message) {
      // Replace with your ngrok URL
      var url = "https://YOUR-ID.ngrok-free.app/api/webhooks/email-received";
      var payload = {
        "email_id": message.getFrom(),
        "subject": message.getSubject(),
        "snippet": message.getPlainBody().substring(0, 500)
      };
      var options = {
        "method": "post",
        "contentType": "application/json",
        "payload": JSON.stringify(payload),
        "muteHttpExceptions": true
      };
      try { UrlFetchApp.fetch(url, options); } catch(e) {}
    }

    function processInbox() {
      // Search for Unread emails with Label "AI-Research"
      var threads = GmailApp.search("label:AI-Research is:unread");
      for (var i = 0; i < threads.length; i++) {
        var msgs = threads[i].getMessages();
        sendToWebhook(msgs[msgs.length - 1]); // Send latest
        threads[i].markRead(); // Prevent duplicate sending
      }
    }
    ```
3.  **Set Trigger**: Click **Triggers (Clock Icon)** > Add Trigger > `processInbox` > `Time-driven` > `Every minute`.

### Option B: Gmail API Pub/Sub (Advanced / "n8n Style")
This is the "official" enterprise method used by tools like n8n and Zapier, but requires significant infrastructure.

1.  **GCP Project**: Create a project in Google Cloud Console.
2.  **Enable APIs**: Enable Gmail API and Cloud Pub/Sub API.
3.  **Create Topic**: Create a Pub/Sub Topic (e.g., `gmail-push`).
4.  **Watch Endpoint**: Your backend must periodically call `POST /users/me/watch` to subscribe to updates.
5.  **Webhook Subscriber**: Configure a Pub/Sub Subscription to push events to your `https://.../webhooks` endpoint.

*Verdict: Use Option A for development/dogfooding. Use Option B only if building a SaaS product for others.*

---

## 5. Verification
1.  **Check Logs**: Look for "WEBHOOK: Starting targeted research..." in your backend logs.
2.  **Check Database**: The system should update the Lead Score and create a new Report entry.
