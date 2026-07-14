"""
check_pillar_scores.py

Processes BOTH the Developer and Non-Developer Employee Performance
Scorecard boards. For each board, it:

1. Computes pillar scores + Overall Score itself from the raw Rating
   question columns (NOT from the Formula columns -- monday.com's API does
   not reliably return computed Formula values through the "text" field,
   so this script re-derives the same AVERAGE math independently).
2. Updates the Coaching Areas dropdown to reflect which pillars are
   currently below 3 (recalculated fresh every run).
3. Posts one consolidated Slack summary per new submission.
4. Creates a Coaching Case or PIP item on the relevant board when the
   Overall Score crosses those thresholds (once per review, tracked via
   checkbox columns so nothing is ever duplicated).

This exists because monday.com automations cannot trigger off Formula
columns either -- this script is the workaround for both problems at
once, same pattern as check_contract_expirations.py.

Run on a schedule (see the GitHub Actions workflow in this same folder)
or manually with: python check_pillar_scores.py
"""

import json
import os
import sys
import requests

MONDAY_API_URL = "https://api.monday.com/v2"
SCORECARD_URL_TEMPLATE = "https://adacahq.monday.com/boards/{board}/pulses/{item}"
SLACK_CHANNEL = "#adaca-excellence-scorecard"


# ---------------------------------------------------------------------------
# Per-scorecard configuration. Add a new dict here to support another board
# without touching any of the logic below.
# ---------------------------------------------------------------------------

SCORECARDS = [
    {
        "name": "Developer",
        "board_id": 18421022069,
        "pillars": {
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
        },
        "coaching_areas_col": "dropdown_mm52873k",
        "label_ids": {
            "Delivery": 1,
            "Quality": 2,
            "Communication and Ownership": 3,
            "Collaboration": 4,
        },
        "employee_col": "text_mm52ps",
        "review_period_col": "timerange_mm52jpf9",
        "review_date_col": "date_mm52nh8r",
        "role_type_col": "color_mm52q72s",
        "coaching_case_created_col": "boolean_mm5364ka",
        "pip_created_col": "boolean_mm53rre1",
        "recognition_notified_col": "boolean_mm53ctmg",
        "leadership_notified_col": "boolean_mm53vj1h",
        "slack_notified_col": "boolean_mm53qzm0",
        # Classification thresholds (4-tier)
        "recognition_threshold": 5.0,   # == 5 -> Recognition
        "leadership_low": 4.0,          # 4.0-4.99 -> Leadership / Upskilling
        "coaching_low": 3.0,            # 3.0-3.99 -> Coaching Case
        "coaching_high": 4.0,
        "pip_threshold": 3.0,           # < 3.0 -> PIP
        "classify_fn": "classify_developer",
        "coaching_board_id": 18421197053,
        "coaching_board_columns": {
            "employee": "text_mm5330cv",
            "review_period": "text_mm53yw1r",
            "coaching_areas": "dropdown_mm53dhkh",
            "overall_score": "numeric_mm53jkg9",
            "source_link": "link_mm53f1dt",
            "classification": None,  # Developer board has no Classification column here
        },
        "pip_board_id": 18421197058,
        "pip_board_columns": {
            "employee": "text_mm53f4qw",
            "overall_score": "numeric_mm53h2we",
            "weak_pillars": "dropdown_mm536yz3",
            "review_date": "date_mm53whmp",
            "source_link": "link_mm53bgjf",
        },
    },
    {
        "name": "Non-Developer",
        "board_id": 18421874087,
        "pillars": {
            "Delivery": [
                "rating_mm587m76",  # Task/Deliverable Completion Rate
                "rating_mm58a77e",  # On-time Milestone Delivery
                "rating_mm58nkgz",  # Proactive Blocker Flagging
                "rating_mm58p8ve",  # Scope Change Handling
            ],
            "Quality": [
                "rating_mm58va9v",  # Error/Rework Rate
                "rating_mm587n7e",  # First-pass Approval Rate
                "rating_mm5899cz",  # Client-reported Quality Issues
                "rating_mm585fx2",  # Accuracy Rate
            ],
            "Communication and Ownership": [
                "rating_mm584zan",  # Response Time / Availability
                "rating_mm58td3x",  # Client Communication Score
                "rating_mm58mqb3",  # Uncertainty Raised Early
                "rating_mm58r1e4",  # Initiative Contributions
                "rating_mm589w4c",  # Accountability Under Pressure
            ],
            "Collaboration": [
                "rating_mm58b6xr",  # Peer 360 Feedback
                "rating_mm58xaww",  # Customer Relationship Score
                "rating_mm5817t",   # Knowledge Sharing
            ],
        },
        "coaching_areas_col": "dropdown_mm58n55x",
        "label_ids": {
            # NOTE: assumes labels were added to this column in this exact
            # order (Delivery, Quality, Communication and Ownership,
            # Collaboration) so the auto-assigned IDs match 1-4.
            "Delivery": 1,
            "Quality": 2,
            "Communication and Ownership": 3,
            "Collaboration": 4,
        },
        "employee_col": "text_mm58pxsh",
        "review_period_col": "timerange_mm58r8n4",
        "review_date_col": "date_mm58xzch",
        "role_type_col": "color_mm584nmg",
        "coaching_case_created_col": "boolean_mm58pk47",
        "pip_created_col": "boolean_mm588q55",
        "recognition_notified_col": "boolean_mm58tsq3",
        "leadership_notified_col": "boolean_mm586zcr",
        "slack_notified_col": "boolean_mm58kf9d",
        # Classification thresholds (5-tier, per the non-developer framework)
        "recognition_threshold": 5.0,   # == 5 -> Role Model
        "leadership_low": 4.5,          # 4.5-4.99 -> High Performer
        "coaching_low": 3.0,            # 3.0-4.49 -> Coaching Case (Strong Performer + Meet Expectations)
        "coaching_high": 4.5,
        "pip_threshold": 3.0,           # < 3.0 -> Performance Improvement
        "classify_fn": "classify_non_developer",
        "coaching_board_id": 18421874193,
        "coaching_board_columns": {
            "employee": "text_mm58waa5",
            "review_period": "text_mm58crn1",
            "coaching_areas": "dropdown_mm58b18j",
            "overall_score": "numeric_mm5828r3",
            "source_link": "link_mm5826wk",
            "classification": "text_mm58z1cj",
        },
        "pip_board_id": 18421874197,
        "pip_board_columns": {
            "employee": "text_mm58617e",
            "overall_score": "numeric_mm58qvvt",
            "weak_pillars": "dropdown_mm58k7ag",
            "review_date": "date_mm58kem1",
            "source_link": "link_mm58csvd",
        },
    },
]


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


