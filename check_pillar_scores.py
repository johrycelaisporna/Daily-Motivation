"""
check_pillar_scores.py

Reads every item on the Employee Performance Scorecard board, checks the
four pillar scores (Delivery, Quality, Communication, Collaboration), and
adds the relevant label(s) to the Coaching Areas column for any pillar
scoring below 3. Any pillar at or above 3 has its label removed (so the
column always reflects current state, not stale flags from an old review).

This exists because monday.com automations cannot trigger off Formula
columns -- this script is the workaround, same pattern as
check_contract_expirations.py.

Run on a schedule (see the GitHub Actions workflow in this same folder)
or manually with: python check_pillar_scores.py
"""

import os
import sys
import requests

MONDAY_API_URL = "https://api.monday.com/v2"
BOARD_ID = 18421022069  # Employee Performance Scorecard

# Column IDs on that board
COL_DELIVERY = "formula_mm52t27g"
COL_QUALITY = "formula_mm529sr"
COL_COMMUNICATION = "formula_mm52e731"
COL_COLLABORATION = "formula_mm525da6"
COL_COACHING_AREAS = "dropdown_mm52873k"

# Maps each pillar's formula column -> the label it should add when < 3
PILLAR_LABELS = {
    COL_DELIVERY: "Delivery",
    COL_QUALITY: "Quality",
    COL_COMMUNICATION: "Communication and Ownership",
    COL_COLLABORATION: "Collaboration",
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


def fetch_items(token: str) -> list[dict]:
    """Fetch all items with the 4 pillar formula values and current Coaching Areas."""
    column_ids = list(PILLAR_LABELS.keys()) + [COL_COACHING_AREAS]
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
    """Work out which Coaching Areas labels an item SHOULD have right now."""
    values = {cv["id"]: cv["text"] for cv in item["column_values"]}
    needed = []
    for col_id, label in PILLAR_LABELS.items():
        raw = values.get(col_id)
        if raw in (None, ""):
            continue  # not yet calculated / no data yet, skip
        try:
            score = float(raw)
        except ValueError:
            continue
        if score < THRESHOLD:
            needed.append(label)
    return needed


def current_labels(item: dict) -> set[str]:
    values = {cv["id"]: cv["text"] for cv in item["column_values"]}
    text = values.get(COL_COACHING_AREAS) or ""
    return {t.strip() for t in text.split(",") if t.strip()}


def update_coaching_areas(item_id: str, labels: list[str], token: str) -> None:
    """Overwrite the Coaching Areas dropdown with exactly the given labels."""
    value = {"labels": labels} if labels else {"labels": []}
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
    import json
    variables = {
        "boardId": str(BOARD_ID),
        "itemId": str(item_id),
        "columnId": COL_COACHING_AREAS,
        "value": json.dumps(value),
    }
    run_query(mutation, variables, token)


def main() -> None:
    token = get_token()
    items = fetch_items(token)
    print(f"Checked {len(items)} item(s) on board {BOARD_ID}")

    for item in items:
        needed = set(compute_labels(item))
        existing = current_labels(item)

        if needed == existing:
            continue  # already correct, don't waste an API call

        update_coaching_areas(item["id"], sorted(needed), token)
        print(
            f"  [{item['name']}] Coaching Areas: {sorted(existing)} -> {sorted(needed)}"
        )

    print("Done.")


if __name__ == "__main__":
    main()
