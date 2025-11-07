import os
import json
import urllib.request

MONDAY_API_TOKEN = os.environ.get('MONDAY_API_TOKEN')
BOARD_ID = "6239668497"

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

# Get board columns
print("=" * 60)
print("BOARD COLUMNS")
print("=" * 60)

query = f'''
{{
  boards(ids: {BOARD_ID}) {{
    columns {{
      id
      title
      type
    }}
  }}
}}
'''

result = query_monday(query)

print("\n📋 ALL COLUMNS IN JOBS BOARD:\n")
for col in result['data']['boards'][0]['columns']:
    print(f"Title: {col['title']}")
    print(f"ID: {col['id']}")
    print(f"Type: {col['type']}")
    print("---")

# Get sample data from Active Recruitment group
print("\n" + "=" * 60)
print("SAMPLE JOB DATA (First job in Active Recruitment)")
print("=" * 60)

query = f'''
{{
  boards(ids: {BOARD_ID}) {{
    groups {{
      title
      items_page(limit: 1) {{
        items {{
          name
          column_values {{
            id
            text
          }}
        }}
      }}
    }}
  }}
}}
'''

result = query_monday(query)

for group in result['data']['boards'][0]['groups']:
    if group['title'] == 'Active Recruitment':
        items = group['items_page']['items']
        if items:
            job = items[0]
            print(f"\nJob: {job['name']}\n")
            for col in job['column_values']:
                if col['text']:
                    print(f"[{col['id']}]: {col['text']}")
        break
