import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

# Configuration
MONDAY_API_TOKEN = os.environ.get('MONDAY_API_TOKEN')
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
BOARD_ID = "6329303796"
SLACK_CHANNEL = "contract-renewals"

def parse_date_to_iso(date_str):
    """Convert various date formats to YYYY-MM-DD"""
    if not date_str:
        return ""
    
    formats = [
        '%b %d, %Y',          # Oct 19, 2026
        '%B %d, %Y',          # October 19, 2026
        '%m/%d/%Y',           # 10/19/2026
        '%m/%d/%y',           # 10/19/26
        '%Y-%m-%d',           # 2026-10-19
        '%d/%m/%Y',           # 19/10/2026
        '%d/%m/%y',           # 19/10/26
        '%Y/%m/%d',           # 2026/10/19
        '%y/%m/%d',           # 26/10/19
    ]
    
    for fmt in formats:
        try:
            parsed_date = datetime.strptime(date_str.strip(), fmt)
            return parsed_date.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    return ""

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

def calculate_contract_end_date(start_date_str, duration_months):
    """Calculate contract end date from start date + duration in months"""
    if not start_date_str or not duration_months:
        return ""
    
    try:
        # Parse start date
        start_date = None
        for fmt in ['%Y-%m-%d', '%b %d, %Y', '%B %d, %Y', '%m/%d/%Y', '%m/%d/%y']:
            try:
                start_date = datetime.strptime(start_date_str.strip(), fmt)
                break
            except ValueError:
                continue
        
        if not start_date:
            return ""
        
        # Add duration in months
        month = start_date.month + int(duration_months)
        year = start_date.year
        
        # Handle month overflow
        while month > 12:
            month -= 12
            year += 1
        
        # Create end date (same day of month, or last day if not valid)
        day = start_date.day
        while day > 0:
            try:
                end_date = datetime(year, month, day)
                return end_date.strftime('%Y-%m-%d')
            except ValueError:
                day -= 1  # Try previous day if invalid (e.g., Feb 31)
        
        return ""
    except Exception as e:
        print(f"Error calculating contract end date: {e}")
        return ""

