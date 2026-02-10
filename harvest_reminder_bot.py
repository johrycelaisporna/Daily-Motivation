import os
import json
import urllib.request

# Configuration
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_CHANNEL = "au-contractors"

def post_to_slack(message, channel=SLACK_CHANNEL):
    """Post message to Slack"""
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "channel": channel,
        "text": message,
        "unfurl_links": False
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=headers
    )

    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode("utf-8"))
        return result.get("ok")

def send_harvest_reminder():
    if not SLACK_BOT_TOKEN:
        raise ValueError("Missing SLACK_BOT_TOKEN env variable")

    message = (
        "Hey team 👋\n"
        "Payroll countdown has started ⏳\n\n"
        "Quick check:\n"
        "• Harvest time updated with clear task details 📝\n"
        "• Invoices prepared and ready to submit 💸\n\n"
        "Do this now, future you will be grateful 😄"
    )

    if post_to_slack(message):
        print("✅ Harvest reminder sent")
    else:
        print("❌ Failed to send harvest reminder")

if __name__ == "__main__":
    send_harvest_reminder()
