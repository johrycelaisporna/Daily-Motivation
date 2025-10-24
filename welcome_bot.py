import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

# Configuration
MONDAY_API_TOKEN = os.environ.get('MONDAY_API_TOKEN')
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
BOARD_ID = "6329303796"
SLACK_CHANNEL = "general"

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

def get_employees_from_groups():
    """Get all employees from Active Employees and Active - Non billable groups"""
    print("👋 Fetching employees from Monday.com...")
    
    query = f'''
    {{
      boards(ids: {BOARD_ID}) {{
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
    
    result = query_monday(query)
    all_employees = []
    
    if result.get('data') and result['data'].get('boards'):
        groups = result['data']['boards'][0]['groups']
        
        for group in groups:
            group_title = group.get('title', '').lower()
            
            # Include both "Active Employees" and "Active - Non billable" groups
            if ('active' in group_title and 'employee' in group_title) or \
               ('active' in group_title and 'non' in group_title and 'billable' in group_title):
                
                items = group['items_page']['items']
                group_name = group.get('title', '')
                print(f"  Checking group: {group_name}")
                
                for item in items:
                    name = item.get('name', '').strip()
                    position = ""
                    project = ""
                    start_date = ""
                    
                    print(f"    Processing: {name}")
                    
                    for col in item['column_values']:
                        col_id = col.get('id', '').lower()
                        col_text = (col.get('text') or '').strip()
                        col_value = col.get('value') or ''
                        
                        # Debug: print all columns
                        if col_text:
                            print(f"      Column {col_id}: {col_text}")
                        
                        # Get position
                        if 'position' in col_id or 'role' in col_id:
                            position = col_text
                        
                        # Get project/client name
                        elif 'project' in col_id or 'client' in col_id:
                            project = col_text
                        
                        # Get start date
                        elif ('adaca' in col_id or 'start' in col_id) and 'date' in col_id:
                            start_date = col_text
                            if not start_date and col_value:
                                try:
                                    value_obj = json.loads(col_value)
                                    if 'date' in value_obj:
                                        start_date = value_obj['date']
                                except:
                                    pass
                    
                    if name:
                        print(f"      -> Name: {name}, Position: {position}, Project: {project}, Start Date: {start_date}")
                        all_employees.append({
                            'name': name,
                            'position': position,
                            'project': project,
                            'start_date': start_date
                        })
        
        print(f"✅ Found {len(all_employees)} total employees")
    
    return all_employees

def find_buddy(new_hire_project, new_hire_start_date, all_employees):
    """Find a buddy from the same project who started earlier"""
    if not new_hire_project:
        return None
    
    # Filter employees on same project
    same_project = [emp for emp in all_employees 
                   if emp['project'] == new_hire_project 
                   and emp['start_date'] != new_hire_start_date
                   and emp['start_date']]
    
    if not same_project:
        return None
    
    # Sort by start date (earliest first) and return the person who's been there longest
    same_project.sort(key=lambda x: x['start_date'])
    return same_project[0]['name'] if same_project else None

def check_new_hires():
    """Check for new hires starting today"""
    print("👋 Checking for new hires today...")
    
    # Get today's date in Manila timezone
    manila_tz = timezone(timedelta(hours=8))
    today = datetime.now(manila_tz)
    today_str = today.strftime('%Y-%m-%d')
    print(f"Today is: {today.strftime('%B %d, %Y')} (Manila time)")
    print(f"Looking for start date: {today_str}")
    
    # Get all employees
    all_employees = get_employees_from_groups()
    
    # Find new hires (start date is today)
    new_hires = [emp for emp in all_employees if emp['start_date'] == today_str]
    
    if not new_hires:
        print("ℹ️ No new hires starting today")
        return
    
    print(f"🎉 Found {len(new_hires)} new hire(s) starting today!")
    
    # Post welcome message for each new hire
    for hire in new_hires:
        name = hire['name']
        position = hire['position'] or 'Team Member'
        project = hire['project'] or 'Multiple Projects'
        start_date = datetime.strptime(hire['start_date'], '%Y-%m-%d').strftime('%B %d, %Y')
        
        # Find buddy
        buddy = find_buddy(hire['project'], hire['start_date'], all_employees)
        
        # Build welcome message
        message = f"🎉 *Welcome to Adaca, {name}!* 🎉\n\n"
        message += "We're thrilled to have you join our team!\n\n"
        message += f"👤 *Role:* {position}\n"
        message += f"💼 *Project:* {project}\n"
        message += f"📅 *Start Date:* {start_date}\n\n"
        
        if buddy:
            message += f"🤝 *Buddy:* {buddy} is working on the same project and will be your go-to person for questions and support!\n\n"
        
        message += "📋 Make sure to check out our Welcome Packet canvas in <#0a-newhire-welcome-packet> for all the essentials to get you started!\n\n"
        message += "Welcome aboard! We're excited to see what you'll accomplish here! 🚀"
        
        # Post to Slack
        if post_to_slack(message):
            print(f"✅ Posted welcome message for {name}")
        else:
            print(f"❌ Failed to post welcome message for {name}")

if __name__ == "__main__":
    check_new_hires()
