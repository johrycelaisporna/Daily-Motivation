import os
import json
import urllib.request
from datetime import datetime, timedelta
import calendar

# Configuration
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")

CHANNELS = {
    "au": "au-contractors",
    "ph": "ph-entity-adaca",
}


# ─── Shared Utilities ────────────────────────────────────────────────

def post_to_slack(message, channel):
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
            print(f"  Slack API error ({channel}): {result.get('error', 'unknown')}")
        return result.get("ok")


def fmt_date(dt, include_year=False):
    if include_year:
        return dt.strftime("%B %d, %Y").replace(" 0", " ")
    return dt.strftime("%B %d").replace(" 0", " ")


def get_reminder_type():
    """
    Determine reminder type based on today's date.

    Returns: "cutoff", "weekly", or None
    Priority: cutoff > weekly (no double messages)
    """
    today = datetime.now()
    day = today.day
    last_day = calendar.monthrange(today.year, today.month)[1]

    # 5 days before the 20th → days 15–19
    if 1 <= (20 - day) <= 5:
        return "cutoff"

    # 5 days before the 5th → end of month + days 1–4
    if day >= (last_day - 4) or day <= 4:
        return "cutoff"

    # Friday
    if today.weekday() == 4:
        return "weekly"

    return None


def get_cutoff_context():
    """Build dynamic cutoff dates for both entities."""
    today = datetime.now()
    day = today.day
    month_name = today.strftime("%B")
    year = today.year
    last_day = calendar.monthrange(year, today.month)[1]

    if day <= 5:
        prev = today.replace(day=1) - timedelta(days=1)
        prev_month = prev.strftime("%B")
        prev_last = calendar.monthrange(prev.year, prev.month)[1]
        cutoff_start = f"{prev_month} 16"
        cutoff_end = f"{prev_month} {prev_last}"
        log_range = f"{prev_month} 16–{prev_last - 2}"
        approval_date = f"{month_name} 1"
        pay_date = f"{month_name} 5, {year}"
    elif day <= 20:
        cutoff_start = f"{month_name} 1"
        cutoff_end = f"{month_name} 15"
        log_range = f"{month_name} 1–13"
        approval_date = f"{month_name} 16"
        pay_date = f"{month_name} 20, {year}"
    else:
        cutoff_start = f"{month_name} 16"
        cutoff_end = f"{month_name} {last_day}"
        log_range = f"{month_name} 16–{last_day - 2}"
        next_m = today.replace(day=28) + timedelta(days=4)
        next_month = next_m.strftime("%B")
        approval_date = f"{next_month} 1"
        pay_date = f"{next_month} 5, {next_m.year}"

    return {
        "today": fmt_date(today),
        "today_full": fmt_date(today, include_year=True),
        "cutoff_start": cutoff_start,
        "cutoff_end": cutoff_end,
        "log_range": log_range,
        "approval_date": approval_date,
        "pay_date": pay_date,
    }


HARVEST_TASK_WARNING = (
    "⚠️ Harvest entries must include specific tasks — generalised "
    "descriptions like \"work\" or \"tasks\" will NOT be accepted. "
    "Break down your hours by actual tasks completed"
)

HARVEST_TASK_EXAMPLES = (
    "⚠️ Harvest entries must include specific tasks — do NOT log "
    "generalised descriptions like \"work\" or \"tasks.\" Break down "
    "your hours by actual tasks completed (e.g. \"client interview — "
    "John Smith,\" \"sourcing — Data Engineer role,\" \"admin — "
    "updating CRM records\")"
)


# ─── AU Contractors ──────────────────────────────────────────────────

def au_weekly():
    today = datetime.now()
    ws = fmt_date(today - timedelta(days=today.weekday()))
    we = fmt_date(today)
    return (
        "Weekly Harvest check-in 🌾\n\n"
        "Hi team, happy Friday! 👋\n\n"
        f"Quick reminder to update your Harvest time logs for this week "
        f"({ws}–{we}) before you wrap up for the day.\n\n"
        "Please make sure:\n"
        "• All hours are logged accurately for each day\n"
        "• Project/task assignments are correct\n"
        "• Any leave or OT taken this week is reflected\n"
        f"• {HARVEST_TASK_EXAMPLES}\n\n"
        "Keeping your logs up to date weekly makes cutoff time much smoother "
        "for everyone. Thank you! 🙌"
    )


