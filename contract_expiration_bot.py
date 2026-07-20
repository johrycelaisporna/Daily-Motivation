import os
import json
import urllib.request
from datetime import datetime, timezone, timedelta
from math import floor

# Configuration
MONDAY_API_TOKEN = os.environ.get('MONDAY_API_TOKEN')
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
BOARD_ID = "6329303796"
SLACK_CHANNEL = "contract-renewals"

ACTIVE_GROUPS = [
    'Active Employees',
    'Active Fractionalised Resources',
    'Active Billable Employees',
    'Active Billable Engineers',
]

def parse_date(date_str):
    """Convert various date formats to YYYY-MM-DD"""
    if not date_str:
        return ""
    formats = [
        '%Y-%m-%d', '%b %d, %Y', '%B %d, %Y',
        '%m/%d/%Y', '%m/%d/%y', '%d/%m/%Y',
        '%d/%m/%y', '%Y/%m/%d', '%y/%m/%d',
    ]
    date_str = date_str.strip().split('T')[0]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return ""

def query_monday(query):
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
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {"channel": channel, "text": message, "unfurl_links": False}
    req = urllib.request.Request(
        url, data=json.dumps(data).encode('utf-8'), headers=headers
    )
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        return result.get("ok")

def calculate_contract_end_date(start_date_str, duration_months):
    """Calculate end date from start date + duration in months (supports decimals)."""
    if not start_date_str or not duration_months:
        return ""
    try:
        start_date_str = parse_date(start_date_str)
        if not start_date_str:
            return ""
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')

        months = floor(float(duration_months) + 0.5)
        if months <= 0:
            months = 1

        month = start_date.month + months
        year = start_date.year
        while month > 12:
            month -= 12
            year += 1

        day = start_date.day
        while day > 0:
            try:
                return datetime(year, month, day).strftime('%Y-%m-%d')
            except ValueError:
                day -= 1
        return ""
    except Exception as e:
        print(f"  ❌ Error calculating end date for start={start_date_str}, duration={duration_months}: {e}")
        return ""

def extract_date_from_column(col):
    """Get date from a Monday column — tries text first, then raw JSON value."""
    col_text = (col.get('text') or '').strip()
    if col_text:
        parsed = parse_date(col_text)
        if parsed:
            return parsed
    raw_value = col.get('value') or ''
    if raw_value:
        try:
            parsed_value = json.loads(raw_value)
            date_from_value = parsed_value.get('date', '')
            if date_from_value:
                return parse_date(date_from_value)
        except (json.JSONDecodeError, AttributeError):
            pass
    return ""

def get_employees_with_contracts():
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

    if 'errors' in result:
        print(f"❌ API ERRORS:")
        for error in result['errors']:
            print(f"   - {error}")
        return []

    if result.get('data') and result['data'].get('boards'):
        groups = result['data']['boards'][0]['groups']

        for group in groups:
            group_title = group.get('title', '')

            if group_title not in ACTIVE_GROUPS:
                print(f"  Skipping group: {group_title}")
                continue

            items = group['items_page']['items']
            print(f"  Checking group: {group_title} ({len(items)} items)")

            for item in items:
                name = item.get('name', '').strip()
                position = ""
                project = ""
                sow_start_date = ""
                emp_start_date = ""
                duration_months = ""
                contract_status = ""
                new_contract_end_date = ""

                for col in item['column_values']:
                    col_id = col.get('id', '')
                    col_text = (col.get('text') or '').strip()

                    if col_id == 'position':
                        position = col_text
                    elif col_id == 'project':
                        project = col_text
                    elif col_id == 'start_date___':
                        emp_start_date = extract_date_from_column(col)
                    elif col_id == 'date_mkkgvb4z':
                        sow_start_date = extract_date_from_column(col)
                    elif col_id == 'numbers_mkm2917g':
                        duration_months = col_text
                    elif col_id == 'status_mkn52y8w':
                        contract_status = col_text
                    elif col_id == 'date_mm4ww2jv':
                        # New Contract End Date — supersedes calculated end date when present
                        new_contract_end_date = extract_date_from_column(col)

                best_start_date = sow_start_date or emp_start_date

                calculated_end_date = ""
                if best_start_date and duration_months:
                    calculated_end_date = calculate_contract_end_date(best_start_date, duration_months)

                # New Contract End Date takes precedence over the calculated one
                final_end_date = new_contract_end_date or calculated_end_date
                end_date_source = "New Contract End Date" if new_contract_end_date else "Calculated (Start + Duration)"

                if name and final_end_date:
                    employees.append({
                        'name': name,
                        'position': position,
                        'project': project,
                        'contract_end_date': final_end_date,
                        'contract_status': contract_status,
                        'end_date_source': end_date_source,
                    })
                else:
                    if name:
                        print(f"  ⚠️  Skipping '{name}' — new_contract_end={repr(new_contract_end_date)}, "
                              f"sow_start={repr(sow_start_date)}, emp_start={repr(emp_start_date)}, duration={repr(duration_months)}")

    print(f"✅ Found {len(employees)} employees with contract dates")
    return employees

