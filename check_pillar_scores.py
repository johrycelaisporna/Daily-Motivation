"""
check_pillar_scores.py

Reads every item on the Employee Performance Scorecard board, computes the
four pillar scores (Delivery, Quality, Communication, Collaboration) itself
from the raw Rating question columns, and adds the relevant label(s) to the
Coaching Areas column for any pillar scoring below 3. Any pillar at or above
3 has its label removed (so the column always reflects current state).

NOTE: This script does NOT read the Formula columns (Delivery Score, Quality
Score, etc). monday.com's API does not reliably return computed Formula
column values through the "text" field -- those are computed live by the
web app for display, not reliably stored/served on the backend. So instead
this script re-derives each pillar's average directly from the same Rating
columns the formulas use, using the exact same AVERAGE logic.

This exists because monday.com automations also cannot trigger off Formula
columns -- this script is the workaround, same pattern as
check_contract_expirations.py.

Run on a schedule (see the GitHub Actions workflow in this same folder)
or manually with: python check_pillar_scores.py
"""

import json
import os
import sys
import requests

MONDAY_API_URL = "https://api.monday.com/v2"
BOARD_ID = 18421022069  # Employee Performance Scorecard

COL_COACHING_AREAS = "dropdown_mm52873k"

# Each pillar's label -> the 4 (or 3) raw Rating columns that feed its average.
# These are the exact same columns each Formula column references.
PILLARS = {
    "Delivery": [
        "rating_mm523n5g",  # Sprint Completion
        "rating_mm52sgpb",  # Milestone Delivery
        "rating_mm52rjw5",  # Proactive Blocker Flagging
        "rating_mm52yd9p",  # Scope Change Handling
    ],
    "Quality": [
        "rating_mm522hyc",  # Bug Rate
        "rating_mm5294dz",  # Rework Rate
        "rating_mm525nzp",  # Code Review Pass Rate
        "rating_mm52nsg5",  # Client Reported Quality Issues
    ],
    "Communication and Ownership": [
        "rating_mm52kfz0",  # Response Time
        "rating_mm52swmf",  # Client Communication
        "rating_mm5296yw",  # Accountability Under Pressure
        "rating_mm52f9w3",  # Initiative Contributions
    ],
    "Collaboration": [
        "rating_mm52cedx",  # Peer Feedback
        "rating_mm52rv1x",  # Customer Relationship
        "rating_mm52n0gt",  # Knowledge Sharing
    ],
}

# Coaching Areas dropdown label IDs (from Coaching Areas -> Edit Labels on
# the board). Must match exactly what's configured there.
LABEL_IDS = {
    "Delivery": 1,
    "Quality": 2,
    "Communication and Ownership": 3,
    "Collaboration": 4,
}

THRESHOLD = 3.0


def get_token() -> str:
    token = os.environ.get("MONDAY_API_TOKEN")
    if not token:
        print("ERROR: MONDAY_API_TOKEN environment variable is not set.")
        sys.exit(1)
    return token


def run_query(query: str, variables: dict | None = None, token: str = "") -> dict:
    headers = {"Authorization": token, "Content-Type": "application/json"}
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = requests.post(MONDAY_API_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"Monday API error: {data['errors']}")
    return data["data"]


def all_rating_column_ids() -> list[str]:
    ids = []
    for cols in PILLARS.values():
        ids.extend(cols)
    return ids


def fetch_items(token: str) -> list[dict]:
    """Fetch all items with the raw rating values and current Coaching Areas."""
    column_ids = all_rating_column_ids() + [
        COL_COACHING_AREAS,
        COL_EMPLOYEE_NAME,
        COL_REVIEW_PERIOD,
        COL_REVIEW_DATE,
        COL_ROLE_TYPE,
        COL_COACHING_CASE_CREATED,
        COL_PIP_CREATED,
        COL_RECOGNITION_NOTIFIED,
        COL_LEADERSHIP_NOTIFIED,
        COL_SLACK_NOTIFIED,
    ]
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


