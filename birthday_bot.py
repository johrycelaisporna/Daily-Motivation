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
        last_name = ""
        dob = ""
        
        # Debug: print all columns to see structure
        print(f"\nChecking item: {item.get('name', 'Unknown')}")
        
        # Get column values
        for col in item['column_values']:
            col_id = col.get('id', '')
            col_text = (col.get('text') or '').strip()
            col_value = col.get('value') or ''
            
            print(f"  Column ID: {col_id}, Text: {col_text}")
            
            # Match columns by ID or text content
            if 'first' in col_id.lower():
                first_name = col_text
            elif 'last' in col_id.lower():
                last_name = col_text
            elif 'birth' in col_id.lower() or 'dob' in col_id.lower():
                dob = col_text
                print(f"  Found DOB text: {dob}")
                # Also try parsing from value if text is empty
                if not dob and col_value:
                    try:
                        value_obj = json.loads(col_value)
                        if 'date' in value_obj:
                            dob = value_obj['date']
                            print(f"  Parsed DOB from value: {dob}")
                    except:
                        pass
        
        # Check if birthday matches today
        if dob:
            try:
                # Try different date formats
                for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y', '%m-%d-%Y', '%m/%d/%y']:
                    try:
                        birth_date = datetime.strptime(dob, fmt)
                        print(f"  Parsed date: {birth_date.month}/{birth_date.day}")
                        if birth_date.month == today_month and birth_date.day == today_day:
                            full_name = f"{first_name} {last_name}".strip()
                            if full_name:
                                birthdays_today.append(full_name)
                                print(f"  ✅ BIRTHDAY MATCH: {full_name}")
                        break
                    except ValueError:
                        continue
            except Exception as e:
                print(f"⚠️ Could not parse date for {first_name} {last_name}: {dob} - Error: {e}")
    
    # Post to Slack if there are birthdays
    if birthdays_today:
        print(f"🎉 Found {len(birthdays_today)} birthday(s) today!")
        
        for name in birthdays_today:
            message = f"🎂 *Happy Birthday, {name}!* 🎉\n\nWishing you an amazing day filled with joy and celebration! Have a wonderful year ahead! 🎈"
            
            if post_to_slack(message):
                print(f"✅ Posted birthday message for {name}")
            else:
                print(f"❌ Failed to post message for {name}")
    else:
        print("ℹ️ No birthdays today")

if __name__ == "__main__":
    check_birthdays()
