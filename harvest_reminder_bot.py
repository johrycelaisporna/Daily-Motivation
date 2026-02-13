import os
import json
import urllib.request
from datetime import datetime, timedelta
import calendar

# Configuration
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_CHANNEL = "au-contractors"


def post_to_slack(message, channel=SLACK_CHANNEL):
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {"channel": channel, "text": message, "unfurl_links": False}
    req = urllib.request.Request(
        url, data=json.dumps(data).encode("utf-8"), headers=headers
    )
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode("utf-8"))
        if not result.get("ok"):
            print(f"Slack API error: {result.get('error', 'unknown')}")
        return result.get("ok")


def get_cutoff_context():
    """Build context for the upcoming cutoff date (5th or 20th)."""
    today = datetime.now()
    day = today.day
    month_name = today.strftime("%B")
    year = today.year
    last_day = calendar.monthrange(year, today.month)[1]

    # Determine which cutoff we're approaching
    if day <= 5:
        # Approaching the 5th — cutoff covers prev month 16–end
        prev = today.replace(day=1) - timedelta(days=1)
        prev_month = prev.strftime("%B")
        prev_last = calendar.monthrange(prev.year, prev.month)[1]
        cutoff_start = f"{prev_month} 16"
        cutoff_end = f"{prev_month} {prev_last}"
        harvest_range = f"{prev_month} 16–{prev_last}"
        pay_date = f"{month_name} 5, {year}"
    elif day <= 20:
        # Approaching the 20th — cutoff covers current month 1–15
        cutoff_start = f"{month_name} 1"
        cutoff_end = f"{month_name} 15"
        harvest_range = f"{month_name} 1–13"
        pay_date = f"{month_name} 20, {year}"
    else:
        # Past the 20th, approaching next month's 5th
        cutoff_start = f"{month_name} 16"
        cutoff_end = f"{month_name} {last_day}"
        harvest_range = f"{month_name} 16–{last_day}"
        next_m = today.replace(day=28) + timedelta(days=4)
        next_month = next_m.strftime("%B")
        pay_date = f"{next_month} 5, {next_m.year}"

    today_str = today.strftime(f"%B %d, %Y").replace(" 0", " ")
    return {
        "month": month_name,
        "year": year,
        "today": today_str,
        "cutoff_start": cutoff_start,
        "cutoff_end": cutoff_end,
        "harvest_range": harvest_range,
        "pay_date": pay_date,
    }


def get_reminder_type():
    """
    Determine which reminder to send based on today's date.

    Priority:
      1. Cutoff reminder — fires 5 days before the 5th and 5 days before the 20th
         (i.e. on the 15th and on the last day of prev month minus 4 → ~1st of month area)
      2. Weekly reminder — fires every Friday as a general Harvest nudge

    Returns: "cutoff", "weekly", or None
    """
    today = datetime.now()
    day = today.day
    year = today.year
    month = today.month
    last_day = calendar.monthrange(year, month)[1]

    # 5 days before the 20th = 15th
    # 5 days before the 5th = last day of prev month - 4 ... through the 1st
    # We define "5 days before" as days 15–19 (before the 20th) and
    # (last_day - 4) through last_day + days 1–4 (before the 5th)

    days_before_20th = 20 - day  # positive if before the 20th
    if 1 <= days_before_20th <= 5:
        return "cutoff"

    # Days before the 5th (could be end of current month or start of next)
    if day >= (last_day - 4):
        # e.g. last_day=31, fires on 27,28,29,30,31
        return "cutoff"
    if day <= 4:
        # days 1–4 are also within 5 days before the 5th
        return "cutoff"

    # Friday = weekday 4
    if today.weekday() == 4:
        return "weekly"

    return None


def build_weekly_reminder():
    """Lighter end-of-week nudge to keep Harvest logs updated."""
    today = datetime.now()
    week_start = (today - timedelta(days=today.weekday())).strftime("%B %d").replace(" 0", " ")
    week_end = today.strftime("%B %d").replace(" 0", " ")

    return (
        "Weekly Harvest check-in 🌾\n\n"
        "Hi team, happy Friday! 👋\n\n"
        f"Quick reminder to update your Harvest time logs for this week "
        f"({week_start}–{week_end}) before you wrap up for the day.\n\n"
        "Please make sure:\n"
        "• All hours are logged accurately for each day\n"
        "• Project/task assignments are correct\n"
        "• Any leave or OT taken this week is reflected\n\n"
        "Keeping your logs up to date weekly makes cutoff time much smoother "
        "for everyone. Thank you! 🙌"
    )


def build_cutoff_reminder():
    """Detailed payroll cutoff reminder — 5 days before the 5th and 20th."""
    ctx = get_cutoff_context()

    return (
        "Reminder: Payroll cutoff logs – action needed @channel ⏰\n\n"
        "Hi team, good day 👋\n\n"
        f"Please review and verify your time logs for the current cutoff period "
        f"{ctx['cutoff_start']}–{ctx['cutoff_end']}. "
        f"Deadline is approaching — today is {ctx['today']}.\n\n"
        "What you must submit:\n"
        "• Filed OTs\n"
        "• Filed leaves\n"
        "• Any adjustments — please double-check your logs for this cutoff\n"
        "• Any missing logs\n"
        f"• Harvest logs must be complete for {ctx['harvest_range']}\n\n"
        "Why this matters:\n"
        "Payroll approval will be submitted shortly after cutoff to allow time for "
        "checking, approval, and bank processing.\n"
        f"Payroll will be processed on {ctx['pay_date']}.\n\n"
        "AU contractors reminder 🇦🇺:\n"
        f"Please submit your invoices for the {ctx['cutoff_start']}–"
        f"{ctx['cutoff_end']} cutoff.\n\n"
        "Important:\n"
        "• No invoice, no payment\n"
        "• Late invoice submissions will roll over to the next payout cycle"
    )


def send_harvest_reminder():
    if not SLACK_BOT_TOKEN:
        raise ValueError("Missing SLACK_BOT_TOKEN env variable")

    reminder_type = get_reminder_type()

    if reminder_type == "cutoff":
        message = build_cutoff_reminder()
        label = "Cutoff"
    elif reminder_type == "weekly":
        message = build_weekly_reminder()
        label = "Weekly"
    else:
        print("ℹ️  No reminder scheduled for today — not a Friday or cutoff window.")
        return

    if post_to_slack(message):
        print(f"✅ {label} Harvest reminder sent successfully")
    else:
        print(f"❌ Failed to send {label} Harvest reminder")


if __name__ == "__main__":
    send_harvest_reminder()
