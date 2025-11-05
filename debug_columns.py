import os
import json
import urllib.request

MONDAY_API_TOKEN = os.environ.get('MONDAY_API_TOKEN')
BOARD_ID = "6329303796"

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

print("📋 ALL COLUMNS IN BOARD:\n")
for col in result['data']['boards'][0]['columns']:
    print(f"Title: {col['title']}")
    print(f"ID: {col['id']}")
    print(f"Type: {col['type']}")
    print("---")