def compute_labels(item: dict) -> list[str]:
    """Work out which Coaching Areas labels an item SHOULD have right now,
    by averaging the raw Rating columns ourselves (mirrors each Formula
    column's AVERAGE logic exactly)."""
    values = {cv["id"]: cv["text"] for cv in item["column_values"]}
    needed = []

    for label, rating_col_ids in PILLARS.items():
        scores = []
        for col_id in rating_col_ids:
            raw = values.get(col_id)
            if raw in (None, ""):
                continue  # question not answered yet, skip it
            try:
                scores.append(float(raw))
            except ValueError:
                continue

        if not scores:
            continue  # no ratings answered at all for this pillar yet

        average = sum(scores) / len(scores)
        if average < THRESHOLD:
            needed.append(label)

    return needed


def current_labels(item: dict) -> set[str]:
    values = {cv["id"]: cv["text"] for cv in item["column_values"]}
    text = values.get(COL_COACHING_AREAS) or ""
    return {t.strip() for t in text.split(",") if t.strip()}


def update_coaching_areas(item_id: str, labels: list[str], token: str) -> None:
    """Overwrite the Coaching Areas dropdown with exactly the given labels.

    The raw API expects {"ids": [<label id>, ...]}, not label text.
    """
    ids = [LABEL_IDS[label] for label in labels if label in LABEL_IDS]
    value = {"ids": ids}
    mutation = """
    mutation ($boardId: ID!, $itemId: ID!, $columnId: String!, $value: JSON!) {
      change_column_value(
        board_id: $boardId,
        item_id: $itemId,
        column_id: $columnId,
        value: $value
      ) {
        id
      }
    }
    """
    variables = {
        "boardId": str(BOARD_ID),
        "itemId": str(item_id),
        "columnId": COL_COACHING_AREAS,
        "value": json.dumps(value),
    }
    run_query(mutation, variables, token)


SCORECARD_URL_TEMPLATE = "https://adacahq.monday.com/boards/{board}/pulses/{item}"

COL_EMPLOYEE_NAME = "text_mm52ps"
COL_REVIEW_PERIOD = "timerange_mm52jpf9"
COL_REVIEW_DATE = "date_mm52nh8r"
COL_ROLE_TYPE = "color_mm52q72s"
COL_COACHING_CASE_CREATED = "boolean_mm5364ka"
COL_PIP_CREATED = "boolean_mm53rre1"
COL_RECOGNITION_NOTIFIED = "boolean_mm53ctmg"
COL_LEADERSHIP_NOTIFIED = "boolean_mm53vj1h"
COL_SLACK_NOTIFIED = "boolean_mm53qzm0"

COACHING_BOARD_ID = 18421197053
PIP_BOARD_ID = 18421197058

RECOGNITION_THRESHOLD = 5.0     # Overall Score == 5 -> Recognition
LEADERSHIP_LOW = 4.0            # Overall Score 4.0-4.99 -> Leadership/Upskilling
COACHING_LOW = 3.0   # Overall Score >= this and < 4.0 -> Coaching Case
COACHING_HIGH = 4.0
PIP_THRESHOLD = 3.0  # Overall Score < this -> PIP


def overall_score(item: dict, values: dict) -> float | None:
    """Average of the 4 pillar averages -- mirrors the Overall Score formula."""
    pillar_averages = []
    for rating_col_ids in PILLARS.values():
        scores = []
        for col_id in rating_col_ids:
            raw = values.get(col_id)
            if raw in (None, ""):
                continue
            try:
                scores.append(float(raw))
            except ValueError:
                continue
        if scores:
            pillar_averages.append(sum(scores) / len(scores))
    if not pillar_averages:
        return None
    return sum(pillar_averages) / len(pillar_averages)


