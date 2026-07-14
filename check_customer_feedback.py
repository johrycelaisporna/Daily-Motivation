"""
check_customer_feedback.py

Watches the Customer Feedback Form board on monday.com. Every time a new
submission comes in, posts a summary to Slack and marks it as notified so
it's never posted twice.

This is a standalone bot -- separate repo, separate Slack channel from the
Employee Performance Scorecard bots.

Run on a schedule (see the GitHub Actions workflow in this same folder)
or manually with: python check_customer_feedback.py
"""

import json
import os
import sys
import requests

MONDAY_API_URL = "https://api.monday.com/v2"
SLACK_CHANNEL = "#adaca-excellence-customer-feedback"

BOARD_ID = 18420811704  # Adaca Excellence Framework / Customer Feedback Form
NOTIFIED_COL = "boolean_mm58zywk"  # Slack Notified checkbox

# (column_id, label shown in the Slack message)
FIELDS = [
    ("short_textxbl07oqh", "Feedback for"),
    ("short_textynhjo55s", "Submitted by"),
    ("single_selectzkfmsg8", "Stage"),
    ("single_selectvzlxbyy", "Area to focus on"),
]

BOARD_URL_TEMPLATE = "https://adacahq.monday.com/boards/{board}/pulses/{item}"


def get_monday_token() -> str:
    token = os.environ.get("MONDAY_API_TOKEN")
    if not token:
        print("ERROR: MONDAY_API_TOKEN environment variable is not set.")
        sys.exit(1)
    return token


def run_query(query: str, variables: dict, token: str) -> dict:
    headers = {"Authorization": token, "Content-Type": "application/json"}
    resp = requests.post(
        MONDAY_API_URL,
        json={"query": query, "variables": variables},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"Monday API error: {data['errors']}")
    return data["data"]


def fetch_items(token: str) -> list[dict]:
    column_ids = [NOTIFIED_COL] + [f[0] for f in FIELDS]
    query = """
    query ($boardId: [ID!], $columnIds: [String!]) {
      boards(ids: $boardId) {
        items_page(limit: 500) {
          items {
            id
            name
            column_values(ids: $columnIds) {
              id
              text
            }
          }
        }
      }
    }
    """
    variables = {"boardId": [str(BOARD_ID)], "columnIds": column_ids}
    data = run_query(query, variables, token)
    return data["boards"][0]["items_page"]["items"]


def flag_notified(item_id: str, token: str) -> None:
    mutation = """
    mutation ($boardId: ID!, $itemId: ID!, $columnId: String!, $value: JSON!) {
      change_column_value(
        board_id: $boardId, item_id: $itemId, column_id: $columnId, value: $value
      ) { id }
    }
    """
    variables = {
        "boardId": str(BOARD_ID),
        "itemId": str(item_id),
        "columnId": NOTIFIED_COL,
        "value": json.dumps({"checked": "true"}),
    }
    run_query(mutation, variables, token)


def post_to_slack(message: str) -> bool:
    """Returns True if the message was actually sent. Uses the Slack Web API
    (chat.postMessage) with a Bot Token, not an incoming webhook."""
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    if not bot_token:
        print("  WARNING: SLACK_BOT_TOKEN not set, skipping Slack post.")
        return False

    resp = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        json={"channel": SLACK_CHANNEL, "text": message},
        timeout=15,
    )
    data = resp.json()
    if not data.get("ok"):
        print(f"  WARNING: Slack post failed: {data.get('error')}")
        return False
    return True


def main() -> None:
    token = get_monday_token()
    items = fetch_items(token)
    print(f"Checked {len(items)} item(s) on board {BOARD_ID}")

    for item in items:
        values = {cv["id"]: cv["text"] for cv in item["column_values"]}

        if bool(values.get(NOTIFIED_COL)):
            continue  # already notified, skip

        source_url = BOARD_URL_TEMPLATE.format(board=BOARD_ID, item=item["id"])
        lines = ["*New Customer Feedback Form submission*"]
        for col_id, label in FIELDS:
            value = values.get(col_id)
            if value:
                lines.append(f"*{label}:* {value}")
        lines.append(f"<{source_url}|Open submission>")

        sent = post_to_slack("\n".join(lines))
        if sent:
            flag_notified(item["id"], token)
            print(f"  [{item['name']}] Posted Slack notification")
        else:
            print(f"  [{item['name']}] Slack post FAILED, will retry next run")

    print("Done.")


if __name__ == "__main__":
    main()
