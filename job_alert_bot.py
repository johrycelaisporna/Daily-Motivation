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
        seven_days_ago = today - timedelta(days=7)
        three_months_ago = today - timedelta(days=90)
        
        print(f"Looking for:")
        print(f"  - New jobs added in last 7 days (since {seven_days_ago.strftime('%Y-%m-%d')})")
        print(f"  - Open jobs older than 3 months (before {three_months_ago.strftime('%Y-%m-%d')})")
        
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
                
                recruiter = ""
                status = ""
                role_status = ""
                client = ""
                location = ""
                skills = ""
                top_5_skills = ""
                job_listed_date = ""
                
                for col in item['column_values']:
                    col_id = col.get('id', '')
                    col_text = (col.get('text') or '').strip()
                    
                    # Map column IDs based on debug output
                    if col_id == 'people':  # Recruiter
                        recruiter = col_text
                    elif col_id == 'status7':  # Role Status
                        role_status = col_text
                    elif col_id == 'status_mkn7hmst':  # Hiring Status
                        status = col_text
                    elif col_id == 'dropdown':  # Client
                        client = col_text
                    elif col_id == 'color_mknjx0n':  # Role Type
                        location = col_text
                    elif col_id == 'dropdown_mkxfm4d1':  # Top 5 skills needed
                        top_5_skills = col_text
                    elif col_id == 'date_1_mkn7ny21':  # Job Listed
                        job_listed_date = col_text
                
                # Check Role Status first
                if not role_status:
                    print(f"    ✗ {job_title}: No role status found")
                    continue
                
                # Normalize the role status - replace both dash types and normalize spacing
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
                
                # Check if job qualifies:
                # Option A: Listed in last 7 days
                # OR
                # Option C: Open for more than 3 months (90 days) with qualifying status
                is_new = listed_date >= seven_days_ago
                is_old_open = job_age_days > 90
                
                if not (is_new or is_old_open):
                    print(f"    ✗ {job_title}: {job_age_days} days old (not new and not >90 days)")
                    continue
                
                job_type = "🆕 NEW" if is_new else "⏰ STILL OPEN (90+ days)"
                print(f"    ✓ {job_type}: {job_title} ({job_age_days} days old)")
                
                new_jobs.append({
                    'id': job_id,
                    'title': job_title,
                    'recruiter': recruiter,
                    'status': status,
                    'role_status': role_status,
                    'client': client,
                    'location': location,
                    'skills': skills,
                    'top_5_skills': top_5_skills,
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
    
    # Separate new vs old open jobs
    new_jobs = [j for j in jobs if j['is_new']]
    old_open_jobs = [j for j in jobs if not j['is_new']]
    
    # Build message
    message = f"🎯 *WEEKLY JOB ALERTS* 🎯\n\n"
    
    if new_jobs:
        message += f"🆕 *NEW JOBS THIS WEEK* ({len(new_jobs)})\n\n"
        
        for job in new_jobs:
            message += f"━━━━━━━━━━━━━━━━━━━━━\n"
            message += f"💼 *{job['title']}*\n"
            
            if job['client']:
                message += f"🏢 Client: *{job['client']}*\n"
            
            if job['location']:
                message += f"📍 Location: {job['location']}\n"
            
            if job['top_5_skills']:
                message += f"⭐ Top 5 Skills: {job['top_5_skills']}\n"
            elif job['skills']:
                message += f"🎓 Skills: {job['skills']}\n"
            
            if job['recruiter']:
                message += f"👤 Recruiter: {job['recruiter']}\n"
            
            message += f"📅 Posted: {job['created_at']}\n"
            message += f"📊 Role Status: {job['role_status']}\n"
            message += f"🔗 View: https://adacahq.monday.com/boards/{BOARD_ID}/pulses/{job['id']}\n\n"
    
    if old_open_jobs:
        message += f"\n⏰ *STILL OPEN - NEED URGENT ATTENTION* ({len(old_open_jobs)})\n"
        message += f"_These positions have been open for 90+ days_\n\n"
        
        for job in old_open_jobs:
            message += f"━━━━━━━━━━━━━━━━━━━━━\n"
            message += f"💼 *{job['title']}* ⚠️\n"
            
            if job['client']:
                message += f"🏢 Client: *{job['client']}*\n"
            
            message += f"⏳ Open for: *{job['job_age_days']} days*\n"
            
            if job['location']:
                message += f"📍 Location: {job['location']}\n"
            
            if job['top_5_skills']:
                message += f"⭐ Top 5 Skills: {job['top_5_skills']}\n"
            elif job['skills']:
                message += f"🎓 Skills: {job['skills']}\n"
            
            if job['recruiter']:
                message += f"👤 Recruiter: {job['recruiter']}\n"
            
            message += f"📅 Originally Posted: {job['created_at']}\n"
            message += f"📊 Role Status: {job['role_status']}\n"
            message += f"🔗 View: https://adacahq.monday.com/boards/{BOARD_ID}/pulses/{job['id']}\n\n"
    
    # Post summary
    message += f"━━━━━━━━━━━━━━━━━━━━━\n"
    message += f"📊 *Summary*\n"
    message += f"🆕 New jobs: {len(new_jobs)}\n"
    message += f"⏰ Still open (90+ days): {len(old_open_jobs)}\n"
    message += f"📋 Total: {len(jobs)} position(s)\n"
    message += f"\n💪 Let's find amazing talent for these roles!"
    
    # Post to Slack
    if post_to_slack(message):
        print("✅ All job alerts posted!")
    else:
        print("❌ Failed to post to Slack")

if __name__ == "__main__":
    post_job_alerts()
