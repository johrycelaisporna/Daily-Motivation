import os
import json
import urllib.request
import urllib.parse
import random
from datetime import datetime, timezone, timedelta

# Configuration
MONDAY_API_TOKEN = os.environ.get('MONDAY_API_TOKEN')
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
ANNIVERSARY_BOARD_ID = "6329303796"
SLACK_CHANNEL = "#coffee-dates"

def query_monday(query):
    """Query Monday.com API"""
    url = "https://api.monday.com/v2"
    headers = {
        "Authorization": MONDAY_API_TOKEN,
        "Content-Type": "application/json"
    }
    data = json.dumps({"query": query}).encode('utf-8')

    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))

def post_to_slack(message):
    """Post message to Slack"""
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "channel": SLACK_CHANNEL,
        "text": message,
        "unfurl_links": False
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers=headers
    )

    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        return result.get("ok")

def get_active_employees():
    """Get list of active employees/contractors from Monday.com with pagination"""
    print("☕ Fetching active employees from Monday.com...")

    # Increased limit to 500 to get all items at once
    query = f'''
    {{
      boards(ids: {ANNIVERSARY_BOARD_ID}) {{
        groups {{
          id
          title
          items_page(limit: 500) {{
            items {{
              name
            }}
          }}
        }}
      }}
    }}
    '''

    result = query_monday(query)
    employees = []

    if result.get('data') and result['data'].get('boards'):
        groups = result['data']['boards'][0]['groups']

        # Exclude-based matching: include any group whose title says "active"
        # UNLESS it's explicitly flagged as inactive/archived/etc.
        # This way new "Active ..." groups (contractors, engineers,
        # fractionalised resources, etc.) are picked up automatically without
        # needing a new rule every time a group is added on the board.
        exclude_keywords = ['not active', 'inactive', 'terminated', 'alumni', 'archived', 'offboard']

        for group in groups:
            group_title = group.get('title', '').lower()
            group_name = group.get('title', '')

            is_excluded = any(keyword in group_title for keyword in exclude_keywords)
            is_candidate = 'active' in group_title and not is_excluded

            if is_candidate:
                items = group['items_page']['items']
                print(f"  Including group: {group_name} ({len(items)} people)")
                for item in items:
                    name = item.get('name', '').strip()
                    if name:
                        employees.append(name)
            else:
                print(f"  Skipping group: {group_name}")

        print(f"✅ Found {len(employees)} people total from active groups")

    return employees

def create_groups(employees, group_size=7):
    """Create random groups of ~group_size people.

    Any remainder smaller than group_size gets folded into the existing
    groups (round-robin) instead of forming its own small leftover group,
    so no group ends up with just 1-2 people.
    """
    random.shuffle(employees)
    groups = []

    num_full_groups = len(employees) // group_size
    remainder = len(employees) % group_size

    # Handle the edge case where there aren't even enough people for one group
    if num_full_groups == 0:
        return [employees]

    i = 0
    for _ in range(num_full_groups):
        groups.append(employees[i:i + group_size])
        i += group_size

    # Distribute any leftover people round-robin across the groups
    leftover = employees[i:]
    for idx, person in enumerate(leftover):
        groups[idx % len(groups)].append(person)

    return groups


def assign_team_leader(group):
    """Randomly pick one person in the group to be the team leader
    responsible for scheduling the group's coffee call."""
    return random.choice(group)

def create_coffee_pairings():
    """Create and post coffee date pairings"""
    print("☕ Creating bi-weekly coffee pairings...")

    # Get today's date in Manila timezone
    manila_tz = timezone(timedelta(hours=8))
    today = datetime.now(manila_tz)
    print(f"Today is: {today.strftime('%B %d, %Y')} (Manila time)")

    # Get active employees
    employees = get_active_employees()

    if len(employees) < 2:
        print("❌ Not enough employees to create pairings")
        return

    # Create random groups
    groups = create_groups(employees)

    # Build message
    message = "☕ *Coffee Dates Alert!* ☕\n\n"
    message += "New coffee groups are up! Each group's team leader will schedule the call for *Friday at 2:00 PM PH time* — here's the lineup:\n\n"

    for i, group in enumerate(groups, 1):
        leader = assign_team_leader(group)
        message += f"*Group {i}:*\n"
        for person in group:
            tag = " (Team Leader — please schedule the call for Friday 2:00 PM PH time 📅)" if person == leader else ""
            message += f"  • {person}{tag}\n"
        message += "\n"

    message += "_Team leaders: please send the invite for Friday 2:00 PM PH time ☕💬_\n\n"
    message += "Next pairings will be posted in two weeks!"

    # Post to Slack
    if post_to_slack(message):
        print(f"✅ Posted coffee pairings for {len(groups)} groups!")
        print(f"Total participants: {len(employees)}")
    else:
        print("❌ Failed to post coffee pairings")

if __name__ == "__main__":
    create_coffee_pairings()
