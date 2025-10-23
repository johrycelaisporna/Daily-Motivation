import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
import random

# Configuration
MONDAY_API_TOKEN = os.environ.get('MONDAY_API_TOKEN')
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
BIRTHDAY_BOARD_ID = "6329174559"
ANNIVERSARY_BOARD_ID = "6329303796"
SLACK_CHANNEL = "celebrations"

# Birthday message templates
BIRTHDAY_MESSAGES = [
    "🎂 *Happy Birthday, {name}!* 🎉\n\nWishing you an amazing day filled with joy and celebration! Have a wonderful year ahead! 🎈",
    "🎂 *Happy Birthday, {name}!* 🎉\n\nHope your special day is as incredible as you are! Enjoy every moment! 🥳",
    "🎂 *It's {name}'s Birthday!* 🎉\n\nWishing you a fantastic day filled with laughter, love, and cake! 🍰",
    "🎂 *Happy Birthday, {name}!* 🎉\n\nMay this year bring you success, happiness, and everything you've been dreaming of! 🌟",
    "🎂 *Celebrating {name} today!* 🎉\n\nHappy Birthday! Here's to another year of amazing achievements and great memories! 🎈"
]

# Work anniversary message templates
ANNIVERSARY_MESSAGES = [
    "🎊 *Happy Work Anniversary, {name}!* 🎉\n\nCelebrating {years} with Adaca today! Thank you for your dedication and contributions to the team. Here's to many more! 🥳",
    "🎊 *Congratulations, {name}!* 🎉\n\nToday marks {years} with Adaca! Thank you for being an incredible part of our journey. We're lucky to have you on the team! 🙌",
    "🎊 *{years} of awesome!* 🎉\n\nHappy Work Anniversary, {name}! Thanks for bringing your A-game to Adaca every day. Let's celebrate! 🥳🎈",
    "🎊 *{name} is celebrating {years} with us!* 🎉\n\nYour hard work and passion make Adaca better every day. Thank you for everything you do! 🌟",
    "🎊 *Cheers to {name}!* 🎉\n\n{years} with Adaca and still going strong! We appreciate all your contributions to the team. Here's to the journey ahead! 🚀"
]

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

def calculate_years(start_date, today):
    """Calculate years of service"""
    years = today.year - start_date.year
    # Adjust if anniversary hasn't occurred yet this year
    if (today.month, today.day) < (start_date.month, start_date.day):
        years -= 1
    return years

def format_years(years):
    """Format years text"""
    if years == 1:
        return "1 year"
    else:
        return f"{years} years"