def create_coaching_case(item: dict, values: dict, needed_labels: list[str], score: float, token: str) -> None:
    employee = values.get(COL_EMPLOYEE_NAME) or item["name"]
    review_period = values.get(COL_REVIEW_PERIOD) or ""
    source_url = SCORECARD_URL_TEMPLATE.format(board=BOARD_ID, item=item["id"])

    column_values = {
        "text_mm5330cv": employee,
        "text_mm53yw1r": review_period,
        "numeric_mm53jkg9": str(round(score, 2)),
        "link_mm53f1dt": {"url": source_url, "text": "Open review"},
    }
    if needed_labels:
        column_values["dropdown_mm53dhkh"] = {"labels": needed_labels}

    mutation = """
    mutation ($boardId: ID!, $itemName: String!, $columnValues: JSON!) {
      create_item(board_id: $boardId, item_name: $itemName, column_values: $columnValues, create_labels_if_missing: true) {
        id
      }
    }
    """
    variables = {
        "boardId": str(COACHING_BOARD_ID),
        "itemName": f"{employee} — Coaching Case",
        "columnValues": json.dumps(column_values),
    }
    run_query(mutation, variables, token)
    flag_scorecard_item(item["id"], COL_COACHING_CASE_CREATED, token)


def create_pip(item: dict, values: dict, needed_labels: list[str], score: float, token: str) -> None:
    employee = values.get(COL_EMPLOYEE_NAME) or item["name"]
    review_date = values.get(COL_REVIEW_DATE) or ""
    source_url = SCORECARD_URL_TEMPLATE.format(board=BOARD_ID, item=item["id"])

    column_values = {
        "text_mm53f4qw": employee,
        "numeric_mm53h2we": str(round(score, 2)),
        "link_mm53bgjf": {"url": source_url, "text": "Open review"},
    }
    if needed_labels:
        column_values["dropdown_mm536yz3"] = {"labels": needed_labels}
    if review_date:
        column_values["date_mm53whmp"] = {"date": review_date}

    mutation = """
    mutation ($boardId: ID!, $itemName: String!, $columnValues: JSON!) {
      create_item(board_id: $boardId, item_name: $itemName, column_values: $columnValues, create_labels_if_missing: true) {
        id
      }
    }
    """
    variables = {
        "boardId": str(PIP_BOARD_ID),
        "itemName": f"{employee} — PIP",
        "columnValues": json.dumps(column_values),
    }
    run_query(mutation, variables, token)
    flag_scorecard_item(item["id"], COL_PIP_CREATED, token)


def classify(score: float) -> str:
    """Mirrors the Classification formula -- computed here in Python since
    formula columns can't be read reliably via the API."""
    if score >= 5:
        return "Replicate"
    if score >= 4:
        return "Leadership / Upskilling"
    if score >= 3:
        return "Targeted Coaching"
    return "Performance Improvement Plan"


def post_to_slack(message: str) -> None:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("  WARNING: SLACK_WEBHOOK_URL not set, skipping Slack post.")
        return
    resp = requests.post(webhook_url, json={"text": message}, timeout=15)
    if resp.status_code != 200:
        print(f"  WARNING: Slack post failed ({resp.status_code}): {resp.text}")


def post_update(item_id: str, message: str, token: str) -> None:
    """Post an Update (comment) on the scorecard item -- this notifies
    whoever is subscribed to it (typically the Reviewer)."""
    mutation = """
    mutation ($itemId: ID!, $body: String!) {
      create_update(item_id: $itemId, body: $body) {
        id
      }
    }
    """
    variables = {"itemId": str(item_id), "body": message}
    run_query(mutation, variables, token)


def flag_scorecard_item(item_id: str, checkbox_col: str, token: str) -> None:
    """Mark a checkbox true on the scorecard item so we never duplicate-create."""
    mutation = """
    mutation ($boardId: ID!, $itemId: ID!, $columnId: String!, $value: JSON!) {
      change_column_value(
        board_id: $boardId,
        item_id: $itemId,
        column_id: $columnId,
        value: $value
      ) {
        id
      }
    }
    """
    variables = {
        "boardId": str(BOARD_ID),
        "itemId": str(item_id),
        "columnId": checkbox_col,
        "value": json.dumps({"checked": "true"}),
    }
    run_query(mutation, variables, token)


