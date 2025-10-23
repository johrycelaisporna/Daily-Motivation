import os
import json
import urllib.request
import urllib.parse
from datetime import datetime

# Configuration
MONDAY_API_TOKEN = os.environ.get('MONDAY_API_TOKEN')
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
BOARD_ID = "6329174559"
SLACK_CHANNEL = "celebrations"

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

def check_birthdays():
    """Check for birthdays today"""
    print("🎂 Checking for birthdays today...")
    
    # Get today's date
    today = datetime.now()
    today_month = today.month
    today_day = today.day
    print(f"Today is: {today_month}/{today_day}")
    
    # Query Monday.com board
    query = f'''
    {{
      boards(ids: {BOARD_ID}) {{
        items_page {{
          items {{
            name
            column_values {{
              id
              text
              value
            }}
          }}
        }}
      }}
    }}
    '''
    
    result = query_monday(query)
    
    if not result.get('data'):
        print("❌ Error getting data from Monday.com")
        return
    
    items = result['data']['boards'][0]['items_page']['items']
    birthdays_today = []
    
    for item in items:
        first_name = ""
        last_name =
