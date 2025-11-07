import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

# Configuration
MONDAY_API_TOKEN = os.environ.get('MONDAY_API_TOKEN')
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
BOARD_ID = "6239668497"
SLACK_CHANNEL = "job-hirings"

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

def post_to_slack(message, channel=SLACK_CHANNEL):
    """Post message to Slack"""
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "channel": channel,
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

def parse_date_to_iso(date_str):
    """Convert various date formats to YYYY-MM-DD"""
    if not date_str:
        return ""
    
    formats = [
        '%Y-%m-%d',
        '%b %d, %Y',
        '%B %d, %Y',
        '%m/%d/%Y',
        '%m/%d/%y',
        '%d/%m/%Y',
        '%d/%m/%y',
    ]
    
    for fmt in formats:
        try:
            parsed_date = datetime.strptime(date_str.strip(), fmt)
            return parsed_date.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    return ""

def get_new_jobs():
    """Get new job postings from Active recruitment group"""
    print("🔍 Fetching job postings from Monday.com...")
    
    query = f'''
    {{
      boards(ids: {BOARD_ID}) {{
        groups {{
          id
          title
          items_page(limit: 500) {{
            items {{
              id
              name
              created_at
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
    new_jobs = []
    
    if 'errors' in result:
        print(f"❌ API ERRORS:")
        for error in result['errors']:
            print(f"   - {error}")
        return []
    
    if result.get('data') and result['data'].get('boards'):
        groups = result['data']['boards'][0]['groups']
        
        # Get today and 7 days ago in Manila timezone
        manila_tz = timezone(timedelta(hours=8))
        today = datetime.now(manila_tz)
        seven_days_ago = today - timedelta(days=7)
        
        print(f"Looking for jobs added between {seven_days_ago.strftime('%Y-%m-%d')} and {today.strftime('%Y-%m-%d')}")
        
        for group in groups:
            group_title = group.get('title', '')
            
            # Only process "Active recruitment" group
            if group_title != 'Active recruitment':
                print(f"  Skipping group: {group_title}")
                continue
            
            items = group['items_page']['items']
            print(f"  Checking group: {group_title} ({len(items)} items)")
            
            for item in items:
                job_title = item.get('name', '').strip()
                job_id = item.get('id', '')
                created_at_str = item.get('created_at', '')
                
                # Parse created date
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    created_at = created_at.astimezone(manila_tz)
                except:
                    print(f"    ✗ {job_title}: Could not parse created date")
                    continue
                
                # Check if job was created in the last 7 days
                if created_at < seven_days_ago:
                    continue
                
                recruiter = ""
                status = ""
                role_status = ""
                client = ""
                location = ""
                skills = ""
                salary = ""
                
                for col in item['column_values']:
                    col_id = col.get('id', '')
                    col_text = (col.get('text') or '').strip()
                    
                    # Map column IDs (you may need to adjust these)
                    if 'recruiter' in col_id.lower() or 'person' in col_id.lower():
                        recruiter = col_text
                    elif col_id.lower() == 'status':
                        status = col_text
                    elif 'role' in col_id.lower() and 'status' in col_id.lower():
                        role_status = col_text
                    elif 'client' in col_id.lower() or 'company' in col_id.lower():
                        client = col_text
                    elif 'location' in col_id.lower():
                        location = col_text
                    elif 'skill' in col_id.lower() or 'tech' in col_id.lower():
                        skills = col_text
                    elif 'salary' in col_id.lower():
                        salary = col_text
                
                # Check Role Status - must be "need more profiles", "In progress", or "sales - New Lead"
                if not role_status:
                    print(f"    ✗ {job_title}: No role status found")
                    continue
                
                role_status_lower = role_status.lower()
                allowed_statuses = ['need more profiles', 'in progress', 'sales - new lead']
                if role_status_lower not in allowed_statuses:
                    print(f"    ✗ {job_title}: Role status is '{role_status}', skipping")
                    continue
                
                print(f"    ✓ NEW JOB: {job_title} (created {created_at.strftime('%Y-%m-%d')})")
                
                new_jobs.append({
                    'id': job_id,
                    'title': job_title,
                    'recruiter': recruiter,
                    'status': status,
                    'role_status': role_status,
                    'client': client,
                    'location': location,
                    'skills': skills,
                    'salary': salary,
                    'created_at': created_at.strftime('%B %d, %Y')
                })
    
    print(f"✅ Found {len(new_jobs)} new job(s)")
    return new_jobs

def post_job_alerts():
    """Post new job alerts to Slack"""
    print("🎯 Checking for new job postings...")
    
    new_jobs = get_new_jobs()
    
    if not new_jobs:
        print("ℹ️ No new jobs to post")
        return
    
    # Post header message
    header = f"🎯 *NEW JOB OPENINGS THIS WEEK* 🎯\n\n"
    header += f"We have {len(new_jobs)} new position(s) to fill!\n\n"
    
    for job in new_jobs:
        message = header if new_jobs.index(job) == 0 else ""
        
        message += f"━━━━━━━━━━━━━━━━━━━━━\n"
        message += f"💼 *{job['title']}*\n\n"
        
        if job['client']:
            message += f"🏢 Client: {job['client']}\n"
        
        if job['location']:
            message += f"📍 Location: {job['location']}\n"
        
        if job['salary']:
            message += f"💰 Salary: {job['salary']}\n"
        
        if job['skills']:
            message += f"🎓 Skills: {job['skills']}\n"
        
        if job['recruiter']:
            message += f"👤 Recruiter: {job['recruiter']}\n"
        
        message += f"📅 Posted: {job['created_at']}\n"
        message += f"📊 Role Status: {job['role_status']}\n"
        message += f"\n🔗 View in Monday.com: https://adacahq.monday.com/boards/{BOARD_ID}/pulses/{job['id']}\n"
        
        # Post to Slack
        if post_to_slack(message):
            print(f"  ✅ Posted: {job['title']}")
        else:
            print(f"  ❌ Failed to post: {job['title']}")
    
    # Post summary
    summary = f"\n━━━━━━━━━━━━━━━━━━━━━\n"
    summary += f"📊 *Summary*: {len(new_jobs)} new job opening(s) this week\n"
    summary += f"💪 Let's find amazing talent for these roles!\n"
    
    post_to_slack(summary)
    print("✅ All job alerts posted!")

if __name__ == "__main__":
    post_job_alerts()
