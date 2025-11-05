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
        '%m/%d/%Y',           # 11/05/2025 (primary format)
        '%m/%d/%y',           # 11/05/25
        '%Y-%m-%d',           # 2025-11-05
        '%b %d, %Y',          # Nov 5, 2025
        '%B %d, %Y',          # November 5, 2025
        '%d/%m/%Y',           # 05/11/2025
        '%d/%m/%y',           # 05/11/25
        '%Y/%m/%d',           # 2025/11/05
        '%y/%m/%d',           # 25/11/05
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

def get_employees_with_contracts():
    """Get all active employees with contract end dates"""
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
                contract_end_date = ""
                contract_status = ""
                
                for col in item['column_values']:
                    col_id = col.get('id', '')
                    col_text = (col.get('text') or '').strip()
                    col_value = col.get('value') or ''
                    
                    # Get position
                    if col_id == 'position':
                        position = col_text
                    
                    # Get project
                    elif col_id == 'project':
                        project = col_text
                    
                    # Get contract end date - "Contract End Date" column (formula column)
                    elif col_id == 'formula_mkm2ndwz':
                        contract_end_date = col_text
                        print(f"    {name}: Contract End Date text = '{col_text}'")
                        
                        if not contract_end_date and col_value:
                            try:
                                value_obj = json.loads(col_value)
                                print(f"    {name}: Contract End Date value = {value_obj}")
                                if isinstance(value_obj, str):
                                    contract_end_date = value_obj
                                elif isinstance(value_obj, dict) and 'date' in value_obj:
                                    contract_end_date = value_obj['date']
                            except Exception as e:
                                print(f"    {name}: Error parsing contract date - {e}")
                        
                        if contract_end_date:
                            original_date = contract_end_date
                            contract_end_date = parse_date_to_iso(contract_end_date)
                            print(f"    {name}: Parsed '{original_date}' -> '{contract_end_date}'")
                    
                    # Get contract status
                    elif col_id == 'status_mkn52y8w':
                        contract_status = col_text
                
                if name and contract_end_date:
                    print(f"    ✓ Adding {name} with contract end date: {contract_end_date}")
                    employees.append({
                        'name': name,
                        'position': position,
                        'project': project,
                        'contract_end_date': contract_end_date,
                        'contract_status': contract_status
                    })
                elif name:
                    print(f"    ✗ Skipping {name} (no contract end date)")
    
    print(f"✅ Found {len(employees)} employees with contract dates")
    return employees

def check_contract_expirations():
    """Check for contracts expiring in 30, 60, or 90 days"""
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
    
    # Categorize by expiration timeframe
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
    
    # Build and post alert message with traffic light colors
    if expired or expiring_30 or expiring_60 or expiring_90:
        message = "🚦 *CONTRACT EXPIRATION ALERTS* 🚦\n\n"
        
        if expired:
            message += "⚫ *EXPIRED CONTRACTS* ⚫\n"
            for emp in sorted(expired, key=lambda x: x['days_until']):
                message += f"⚫ *{emp['name']}* - {emp['position']} ({emp['project']})\n"
                message += f"   Expired {abs(emp['days_until'])} days ago on {emp['contract_end_date']}\n"
                message += f"   Status: {emp['contract_status']}\n\n"
        
        if expiring_30:
            message += "🔴 *RED ALERT - EXPIRING WITHIN 30 DAYS* 🔴\n"
            for emp in sorted(expiring_30, key=lambda x: x['days_until']):
                message += f"🔴 *{emp['name']}* - {emp['position']} ({emp['project']})\n"
                message += f"   {emp['days_until']} days left - Expires: {emp['contract_end_date']}\n"
                message += f"   Status: {emp['contract_status']}\n\n"
        
        if expiring_60:
            message += "🟠 *ORANGE ALERT - EXPIRING WITHIN 60 DAYS* 🟠\n"
            for emp in sorted(expiring_60, key=lambda x: x['days_until']):
                message += f"🟠 *{emp['name']}* - {emp['position']} ({emp['project']})\n"
                message += f"   {emp['days_until']} days left - Expires: {emp['contract_end_date']}\n"
                message += f"   Status: {emp['contract_status']}\n\n"
        
        if expiring_90:
            message += "🟡 *YELLOW ALERT - EXPIRING WITHIN 90 DAYS* 🟡\n"
            for emp in sorted(expiring_90, key=lambda x: x['days_until']):
                message += f"🟡 *{emp['name']}* - {emp['position']} ({emp['project']})\n"
                message += f"   {emp['days_until']} days left - Expires: {emp['contract_end_date']}\n"
                message += f"   Status: {emp['contract_status']}\n\n"
        
        message += "━━━━━━━━━━━━━━━━━━━━━\n"
        message += f"📊 *Summary*\n"
        message += f"⚫ Expired: {len(expired)}\n"
        message += f"🔴 Red (30 days): {len(expiring_30)}\n"
        message += f"🟠 Orange (60 days): {len(expiring_60)}\n"
        message += f"🟡 Yellow (90 days): {len(expiring_90)}\n"
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
