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
        COL_COACHING_CASE_CREATED,
        COL_PIP_CREATED,
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
COL_COACHING_CASE_CREATED = "boolean_mm5364ka"
COL_PIP_CREATED = "boolean_mm53rre1"

COACHING_BOARD_ID = 18421197053
PIP_BOARD_ID = 18421197058

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
        "dropdown_mm53dhkh": {"labels": needed_labels},
        "numeric_mm53jkg9": str(round(score, 2)),
        "link_mm53f1dt": {"url": source_url, "text": "Open review"},
    }
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
        "dropdown_mm536yz3": {"labels": needed_labels},
        "link_mm53bgjf": {"url": source_url, "text": "Open review"},
    }
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

        already_coaching = bool(values.get(COL_COACHING_CASE_CREATED))
        already_pip = bool(values.get(COL_PIP_CREATED))

        if COACHING_LOW <= score < COACHING_HIGH and not already_coaching:
            create_coaching_case(item, values, sorted(needed), score, token)
            print(f"  [{item['name']}] Created Coaching Case (score {score:.2f})")
        elif score < PIP_THRESHOLD and not already_pip:
            create_pip(item, values, sorted(needed), score, token)
            print(f"  [{item['name']}] Created PIP (score {score:.2f})")

    print("Done.")


if __name__ == "__main__":
    main()