def check_contract_expirations():
    print("⏰ Checking contract expirations...")

    manila_tz = timezone(timedelta(hours=8))
    today = datetime.now(manila_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    print(f"Today: {today.strftime('%Y-%m-%d')}")

    employees = get_employees_with_contracts()

    expired = []       # ⚫ black — past due
    expiring_30 = []    # 🔴 red — expiring within 30 days
    expiring_60 = []    # 🟡 amber — expiring within 60 days

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
        except ValueError:
            continue

    if expired or expiring_30 or expiring_60:
        message = "🚦 *CONTRACT EXPIRATION ALERTS* 🚦\n"
        message += "_Showing expired contracts and those expiring within 60 days_\n\n"

        all_alerts = []
        for emp in expired:
            emp['emoji'] = '⚫'
            emp['label'] = 'EXPIRED - NEEDS RENEWAL'
            all_alerts.append(emp)
        for emp in expiring_30:
            emp['emoji'] = '🔴'
            emp['label'] = 'EXPIRING WITHIN 30 DAYS'
            all_alerts.append(emp)
        for emp in expiring_60:
            emp['emoji'] = '🟡'
            emp['label'] = 'EXPIRING WITHIN 60 DAYS'
            all_alerts.append(emp)

        projects = {}
        for emp in all_alerts:
            project = emp['project'] or 'No Project'
            if project not in projects:
                projects[project] = []
            projects[project].append(emp)

        for project in sorted(projects.keys()):
            message += f"📁 *{project}*\n"
            for emp in sorted(projects[project], key=lambda x: x['days_until']):
                message += f"{emp['emoji']} {emp['name']} - {emp['position']}\n"
                message += f"   Contract End Date: {emp['contract_end_date']} ({emp['label']})\n"
                message += f"   Source: {emp['end_date_source']}\n"
                if emp['days_until'] >= 0:
                    message += f"   Days remaining: {emp['days_until']}\n"
                else:
                    message += f"   Expired {abs(emp['days_until'])} days ago\n"
                message += f"   Status: {emp['contract_status']}\n\n"
            message += "\n"

        message += "━━━━━━━━━━━━━━━━━━━━━\n"
        message += f"📊 *Summary*\n"
        message += f"⚫ Expired: {len(expired)}\n"
        message += f"🔴 Expiring within 30 days: {len(expiring_30)}\n"
        message += f"🟠 Expiring within 60 days: {len(expiring_60)}\n"
        message += f"📋 Total contracts requiring action: {len(all_alerts)}\n"
        message += "━━━━━━━━━━━━━━━━━━━━━\n"
        message += "💼 Please review and take necessary action for contract renewals."

        if post_to_slack(message):
            print("✅ Contract expiration alerts posted to Slack!")
        else:
            print("❌ Failed to post to Slack")
    else:
        print("ℹ️ No contracts expiring within 60 days or expired — all clear!")

if __name__ == "__main__":
    check_contract_expirations()
