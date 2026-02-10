import os
import requests

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def send_harvest_reminder():
    if not SLACK_WEBHOOK_URL:
        raise ValueError("Missing SLACK_WEBHOOK_URL env variable")

    payload = {
        "channel": "#au-contractors",
        "text": (
            "Hey team 👋\n"
            "Payroll countdown has started ⏳\n\n"
            "Quick check:\n"
            "• Harvest time updated with clear task details 📝\n"
            "• Invoices prepared and ready to submit 💸\n\n"
            "Do this now, future you will be grateful 😄"
        )
    }

    response = requests.post(
        SLACK_WEBHOOK_URL,
        json=payload,
        timeout=10
    )

    response.raise_for_status()

if __name__ == "__main__":
    send_harvest_reminder()