def au_cutoff():
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
        f"• Harvest logs must be complete for {ctx['log_range']}\n"
        f"• {HARVEST_TASK_WARNING}\n\n"
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


# ─── PH Entity ───────────────────────────────────────────────────────

def ph_weekly():
    today = datetime.now()
    ws = fmt_date(today - timedelta(days=today.weekday()))
    we = fmt_date(today)
    return (
        "Weekly Harvest & SweldoMo Check-in 🌾\n\n"
        "Hi team, happy Friday! 👋\n\n"
        f"Quick reminder to update your time logs for this week "
        f"({ws}–{we}) before you wrap up for the day.\n\n"
        "Please make sure:\n"
        "• All Harvest hours are logged accurately for each day\n"
        "• SweldoMo logs are up to date (clock-in/clock-out entries)\n"
        "• Project and task assignments are correct\n"
        "• Any leave or OT taken this week is properly reflected\n"
        f"• {HARVEST_TASK_EXAMPLES}\n\n"
        "Keeping both Harvest and SweldoMo updated weekly makes cutoff "
        "time much smoother for everyone. Thank you! 🙌"
    )


def ph_cutoff():
    ctx = get_cutoff_context()
    return (
        "Reminder: Payroll cutoff logs – action needed @channel ⏰\n\n"
        "Hi team, good day! 👋\n\n"
        f"Please make sure to review and verify your time logs for the "
        f"current cutoff period ({ctx['cutoff_start']}–{ctx['cutoff_end']}) "
        f"today, {ctx['today']}.\n\n"
        "We kindly ask everyone to submit all of the following:\n"
        "• Filed OTs\n"
        "• Filed leaves\n"
        "• Adjustments — please check your logs for the cutoff\n"
        "• Any missing logs\n"
        f"• PLEASE MAKE SURE YOU HAVE YOUR SWELDO MO LOGS FROM "
        f"{ctx['log_range'].upper()}\n"
        f"• Harvest logs must be complete for {ctx['log_range']}\n"
        f"• {HARVEST_TASK_WARNING}\n\n"
        f"Deadline: On or before {ctx['today']}\n"
        f"(Approval of payroll will be submitted latest {ctx['approval_date']} "
        f"to make time for checking, approval, and bank transactions.)\n\n"
        "We appreciate your cooperation in helping ensure that payroll gets "
        f"processed and transferred on {ctx['pay_date']}.\n\n"
        "Let us know if you have any questions, thank you! 🙏"
    )


# ─── Main Runner ─────────────────────────────────────────────────────

def main():
    if not SLACK_BOT_TOKEN:
        raise ValueError("Missing SLACK_BOT_TOKEN env variable")

    reminder_type = get_reminder_type()

    if not reminder_type:
        print("ℹ️  No reminder scheduled for today — not a Friday or cutoff window.")
        return

    # Map: (entity) → (reminder_type) → (message builder, channel)
    reminders = {
        "AU": {
            "cutoff": (au_cutoff, CHANNELS["au"]),
            "weekly": (au_weekly, CHANNELS["au"]),
        },
        "PH": {
            "cutoff": (ph_cutoff, CHANNELS["ph"]),
            "weekly": (ph_weekly, CHANNELS["ph"]),
        },
    }

    label = "Cutoff" if reminder_type == "cutoff" else "Weekly"
    print(f"📅 Sending {label} reminders...\n")

    for entity, types in reminders.items():
        builder, channel = types[reminder_type]
        message = builder()
        if post_to_slack(message, channel):
            print(f"  ✅ {entity} — sent to #{channel}")
        else:
            print(f"  ❌ {entity} — failed for #{channel}")

    print("\n🏁 Done.")


if __name__ == "__main__":
    main()
