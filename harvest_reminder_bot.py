import os
import json
import urllib.request
from datetime import datetime
import calendar

# Configuration
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_CHANNEL = "au-contractors"

def post_to_slack(message, channel=SLACK_CHANNEL):
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

def get_cutoff_context():
    today = datetime.now()
    day = today.day
    month_name = today.strftime("%B")
    year = today.year
    last_day = calendar.monthrange(year, today.month)[1]

    if day <= 15:
        cutoff_start = f"{month_name} 1"
        cutoff_end = f"{month_name} 15"
        harvest_range = f"{month_name} 1–13"
    else:
        cutoff_start = f"{month_name} 16"
        cutoff_end = f"{month_name} {last_day}"
        harvest_range = f"{month_name} 16–{last_day}"

    today_str = today.strftime(f"{month_name} %d").lstrip("0")

    return {
        "month": month_name,
        "year": year,
        "today": today_str,
        "cutoff_start": cutoff_start,
        "cutoff_end": cutoff_end,
        "harvest_range": harvest_range
    }

def send_harvest_reminder():
    if not SLACK_BOT_TOKEN:
        raise ValueError("Missing SLACK_BOT_TOKEN env variable")

    ctx = get_cutoff_context()

    message = (
        "Reminder: Payroll cutoff logs – action needed @channel ⏰\n\n"
        "Hi team, good day 👋\n\n"
        f"Please review and verify your time logs for the current cutoff period "
        f"{ctx['cutoff_start']}–{ctx['cutoff_end']}. "
        f"Deadline is today, {ctx['today']}.\n\n"
        "What you must submit:\n"
        "• Filed OTs\n"
        "• Filed leaves\n"
        "• Any adjustments, please double-check your logs for this cutoff\n"
        "• Any missing logs\n"
        f"• Harvest logs must be complete for {ctx['harvest_range']}\n\n"
        "Why this matters:\n"
        "Payroll approval will be submitted shortly after cutoff to allow time for "
        "checking, approval, and bank processing.\n"
        f"Payroll will be processed on {ctx['month']} 20, {ctx['year']}.\n\n"
        "AU contractors reminder 🇦🇺:\n"
        f"Please submit your invoices for the {ctx['cutoff_start']}–"
        f"{ctx['cutoff_end']} cutoff today.\n\n"
        "Important:\n"
        "• No invoice, no payment\n"
        "• Late invoice submissions will roll over to the next payout cycle"
    )

    if post_to_slack(message):
        print("✅ Harvest reminder sent successfully")
    else:
        print("❌ Failed to send harvest reminder")

if __name__ == "__main__":
    send_harvest_reminder()
