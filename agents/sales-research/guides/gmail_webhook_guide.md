# Gmail "Native" Webhook (via Apps Script)

Gmail does not have a simple "Webhook URL" field. However, you can use **Google Apps Script** (free, built-in) to watch for specific emails and forward them to your webhook instantly.

## Step 1: Create the Script
1.  Go to [script.google.com](https://script.google.com/) and click **"New Project"**.
2.  Paste the following code (replace `YOUR_NGROK_URL`):

```javascript
// --- CONFIGURATION ---
var WEBHOOK_URL = "https://<YOUR-NGROK-ID>.ngrok-free.app/api/webhooks/email-received";
var SEARCH_QUERY = "label:Research-Target is:unread"; // Only process unread emails with this label
// ---------------------

function processEmails() {
  // Search for relevant threads
  var threads = GmailApp.search(SEARCH_QUERY);
  
  for (var i = 0; i < threads.length; i++) {
    var messages = threads[i].getMessages();
    var lastMessage = messages[messages.length - 1]; // Get latest reply
    
    var payload = {
      "email_id": lastMessage.getFrom(),
      "subject": lastMessage.getSubject(),
      "snippet": lastMessage.getPlainBody().substring(0, 1000) // First 1000 chars of body
    };

    var options = {
      "method": "post",
      "contentType": "application/json",
      "payload": JSON.stringify(payload),
      "muteHttpExceptions": true
    };

    try {
      UrlFetchApp.fetch(WEBHOOK_URL, options);
      Logger.log("Forwarded: " + lastMessage.getSubject());
      
      // Mark as read to prevent duplicates
      threads[i].markRead(); 
      
      // Optional: Add "Processed" label
      // threads[i].addLabel(GmailApp.getUserLabelByName("Processed"));
    } catch (e) {
      Logger.log("Error: " + e.toString());
    }
  }
}
```

## Step 2: Set up the Trigger (Run Automatically)
1.  Click the **Clock Icon** (Triggers) on the left sidebar.
2.  Click **+ Add Trigger**.
3.  Configure:
    *   **Function**: `processEmails`
    *   **Event Source**: `Time-driven`
    *   **Type**: `Minutes timer` -> `Every minute`
4.  Click **Save** and grant permissions (Advanced > Go to Project (Unsafe) > Allow).

## Step 3: Use It
1.  In Gmail, create a Label called **"Research-Target"**.
2.  Create a Filter: "If email is from specific lead -> Apply Label: Research-Target".
3.  When a matching email arrives, the script will pick it up within 1 minute, send it to your local webhook, and mark it as read.

This gives you a fully automated "Gmail Webhook" without any external paid tools like Zapier.