def check_celebrations():
    """Check for birthdays and work anniversaries today"""
    print("🎂 Checking for celebrations today...")
    
    # Get today's date in Manila timezone (UTC+8)
    manila_tz = timezone(timedelta(hours=8))
    today = datetime.now(manila_tz)
    today_month = today.month
    today_day = today.day
    print(f"Today is: {today_month}/{today_day}/{today.year} (Manila time)")
    
    birthdays_today = []
    anniversaries_today = []
    
    # Check Birthday Board
    print("\n--- Checking Birthday Board ---")
    birthday_query = f'''
    {{
      boards(ids: {BIRTHDAY_BOARD_ID}) {{
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
    
    birthday_result = query_monday(birthday_query)
    
    if birthday_result.get('data'):
        items = birthday_result['data']['boards'][0]['items_page']['items']
        
        for item in items:
            first_name = ""
            last_name = ""
            dob = ""
            
            for col in item['column_values']:
                col_id = col.get('id', '')
                col_text = (col.get('text') or '').strip()
                col_value = col.get('value') or ''
                
                if 'first' in col_id.lower():
                    first_name = col_text
                elif 'last' in col_id.lower():
                    last_name = col_text
                elif 'date_of_birth' in col_id.lower():
                    dob = col_text
                    if not dob and col_value:
                        try:
                            value_obj = json.loads(col_value)
                            if 'date' in value_obj:
                                dob = value_obj['date']
                        except:
                            pass
            
            full_name = f"{first_name} {last_name}".strip()
            
            if dob and full_name:
                try:
                    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%m/%d/%y']:
                        try:
                            birth_date = datetime.strptime(dob, fmt)
                            if birth_date.month == today_month and birth_date.day == today_day:
                                birthdays_today.append(full_name)
                                print(f"✅ Birthday: {full_name}")
                            break
                        except ValueError:
                            continue
                except Exception as e:
                    print(f"⚠️ Error checking birthday for {full_name}: {e}")
    
    # Check Anniversary Board - Only Active Employees group
    print("\n--- Checking Anniversary Board (Active Employees only) ---")
    anniversary_query = f'''
    {{
      boards(ids: {ANNIVERSARY_BOARD_ID}) {{
        groups {{
          id
          title
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
    }}
    '''
    
    print("Querying anniversary board...")
    anniversary_result = query_monday(anniversary_query)
    
    print(f"Anniversary query result: {json.dumps(anniversary_result, indent=2)[:500]}...")
    
    if anniversary_result.get('data') and anniversary_result['data'].get('boards'):
        groups = anniversary_result['data']['boards'][0]['groups']
        print(f"Found {len(groups)} groups")
        
        # Find the "Active Employees" group
        for group in groups:
            group_title = group.get('title', '')
            print(f"Group: '{group_title}'")
            
            if 'active' in group_title.lower() and 'employee' in group_title.lower():
                print(f"✅ Found Active Employees group!")
                items = group['items_page']['items']
                print(f"Found {len(items)} items in Active Employees")
                
                for item in items:
                    name = item.get('name', '').strip()
                    start_date = ""
                    
                    print(f"\n  Item: {name}")
                    
                    for col in item['column_values']:
                        col_id = col.get('id', '')
                        col_text = (col.get('text') or '').strip()
                        col_value = col.get('value') or ''
                        
                        print(f"    Column ID: {col_id}, Text: {col_text}")
                        
                        if ('adaca' in col_id.lower() or 'start' in col_id.lower()) and 'date' in col_id.lower():
                            start_date = col_text
                            print(f"    Found start date: {start_date}")
                            if not start_date and col_value:
                                try:
                                    value_obj = json.loads(col_value)
                                    if 'date' in value_obj:
                                        start_date = value_obj['date']
                                        print(f"    Parsed start date from value: {start_date}")
                                except:
                                    pass
                    
                    if start_date and name:
                        print(f"  Processing: {name} - Start Date: {start_date}")
                        try:
                            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%m/%d/%y']:
                                try:
                                    hire_date = datetime.strptime(start_date, fmt)
                                    print(f"    Parsed as: {hire_date.month}/{hire_date.day}/{hire_date.year}")
                                    if hire_date.month == today_month and hire_date.day == today_day:
                                        years = calculate_years(hire_date, today)
                                        print(f"    Years: {years}")
                                        if years > 0:
                                            anniversaries_today.append({
                                                'name': name,
                                                'years': years
                                            })
                                            print(f"  ✅ MATCH! Work Anniversary: {name} - {years} years")
                                    break
                                except ValueError:
                                    continue
                        except Exception as e:
                            print(f"  ⚠️ Error checking anniversary for {name}: {e}")
            else:
                print(f"  Skipping group: {group_title}")
    else:
        print("❌ No data returned from anniversary board query")
    
    # Post birthdays to Slack
    if birthdays_today:
        print(f"\n🎉 Found {len(birthdays_today)} birthday(s) today!")
        for name in birthdays_today:
            message = random.choice(BIRTHDAY_MESSAGES).format(name=name)
            if post_to_slack(message):
                print(f"✅ Posted birthday message for {name}")
            else:
                print(f"❌ Failed to post birthday message for {name}")
    
    # Post anniversaries to Slack
    if anniversaries_today:
        print(f"\n🎊 Found {len(anniversaries_today)} work anniversary/anniversaries today!")
        for person in anniversaries_today:
            years_text = format_years(person['years'])
            message = random.choice(ANNIVERSARY_MESSAGES).format(
                name=person['name'],
                years=years_text
            )
            if post_to_slack(message):
                print(f"✅ Posted anniversary message for {person['name']}")
            else:
                print(f"❌ Failed to post anniversary message for {person['name']}")
    
    if not birthdays_today and not anniversaries_today:
        print("\nℹ️ No celebrations today")

if __name__ == "__main__":
    check_celebrations()
