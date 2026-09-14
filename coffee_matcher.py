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

def create_groups(employees, group_size=3):
    """Create random groups of 3-4 people"""
    random.shuffle(employees)
    groups = []

    i = 0
    while i < len(employees):
        # Calculate how many people are left
        remaining = len(employees) - i

        # If 4 or more people left, make a group of 3 or 4
        if remaining >= 4:
            # Alternate between groups of 3 and 4
            size = 4 if len(groups) % 2 == 0 else 3
            groups.append(employees[i:i+size])
            i += size
        # If exactly 3 people left, make a group of 3
        elif remaining == 3:
            groups.append(employees[i:i+3])
            i += 3
        # If 2 people left, add them to the last group
        elif remaining == 2:
            if groups:
                groups[-1].extend(employees[i:i+2])
            else:
                groups.append(employees[i:i+2])
            break
        # If 1 person left, add to last group
        else:
            if groups:
                groups[-1].append(employees[i])
            else:
                groups.append([employees[i]])
            break

    return groups

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
    message += "It's time to meet at 8:30 AM on Thursday! Here are your random coffee groups:\n\n"

    for i, group in enumerate(groups, 1):
        message += f"*Group {i}:*\n"
        for person in group:
            message += f"  • {person}\n"
        message += "\n"

    message += "_Connect with your group this Thursday at 8:30 AM for coffee ☕🍕💬_\n\n"
    message += "Next pairings will be posted in two weeks!"

    # Post to Slack
    if post_to_slack(message):
        print(f"✅ Posted coffee pairings for {len(groups)} groups!")
        print(f"Total participants: {len(employees)}")
    else:
        print("❌ Failed to post coffee pairings")

if __name__ == "__main__":
    create_coffee_pairings()