def main() -> None:
    token = get_token()
    items = fetch_items(token)
    print(f"Checked {len(items)} item(s) on board {BOARD_ID}")

    for item in items:
        values = {cv["id"]: cv["text"] for cv in item["column_values"]}

        needed = set(compute_labels(item))
        existing = current_labels(item)

        if needed != existing:
            update_coaching_areas(item["id"], sorted(needed), token)
            print(f"  [{item['name']}] Coaching Areas: {sorted(existing)} -> {sorted(needed)}")
        else:
            print(f"  [{item['name']}] Coaching Areas unchanged ({sorted(existing)})")

        score = overall_score(item, values)
        if score is None:
            continue  # no ratings answered yet at all, nothing to classify

        already_slack_notified = bool(values.get(COL_SLACK_NOTIFIED))
        if not already_slack_notified:
            employee = values.get(COL_EMPLOYEE_NAME) or item["name"]
            role = values.get(COL_ROLE_TYPE) or "—"
            classification = classify(score)
            source_url = SCORECARD_URL_TEMPLATE.format(board=BOARD_ID, item=item["id"])

            lines = [
                f"*New performance review submitted*",
                f"*Employee:* {employee}  |  *Role:* {role}",
                f"*Overall Score:* {score:.2f}  |  *Classification:* {classification}",
            ]
            if needed:
                lines.append(f"*Coaching Areas flagged:* {', '.join(sorted(needed))}")
            if score >= RECOGNITION_THRESHOLD:
                lines.append("🎉 Perfect score — candidate for Recognition.")
            elif LEADERSHIP_LOW <= score < RECOGNITION_THRESHOLD:
                lines.append("⭐ Candidate for Leadership / Upskilling.")
            elif score < PIP_THRESHOLD:
                lines.append("🚨 Below 3.0 — a PIP has been created.")
            elif COACHING_LOW <= score < COACHING_HIGH:
                lines.append("📋 In Coaching range — a Coaching Case has been created.")
            lines.append(f"<{source_url}|Open review>")

            post_to_slack("\n".join(lines))
            flag_scorecard_item(item["id"], COL_SLACK_NOTIFIED, token)
            print(f"  [{item['name']}] Posted Slack summary (score {score:.2f})")

        already_coaching = bool(values.get(COL_COACHING_CASE_CREATED))
        already_pip = bool(values.get(COL_PIP_CREATED))
        already_recognized = bool(values.get(COL_RECOGNITION_NOTIFIED))
        already_leadership = bool(values.get(COL_LEADERSHIP_NOTIFIED))

        if score >= RECOGNITION_THRESHOLD and not already_recognized:
            flag_scorecard_item(item["id"], COL_RECOGNITION_NOTIFIED, token)
            print(f"  [{item['name']}] Flagged Recognition (score {score:.2f}) — covered in Slack post above")

        elif LEADERSHIP_LOW <= score < RECOGNITION_THRESHOLD and not already_leadership:
            flag_scorecard_item(item["id"], COL_LEADERSHIP_NOTIFIED, token)
            print(f"  [{item['name']}] Flagged Leadership (score {score:.2f}) — covered in Slack post above")

        if COACHING_LOW <= score < COACHING_HIGH and not already_coaching:
            create_coaching_case(item, values, sorted(needed), score, token)
            print(f"  [{item['name']}] Created Coaching Case (score {score:.2f})")
        elif score < PIP_THRESHOLD and not already_pip:
            create_pip(item, values, sorted(needed), score, token)
            print(f"  [{item['name']}] Created PIP (score {score:.2f})")

    print("Done.")


if __name__ == "__main__":
    main()
