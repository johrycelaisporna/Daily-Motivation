import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

# Configuration
MONDAY_API_TOKEN = os.environ.get('MONDAY_API_TOKEN')
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
BOARD_ID = "6329303796"
RESULTS_USER = "Den"

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

def get_user_id_by_name(display_name):
    """Get Slack user ID by display name"""
    url = "https://slack.com/api/users.list"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        if result.get('ok'):
            for user in result.get('members', []):
                real_name = user.get('real_name', '').strip()
                username = user.get('name', '').strip()
                profile_name = user.get('profile', {}).get('display_name', '').strip()
                
                # Check all possible name formats
                if (real_name == display_name or 
                    username == display_name.lower() or 
                    profile_name == display_name or
                    display_name.lower() in real_name.lower()):
                    return user.get('id')
    return None

def send_slack_dm(user_id, message):
    """Send DM to a Slack user"""
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "channel": user_id,
        "text": message,
        "unfurl_links": False
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers=headers
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get("ok")
    except Exception as e:
        print(f"Error sending DM: {e}")
        return False

def get_active_employees():
    """Get list of active employees from Monday.com"""
    print("📊 Fetching active employees from Monday.com...")
    
    query = f'''
    {{
      boards(ids: {BOARD_ID}) {{
        groups {{
          id
          title
          items_page {{
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
        
        for group in groups:
            group_title = group.get('title', '').lower()
            
            if ('active' in group_title and 'employee' in group_title) or \
               ('active' in group_title and 'non' in group_title and 'billable' in group_title):
                items = group['items_page']['items']
                for item in items:
                    name = item.get('name', '').strip()
                    if name:
                        employees.append(name)
        
        print(f"✅ Found {len(employees)} active employees")
    
    return employees

def send_pulse_check():
    """Send pulse check DM to all active employees"""
    print("📊 Starting Monthly Pulse Check...")
    
    manila_tz = timezone(timedelta(hours=8))
    today = datetime.now(manila_tz)
    month_name = today.strftime('%B %Y')
    
    print(f"Month: {month_name}")
    
    # Get active employees
    employees = get_active_employees()
    
    if not employees:
        print("❌ No employees found")
        return
    
    # Create the message
    message = f"""📊 *Monthly Pulse Check - {month_name}*

On a scale of 1 to 5, 5 being the highest:

*Would you recommend Adaca to your friend?*

Please reply with a number from 1 to 5:
- 1 ⭐ (Not likely)
- 2 ⭐⭐
- 3 ⭐⭐⭐ (Neutral)
- 4 ⭐⭐⭐⭐
- 5 ⭐⭐⭐⭐⭐ (Very likely)

_Your response is anonymous and helps us improve Adaca._"""
    
    # Send DM to each employee
    sent_count = 0
    failed = []
    
    for employee_name in employees:
        print(f"Sending to: {employee_name}")
        user_id = get_user_id_by_name(employee_name)
        
        if user_id:
            if send_slack_dm(user_id, message):
                sent_count += 1
                print(f"  ✅ Sent")
            else:
                failed.append(employee_name)
                print(f"  ❌ Failed to send")
        else:
            failed.append(employee_name)
            print(f"  ❌ User not found in Slack")
    
    print(f"\n📊 Pulse Check Summary:")
    print(f"✅ Successfully sent: {sent_count}")
    print(f"❌ Failed: {len(failed)}")
    
    if failed:
        print(f"Failed employees: {', '.join(failed)}")
    
    # Notify results recipient
    results_user_id = get_user_id_by_name(RESULTS_USER)
    if results_user_id:
        notification = f"""📊 *Monthly Pulse Check Sent - {month_name}*

✅ Sent to {sent_count} employees

_I'll send you the compiled results in 7 days. People will reply with their scores (1-5) to me via DM._"""
        
        if failed:
            notification += f"\n\n⚠️ Failed to send to {len(failed)} employees:\n{', '.join(failed[:10])}"
        
        send_slack_dm(results_user_id, notification)
        print(f"✅ Notified {RESULTS_USER}")

if __name__ == "__main__":
    send_pulse_check()
