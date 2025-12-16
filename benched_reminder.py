#!/usr/bin/env python3
"""
Benched Employees Reminder Bot
Fetches benched employees from Monday.com and posts to Slack
"""

import requests
import json
import os
from datetime import datetime

# Monday.com API configuration
MONDAY_API_URL = "https://api.monday.com/v2"
MONDAY_TOKEN = os.environ.get('MONDAY_API_TOKEN')
BOARD_ID = "6329303796"
GROUP_TITLE = "Not Active Employees (Bench)"  # Search by group title instead

# Slack bot token
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL = "#benched-employees"

def fetch_benched_employees():
    """Fetch items from the benched employees group in Monday.com"""
    
    # Query to get all groups and find the one with matching title
    # Include assets to get file URLs
    query = """
    query {
      boards(ids: %s) {
        groups {
          id
          title
          items_page {
            items {
              name
              assets {
                id
                name
                url
                public_url
              }
              column_values {
                id
                text
                value
                type
              }
            }
          }
        }
      }
    }
    """ % BOARD_ID

    headers = {
        "Authorization": MONDAY_TOKEN,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            MONDAY_API_URL,
            headers=headers,
            json={"query": query},
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Find the group with matching title
        groups = data.get('data', {}).get('boards', [{}])[0].get('groups', [])
        
        target_group = None
        for group in groups:
            if group.get('title') == GROUP_TITLE:
                target_group = group
                break
        
        if not target_group:
            print(f"Warning: Group '{GROUP_TITLE}' not found")
            print(f"Available groups: {[g.get('title') for g in groups]}")
            return []
        
        print(f"Found group: {target_group.get('title')} (ID: {target_group.get('id')})")
        
        items = target_group.get('items_page', {}).get('items', [])
        
        # Extract employee details with column values
        benched_employees = []
        for item in items:
            if not item.get('name'):
                continue
                
            employee = {
                'name': item['name'],
                'project': '',
                'position': '',
                'branch': '',
                'contract_end': '',
                'cv_files': []
            }
            
            # Parse column values - ENABLE DEBUGGING
            print(f"\n{'='*60}")
            print(f"Employee: {item['name']}")
            print(f"{'='*60}")
            
            # First, check if there are assets (files) directly on the item
            assets = item.get('assets', [])
            if assets:
                print(f"Found {len(assets)} assets attached to item")
                for asset in assets:
                    file_url = asset.get('public_url') or asset.get('url') or ''
                    file_name = asset.get('name', 'Document')
                    if file_url:
                        employee['cv_files'].append({
                            'name': file_name,
                            'url': file_url
                        })
                        print(f"  >>> Added asset: {file_name} - {file_url[:50]}...")
            
            for col in item.get('column_values', []):
                col_id = col.get('id', '')
                col_text = col.get('text', '')
                col_value = col.get('value', '')
                col_type = col.get('type', '')
                
                # Print ALL columns for debugging
                print(f"Column ID: '{col_id}'")
                print(f"  Type: {col_type}")
                print(f"  Text: {col_text}")
                if col_value and len(col_value) < 200:
                    print(f"  Value: {col_value}")
                print()
                
                # Map columns (case-insensitive matching)
                col_id_lower = col_id.lower()
                
                if col_id_lower == 'project' or col_text == 'Project':
                    employee['project'] = col_text
                elif col_id_lower == 'position' or 'position' in col_id_lower:
                    employee['position'] = col_text
                elif col_id_lower == 'branch' or 'branch' in col_id_lower:
                    employee['branch'] = col_text
                elif 'contract' in col_id_lower or 'end' in col_id_lower or 'date' in col_id_lower:
                    if col_text:
                        employee['contract_end'] = col_text
                
                # Check file columns and extract asset IDs
                if col_type == 'file' or 'cv' in col_id_lower or 'adaca' in col_id_lower:
                    try:
                        if col_value and col_value != '':
                            files_data = json.loads(col_value)
                            print(f"  >>> Found file column! Data: {files_data}")
                            
                            # If we didn't get files from assets, try to extract from column value
                            if isinstance(files_data, dict) and 'files' in files_data and not employee['cv_files']:
                                for file_info in files_data['files']:
                                    # Try to match with assets by name or ID
                                    file_name = file_info.get('name', 'CV')
                                    asset_id = file_info.get('assetId') or file_info.get('id')
                                    
                                    # Try to find matching asset
                                    matched_asset = None
                                    if asset_id and assets:
                                        for asset in assets:
                                            if str(asset.get('id')) == str(asset_id):
                                                matched_asset = asset
                                                break
                                    
                                    if matched_asset:
                                        file_url = matched_asset.get('public_url') or matched_asset.get('url') or ''
                                        if file_url:
                                            employee['cv_files'].append({
                                                'name': file_name,
                                                'url': file_url
                                            })
                                            print(f"  >>> Matched asset: {file_name} - {file_url[:50]}...")
                                    else:
                                        # No URL found
                                        employee['cv_files'].append({
                                            'name': file_name,
                                            'url': None
                                        })
                                        print(f"  >>> File without URL: {file_name}")
                    except (json.JSONDecodeError, TypeError) as e:
                        print(f"  >>> Error parsing file: {e}")
            
            print(f"\nFinal employee data:")
            print(f"  Project: {employee['project']}")
            print(f"  Position: {employee['position']}")
            print(f"  Branch: {employee['branch']}")
            print(f"  Contract End: {employee['contract_end']}")
            print(f"  CV Files: {len(employee['cv_files'])} found")
            
            benched_employees.append(employee)
        
        return benched_employees
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Monday.com data: {e}")
        raise
    except (KeyError, IndexError, TypeError) as e:
        print(f"Error parsing Monday.com response: {e}")
        print(f"Response data: {json.dumps(data, indent=2)}")
        raise

def send_slack_notification(benched_employees):
    """Send notification to Slack with list of benched employees"""
    
    current_date = datetime.now().strftime("%B %d, %Y")
    
    if benched_employees:
        # Create formatted table
        employee_details = []
        for emp in benched_employees:
            details = f"*{emp['name']}*\n"
            details += f"  └ Project: {emp['project'] or 'N/A'}\n"
            details += f"  └ Position: {emp['position'] or 'N/A'}\n"
            details += f"  └ Branch: {emp['branch'] or 'N/A'}\n"
            details += f"  └ Contract End: {emp['contract_end'] or 'N/A'}"
            
            # Add CV files if any
            if emp['cv_files']:
                details += "\n  └ Adaca CV:"
                for file in emp['cv_files']:
                    if file['url']:
                        # Clickable link if URL exists
                        details += f"\n     • <{file['url']}|{file['name']}>"
                    else:
                        # Just show filename if no URL
                        details += f"\n     • {file['name']} (Contact HR for access)"
            
            employee_details.append(details)
        
        employee_list = "\n\n".join(employee_details)
        
        message = f"""
:warning: *Benched Employees Report - {current_date}*

The following employees are currently on the bench:

{employee_list}

*Total: {len(benched_employees)} employee(s)*

_Please review and take appropriate action._
"""
    else:
        message = f"""
:white_check_mark: *Benched Employees Report - {current_date}*

Great news! There are currently no employees on the bench.
"""

    # Use Slack API with bot token
    slack_url = "https://slack.com/api/chat.postMessage"
    
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "channel": SLACK_CHANNEL,
        "text": message,
        "mrkdwn": True
    }

    try:
        response = requests.post(
            slack_url,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        
        if not result.get('ok'):
            error_msg = result.get('error', 'Unknown error')
            raise Exception(f"Slack API error: {error_msg}")
        
        print(f"✓ Successfully sent notification to Slack")
        print(f"✓ Found {len(benched_employees)} benched employee(s)")
        
    except requests.exceptions.RequestException as e:
        print(f"Error sending to Slack: {e}")
        raise
    except Exception as e:
        print(f"Slack API error: {e}")
        raise

def main():
    """Main execution function"""
    
    # Validate environment variables
    if not MONDAY_TOKEN:
        raise ValueError("MONDAY_API_TOKEN environment variable not set")
    if not SLACK_BOT_TOKEN:
        raise ValueError("SLACK_BOT_TOKEN environment variable not set")
    
    print("Fetching benched employees from Monday.com...")
    benched_employees = fetch_benched_employees()
    
    print(f"Found {len(benched_employees)} benched employee(s)")
    
    print("Sending notification to Slack...")
    send_slack_notification(benched_employees)
    
    print("Done!")

if __name__ == "__main__":
    main()