def classify_developer(score: float) -> str:
    if score >= 5:
        return "Replicate"
    if score >= 4:
        return "Leadership / Upskilling"
    if score >= 3:
        return "Targeted Coaching"
    return "Performance Improvement Plan"


def classify_non_developer(score: float) -> str:
    if score >= 5:
        return "Role Model"
    if score >= 4.5:
        return "High Performer"
    if score >= 4:
        return "Strong Performer"
    if score >= 3:
        return "Meet Expectations"
    return "Performance Improvement"


CLASSIFY_FUNCTIONS = {
    "classify_developer": classify_developer,
    "classify_non_developer": classify_non_developer,
}


def all_rating_column_ids(cfg: dict) -> list[str]:
    ids = []
    for cols in cfg["pillars"].values():
        ids.extend(cols)
    return ids


def fetch_items(cfg: dict, token: str) -> list[dict]:
    column_ids = all_rating_column_ids(cfg) + [
        cfg["coaching_areas_col"],
        cfg["employee_col"],
        cfg["review_period_col"],
        cfg["review_date_col"],
        cfg["role_type_col"],
        cfg["coaching_case_created_col"],
        cfg["pip_created_col"],
        cfg["recognition_notified_col"],
        cfg["leadership_notified_col"],
        cfg["slack_notified_col"],
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
    variables = {"boardId": [str(cfg["board_id"])], "columnIds": column_ids}
    data = run_query(query, variables, token)
    return data["boards"][0]["items_page"]["items"]


def compute_labels(cfg: dict, values: dict) -> list[str]:
    needed = []
    for label, rating_col_ids in cfg["pillars"].items():
        scores = []
        for col_id in rating_col_ids:
            raw = values.get(col_id)
            if raw in (None, ""):
                continue
            try:
                scores.append(float(raw))
            except ValueError:
                continue
        if not scores:
            continue
        average = sum(scores) / len(scores)
        if average < 3.0:
            needed.append(label)
    return needed


def overall_score(cfg: dict, values: dict) -> float | None:
    pillar_averages = []
    for rating_col_ids in cfg["pillars"].values():
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


def current_labels(cfg: dict, values: dict) -> set[str]:
    text = values.get(cfg["coaching_areas_col"]) or ""
    return {t.strip() for t in text.split(",") if t.strip()}


def update_coaching_areas(cfg: dict, item_id: str, labels: list[str], token: str) -> None:
    ids = [cfg["label_ids"][label] for label in labels if label in cfg["label_ids"]]
    mutation = """
    mutation ($boardId: ID!, $itemId: ID!, $columnId: String!, $value: JSON!) {
      change_column_value(
        board_id: $boardId, item_id: $itemId, column_id: $columnId, value: $value
      ) { id }
    }
    """
    variables = {
        "boardId": str(cfg["board_id"]),
        "itemId": str(item_id),
        "columnId": cfg["coaching_areas_col"],
        "value": json.dumps({"ids": ids}),
    }
    run_query(mutation, variables, token)


def flag_scorecard_item(cfg: dict, item_id: str, checkbox_col: str, token: str) -> None:
    mutation = """
    mutation ($boardId: ID!, $itemId: ID!, $columnId: String!, $value: JSON!) {
      change_column_value(
        board_id: $boardId, item_id: $itemId, column_id: $columnId, value: $value
      ) { id }
    }
    """
    variables = {
        "boardId": str(cfg["board_id"]),
        "itemId": str(item_id),
        "columnId": checkbox_col,
        "value": json.dumps({"checked": "true"}),
    }
    run_query(mutation, variables, token)


def create_coaching_case(cfg: dict, item: dict, values: dict, needed_labels: list[str],
                          score: float, classification: str, token: str) -> None:
    cols = cfg["coaching_board_columns"]
    employee = values.get(cfg["employee_col"]) or item["name"]
    review_period = values.get(cfg["review_period_col"]) or ""
    source_url = SCORECARD_URL_TEMPLATE.format(board=cfg["board_id"], item=item["id"])

    column_values = {
        cols["employee"]: employee,
        cols["review_period"]: review_period,
        cols["overall_score"]: str(round(score, 2)),
        cols["source_link"]: {"url": source_url, "text": "Open review"},
    }
    if needed_labels:
        column_values[cols["coaching_areas"]] = {"labels": needed_labels}
    if cols.get("classification"):
        column_values[cols["classification"]] = classification

    mutation = """
    mutation ($boardId: ID!, $itemName: String!, $columnValues: JSON!) {
      create_item(board_id: $boardId, item_name: $itemName, column_values: $columnValues, create_labels_if_missing: true) {
        id
      }
    }
    """
    variables = {
        "boardId": str(cfg["coaching_board_id"]),
        "itemName": f"{employee} — Coaching Case",
        "columnValues": json.dumps(column_values),
    }
    run_query(mutation, variables, token)
    flag_scorecard_item(cfg, item["id"], cfg["coaching_case_created_col"], token)


def create_pip(cfg: dict, item: dict, values: dict, needed_labels: list[str],
                score: float, token: str) -> None:
    cols = cfg["pip_board_columns"]
    employee = values.get(cfg["employee_col"]) or item["name"]
    review_date = values.get(cfg["review_date_col"]) or ""
    source_url = SCORECARD_URL_TEMPLATE.format(board=cfg["board_id"], item=item["id"])

    column_values = {
        cols["employee"]: employee,
        cols["overall_score"]: str(round(score, 2)),
        cols["source_link"]: {"url": source_url, "text": "Open review"},
    }
    if needed_labels:
        column_values[cols["weak_pillars"]] = {"labels": needed_labels}
    if review_date:
        column_values[cols["review_date"]] = {"date": review_date}

    mutation = """
    mutation ($boardId: ID!, $itemName: String!, $columnValues: JSON!) {
      create_item(board_id: $boardId, item_name: $itemName, column_values: $columnValues, create_labels_if_missing: true) {
        id
      }
    }
    """
    variables = {
        "boardId": str(cfg["pip_board_id"]),
        "itemName": f"{employee} — PIP",
        "columnValues": json.dumps(column_values),
    }
    run_query(mutation, variables, token)
    flag_scorecard_item(cfg, item["id"], cfg["pip_created_col"], token)


def post_to_slack(message: str) -> bool:
    """Returns True if the message was actually sent, False otherwise.

    Uses the Slack Web API (chat.postMessage) with a Bot Token
    (SLACK_BOT_TOKEN secret), not an incoming webhook.
    """
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


def process_scorecard(cfg: dict, token: str) -> None:
    classify = CLASSIFY_FUNCTIONS[cfg["classify_fn"]]
    items = fetch_items(cfg, token)
    print(f"[{cfg['name']}] Checked {len(items)} item(s) on board {cfg['board_id']}")

    for item in items:
        values = {cv["id"]: cv["text"] for cv in item["column_values"]}

        needed = set(compute_labels(cfg, values))
        existing = current_labels(cfg, values)
        if needed != existing:
            update_coaching_areas(cfg, item["id"], sorted(needed), token)
            print(f"  [{cfg['name']}][{item['name']}] Coaching Areas: {sorted(existing)} -> {sorted(needed)}")
        else:
            print(f"  [{cfg['name']}][{item['name']}] Coaching Areas unchanged ({sorted(existing)})")

        score = overall_score(cfg, values)
        if score is None:
            continue

        classification = classify(score)

        already_slack_notified = bool(values.get(cfg["slack_notified_col"]))
        if not already_slack_notified:
            employee = values.get(cfg["employee_col"]) or item["name"]
            role = values.get(cfg["role_type_col"]) or "—"
            source_url = SCORECARD_URL_TEMPLATE.format(board=cfg["board_id"], item=item["id"])

            lines = [
                f"*New {cfg['name']} performance review submitted*",
                f"*Employee:* {employee}  |  *Role:* {role}",
                f"*Overall Score:* {score:.2f}  |  *Classification:* {classification}",
            ]
            if needed:
                lines.append(f"*Coaching Areas flagged:* {', '.join(sorted(needed))}")
            if score >= cfg["recognition_threshold"]:
                lines.append("🎉 Perfect score — candidate for Recognition.")
            elif cfg["leadership_low"] <= score < cfg["recognition_threshold"]:
                lines.append("⭐ Candidate for Leadership / Upskilling.")
            elif score < cfg["pip_threshold"]:
                lines.append("🚨 Below 3.0 — a PIP has been created.")
            elif cfg["coaching_low"] <= score < cfg["coaching_high"]:
                lines.append("📋 In Coaching range — a Coaching Case has been created.")
            lines.append(f"<{source_url}|Open review>")

            sent = post_to_slack("\n".join(lines))
            if sent:
                flag_scorecard_item(cfg, item["id"], cfg["slack_notified_col"], token)
                print(f"  [{cfg['name']}][{item['name']}] Posted Slack summary (score {score:.2f})")
            else:
                print(f"  [{cfg['name']}][{item['name']}] Slack post FAILED, will retry next run")

        already_coaching = bool(values.get(cfg["coaching_case_created_col"]))
        already_pip = bool(values.get(cfg["pip_created_col"]))
        already_recognized = bool(values.get(cfg["recognition_notified_col"]))
        already_leadership = bool(values.get(cfg["leadership_notified_col"]))

        if score >= cfg["recognition_threshold"] and not already_recognized:
            flag_scorecard_item(cfg, item["id"], cfg["recognition_notified_col"], token)
            print(f"  [{cfg['name']}][{item['name']}] Flagged Recognition (score {score:.2f})")

        elif cfg["leadership_low"] <= score < cfg["recognition_threshold"] and not already_leadership:
            flag_scorecard_item(cfg, item["id"], cfg["leadership_notified_col"], token)
            print(f"  [{cfg['name']}][{item['name']}] Flagged Leadership (score {score:.2f})")

        if cfg["coaching_low"] <= score < cfg["coaching_high"] and not already_coaching:
            create_coaching_case(cfg, item, values, sorted(needed), score, classification, token)
            print(f"  [{cfg['name']}][{item['name']}] Created Coaching Case (score {score:.2f})")
        elif score < cfg["pip_threshold"] and not already_pip:
            create_pip(cfg, item, values, sorted(needed), score, token)
            print(f"  [{cfg['name']}][{item['name']}] Created PIP (score {score:.2f})")


def main() -> None:
    token = get_token()
    for cfg in SCORECARDS:
        process_scorecard(cfg, token)
    print("Done.")


if __name__ == "__main__":
    main()
