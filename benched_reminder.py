#!/usr/bin/env python3
"""
Benched Employees Reminder Bot
Fetches benched employees from Monday.com and posts to Slack
"""

import requests
import json
import os
from datetime import datetime

# Monday.com API configuration
MONDAY_API_URL = "https://api.monday.com/v2"
MONDAY_TOKEN = os.environ.get('MONDAY_API_TOKEN')
BOARD_ID = "6329303796"
GROUP_ID = "not_active_employees__bench_"

# Slack webhook URL
SLACK_WEBHOOK = os.environ.get('SLACK_WEBHOOK_URL')

def fetch_benched_employees():
    """Fetch items from the benched employees group in Monday.com"""
    
    query = """
    query {
      boards(ids: %s) {
        groups(ids: ["%s"]) {
          title
          items_page {
            items {
              name
              column_values {
                id
                text
                value
              }
            }
          }
        }
      }
    }
    """ % (BOARD_ID, GROUP_ID)

    headers = {
        "Authorization": MONDAY_TOKEN,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            MONDAY_API_URL,
            headers=headers,
            json={"query": query},
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Extract benched employees
        groups = data.get('data', {}).get('boards', [{}])[0].get('groups', [])
        
        if not groups:
            print("Warning: Group not found or empty")
            return []
        
        items = groups[0].get('items_page', {}).get('items', [])
        benched_employees = [item['name'] for item in items if item.get('name')]
        
        return benched_employees
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Monday.com data: {e}")
        raise
    except (KeyError, IndexError, TypeError) as e:
        print(f"Error parsing Monday.com response: {e}")
        print(f"Response data: {json.dumps(data, indent=2)}")
        raise

def send_slack_notification(benched_employees):
    """Send notification to Slack with list of benched employees"""
    
    current_date = datetime.now().strftime("%B %d, %Y")
    
    if benched_employees:
        employee_list = "\n".join([f"• {emp}" for emp in benched_employees])
        message = f"""
:warning: *Benched Employees Report - {current_date}*

The following employees are currently on the bench:

{employee_list}

*Total: {len(benched_employees)} employee(s)*

_Please review and take appropriate action._
"""
    else:
        message = f"""
:white_check_mark: *Benched Employees Report - {current_date}*

Great news! There are currently no employees on the bench.
"""

    slack_payload = {
        "text": message,
        "mrkdwn": True
    }

    try:
        response = requests.post(
            SLACK_WEBHOOK,
            headers={"Content-Type": "application/json"},
            json=slack_payload,
            timeout=30
        )
        response.raise_for_status()
        
        print(f"✓ Successfully sent notification to Slack")
        print(f"✓ Found {len(benched_employees)} benched employee(s)")
        
    except requests.exceptions.RequestException as e:
        print(f"Error sending to Slack: {e}")
        raise

def main():
    """Main execution function"""
    
    # Validate environment variables
    if not MONDAY_TOKEN:
        raise ValueError("MONDAY_API_TOKEN environment variable not set")
    if not SLACK_WEBHOOK:
        raise ValueError("SLACK_WEBHOOK_URL environment variable not set")
    
    print("Fetching benched employees from Monday.com...")
    benched_employees = fetch_benched_employees()
    
    print(f"Found {len(benched_employees)} benched employee(s)")
    
    print("Sending notification to Slack...")
    send_slack_notification(benched_employees)
    
    print("Done!")

if __name__ == "__main__":
    main()