def get_employees_with_contracts():
    """Get all employees and calculate contract end dates"""
    print("📋 Fetching employees from Monday.com...")
    
    query = f'''
    {{
      boards(ids: {BOARD_ID}) {{
        groups {{
          id
          title
          items_page(limit: 500) {{
            items {{
              name
              column_values {{
                id
                title
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
    employees = []
    
    if result.get('data') and result['data'].get('boards'):
        groups = result['data']['boards'][0]['groups']
        
        for group in groups:
            group_title = group.get('title', '')
            items = group['items_page']['items']
            
            print(f"  Checking group: {group_title} ({len(items)} items)")
            
            for item in items:
                name = item.get('name', '').strip()
                position = ""
                project = ""
                start_date = ""
                duration_months = ""
                contract_status = ""
                
                for col in item['column_values']:
                    col_id = col.get('id', '')
                    col_title = col.get('title', '')
                    col_text = (col.get('text') or '').strip()
                    col_value = col.get('value') or ''
                    
                    # Get position
                    if col_id == 'position':
                        position = col_text
                    
                    # Get project
                    elif col_id == 'project':
                        project = col_text
                    
                    # Get start date (Adaca Start Date or Contract Start Date)
                    elif col_id in ['start_date___', 'date_mkkgvb4z']:
                        if col_text:
                            start_date = col_text
                    
                    # Get contract duration (in months)
                    elif col_id == 'numbers_mkm2917g':
                        duration_months = col_text
                    
                    # Get contract status
                    elif col_id == 'status_mkn52y8w':
                        contract_status = col_text
                
                # Calculate contract end date from start date + duration
                if name and start_date and duration_months:
                    contract_end_date = calculate_contract_end_date(start_date, duration_months)
                    
                    if contract_end_date:
                        print(f"    ✓ {name}: {start_date} + {duration_months} months = {contract_end_date}")
                        employees.append({
                            'name': name,
                            'position': position,
                            'project': project,
                            'contract_end_date': contract_end_date,
                            'contract_status': contract_status
                        })
                    else:
                        print(f"    ✗ {name}: Could not calculate end date")
                elif name:
                    print(f"    ✗ {name}: Missing start_date={start_date}, duration={duration_months}")
    
    print(f"✅ Found {len(employees)} employees with contract dates")
    return employees

def check_contract_expirations():
    """Check for contracts expiring in 30, 60, 90 days, or already expired"""
    print("⏰ Checking contract expirations...")
    
    # Get today's date in Manila timezone
    manila_tz = timezone(timedelta(hours=8))
    today = datetime.now(manila_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Calculate future dates
    days_30 = today + timedelta(days=30)
    days_60 = today + timedelta(days=60)
    days_90 = today + timedelta(days=90)
    
    print(f"Today: {today.strftime('%Y-%m-%d')}")
    print(f"30 days: {days_30.strftime('%Y-%m-%d')}")
    print(f"60 days: {days_60.strftime('%Y-%m-%d')}")
    print(f"90 days: {days_90.strftime('%Y-%m-%d')}")
    
    # Get all employees
    employees = get_employees_with_contracts()
    
    # Categorize by expiration timeframe (including past dates)
    expiring_30 = []
    expiring_60 = []
    expiring_90 = []
    expired = []
    
    for emp in employees:
        try:
            contract_date = datetime.strptime(emp['contract_end_date'], '%Y-%m-%d')
            contract_date = contract_date.replace(tzinfo=manila_tz)
            days_until = (contract_date - today).days
            
            emp['days_until'] = days_until
            
            # Include all expired contracts (any date before today)
            if days_until < 0:
                expired.append(emp)
            elif days_until <= 30:
                expiring_30.append(emp)
            elif days_until <= 60:
                expiring_60.append(emp)
            elif days_until <= 90:
                expiring_90.append(emp)
                
        except ValueError:
            continue
    
    # Build and post alert message with traffic light colors - GROUPED BY PROJECT
    if expired or expiring_30 or expiring_60 or expiring_90:
        message = "🚦 *CONTRACT EXPIRATION ALERTS* 🚦\n\n"
        
        # Combine all lists with their traffic light status
        all_alerts = []
        for emp in expired:
            emp['alert_type'] = 'expired'
            emp['emoji'] = '⚫'
            emp['label'] = 'EXPIRED - NEEDS RENEWAL'
            all_alerts.append(emp)
        for emp in expiring_30:
            emp['alert_type'] = 'red'
            emp['emoji'] = '🔴'
            emp['label'] = 'RED ALERT - 30 DAYS'
            all_alerts.append(emp)
        for emp in expiring_60:
            emp['alert_type'] = 'orange'
            emp['emoji'] = '🟠'
            emp['label'] = 'ORANGE ALERT - 60 DAYS'
            all_alerts.append(emp)
        for emp in expiring_90:
            emp['alert_type'] = 'yellow'
            emp['emoji'] = '🟡'
            emp['label'] = 'YELLOW ALERT - 90 DAYS'
            all_alerts.append(emp)
        
        # Group by project
        projects = {}
        for emp in all_alerts:
            project = emp['project'] or 'No Project'
            if project not in projects:
                projects[project] = []
            projects[project].append(emp)
        
        # Sort projects alphabetically
        for project in sorted(projects.keys()):
            message += f"📁 *{project}*\n"
            
            # Sort employees within project by days_until (most urgent first)
            for emp in sorted(projects[project], key=lambda x: x['days_until']):
                message += f"{emp['emoji']} {emp['name']} - {emp['position']}\n"
                message += f"   Contract End Date: {emp['contract_end_date']} ({emp['label']})\n"
                if emp['days_until'] >= 0:
                    message += f"   Days remaining: {emp['days_until']}\n"
                else:
                    message += f"   Expired {abs(emp['days_until'])} days ago\n"
                message += f"   Status: {emp['contract_status']}\n\n"
            
            message += "\n"
        
        message += "━━━━━━━━━━━━━━━━━━━━━\n"
        message += f"📊 *Summary*\n"
        message += f"⚫ Expired: {len(expired)}\n"
        message += f"🔴 Red (30 days): {len(expiring_30)}\n"
        message += f"🟠 Orange (60 days): {len(expiring_60)}\n"
        message += f"🟡 Yellow (90 days): {len(expiring_90)}\n"
        message += f"📋 Total contracts to review: {len(all_alerts)}\n"
        message += "━━━━━━━━━━━━━━━━━━━━━\n"
        message += "💼 Please review and take necessary action for contract renewals."
        
        # Post to Slack
        if post_to_slack(message):
            print("✅ Contract expiration alerts posted to Slack!")
        else:
            print("❌ Failed to post to Slack")
    else:
        print("ℹ️ No contracts expiring in the next 90 days")

if __name__ == "__main__":
    check_contract_expirations()
