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
        
        # Get today and time ranges in Manila timezone
        manila_tz = timezone(timedelta(hours=8))
        today = datetime.now(manila_tz)
        three_days_ago = today - timedelta(days=3)
        ninety_days_ago = today - timedelta(days=90)
        
        print(f"Looking for jobs added in last 3 days (since {three_days_ago.strftime('%Y-%m-%d')})")
        print(f"And jobs open for 0-90+ days")
        
        for group in groups:
            group_title = group.get('title', '')
            
            # Only process "Active Recruitment" group (case-insensitive)
            if group_title.lower() != 'active recruitment':
                print(f"  Skipping group: {group_title}")
                continue
            
            items = group['items_page']['items']
            print(f"  Checking group: {group_title} ({len(items)} items)")
            
            for item in items:
                job_title = item.get('name', '').strip()
                job_id = item.get('id', '')
                
                role_status = ""
                client = ""
                top_5_skills = ""
                headcount = ""
                job_listed_date = ""
                
                for col in item['column_values']:
                    col_id = col.get('id', '')
                    col_text = (col.get('text') or '').strip()
                    
                    # Debug: print all columns to help identify the right IDs
                    if col_text:
                        print(f"      Column '{col_id}': {col_text}")
                    
                    # Map column IDs
                    if col_id == 'status7':  # Role Status
                        role_status = col_text
                    elif col_id == 'dropdown':  # Client
                        client = col_text
                    elif col_id == 'dropdown_mkxfm4d1':  # Top 5 skills needed
                        top_5_skills = col_text
                    elif 'number' in col_id.lower() or 'headcount' in col_id.lower() or 'head_count' in col_id.lower():  # Headcount
                        headcount = col_text
                    elif col_id == 'date_1_mkn7ny21':  # Job Listed
                        job_listed_date = col_text
                
                # Check Role Status first
                if not role_status:
                    print(f"    ✗ {job_title}: No role status found")
                    continue
                
                # Normalize the role status
                role_status_normalized = role_status.replace('–', '-').replace('  ', ' ').lower().strip()
                allowed_statuses = ['need more profiles', 'in progress', 'sales - new lead']
                
                if role_status_normalized not in allowed_statuses:
                    print(f"    ✗ {job_title}: Role status is '{role_status}', skipping")
                    continue
                
                # Parse Job Listed date
                if not job_listed_date:
                    print(f"    ✗ {job_title}: No 'Job Listed' date found")
                    continue
                
                job_listed_iso = parse_date_to_iso(job_listed_date)
                if not job_listed_iso:
                    print(f"    ✗ {job_title}: Could not parse 'Job Listed' date: {job_listed_date}")
                    continue
                
                try:
                    listed_date = datetime.strptime(job_listed_iso, '%Y-%m-%d')
                    listed_date = listed_date.replace(tzinfo=manila_tz)
                except:
                    print(f"    ✗ {job_title}: Could not convert date")
                    continue
                
                # Calculate age of job
                job_age_days = (today - listed_date).days
                
                # Include jobs from 0 to 90+ days
                # Alert specifically for jobs added in last 3 days
                is_new = listed_date >= three_days_ago
                
                print(f"    ✓ {job_title} ({job_age_days} days old) {'🆕 NEW!' if is_new else ''}")
                
                new_jobs.append({
                    'id': job_id,
                    'title': job_title,
                    'role_status': role_status,
                    'client': client,
                    'top_5_skills': top_5_skills,
                    'headcount': headcount or "1",
                    'created_at': listed_date.strftime('%B %d, %Y'),
                    'job_age_days': job_age_days,
                    'is_new': is_new
                })
    
    print(f"✅ Found {len(new_jobs)} job(s)")
    return new_jobs

def post_job_alerts():
    """Post new job alerts to Slack"""
    print("🎯 Checking for job postings...")
    
    jobs = get_new_jobs()
    
    if not jobs:
        print("ℹ️ No jobs to post")
        return
    
    # Separate new vs regular jobs
    new_jobs = [j for j in jobs if j['is_new']]
    regular_jobs = [j for j in jobs if not j['is_new']]
    
    # Sort by age (newest first)
    new_jobs.sort(key=lambda x: x['job_age_days'])
    regular_jobs.sort(key=lambda x: x['job_age_days'])
    
    # Build message
    message = f"🎉 *WEEKLY JOB OPENINGS* 🎉\n\n"
    message += f"💰 *REFER & EARN!* Get a bonus when your referral is regularized! 💰\n\n"
    
    if new_jobs:
        message += f"✨ *HOT OFF THE PRESS - NEW THIS WEEK!* ({len(new_jobs)})\n\n"
        
        for job in new_jobs:
            message += f"🔥 *{job['title']}*\n"
            
            if job['client']:
                message += f"   🏢 Client: *{job['client']}*\n"
            
            if job['top_5_skills']:
                message += f"   🎯 Skills: {job['top_5_skills']}\n"
            
            if job['headcount']:
                message += f"   👥 Headcount: {job['headcount']}\n"
            
            message += f"   📅 Posted: {job['created_at']}\n\n"
    
    if regular_jobs:
        message += f"\n📋 *ALL ACTIVE OPENINGS* ({len(regular_jobs)})\n"
        message += f"_Help us fill these roles - your network is powerful!_ 🌟\n\n"
        
        for job in regular_jobs:
            age_emoji = "🔥" if job['job_age_days'] <= 7 else "⚡" if job['job_age_days'] <= 30 else "📌"
            
            message += f"{age_emoji} *{job['title']}*\n"
            
            if job['client']:
                message += f"   🏢 Client: *{job['client']}*\n"
            
            if job['top_5_skills']:
                message += f"   🎯 Skills: {job['top_5_skills']}\n"
            
            if job['headcount']:
                message += f"   👥 Headcount: {job['headcount']}\n"
            
            message += f"   ⏰ Open for: {job['job_age_days']} days\n\n"
    
    # Post summary
    message += f"━━━━━━━━━━━━━━━━━━━━━\n"
    message += f"📊 *SUMMARY*\n"
    message += f"✨ New this week: {len(new_jobs)}\n"
    message += f"📋 Total active: {len(jobs)}\n\n"
    message += f"💡 *Know someone perfect for these roles?*\n"
    message += f"Refer them and earn a bonus when they're regularized! 🎁\n\n"
    message += f"🚀 Let's build amazing teams together!"
    
    # Post to Slack
    if post_to_slack(message):
        print("✅ Job alerts posted successfully!")
    else:
        print("❌ Failed to post to Slack")

if __name__ == "__main__":
    post_job_alerts()
