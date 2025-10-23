import anthropic
import json
import urllib.request
import urllib.parse
import os

# Get configuration from environment variables
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL = "general"

# Generate Quote with Claude
print("🤖 Asking Claude for a motivational quote...")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[
        {
            "role": "user", 
            "content": "Generate one inspiring motivational quote for a tech recruitment team. Make it uplifting and relevant to their work helping people find careers. Keep it concise (1-2 sentences). Don't include attribution or quotation marks."
        }
    ]
)

quote = message.content[0].text
print(f"✨ Quote generated: {quote}")

# Post to Slack
print(f"📤 Posting to #{SLACK_CHANNEL}...")

slack_message = f"☀️ *Daily Motivation*\n\n{quote}\n\n_Have a great day, team!_"

url = "https://slack.com/api/chat.postMessage"
headers = {
    "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
    "Content-Type": "application/json"
}
data = {
    "channel": SLACK_CHANNEL,
    "text": slack_message,
    "unfurl_links": False
}

req = urllib.request.Request(
    url,
    data=json.dumps(data).encode('utf-8'),
    headers=headers
)

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        if result.get("ok"):
            print("✅ SUCCESS! Quote posted to Slack!")
        else:
            print(f"❌ Error: {result.get('error')}")
except Exception as e:
    print(f"❌ Error posting to Slack: {e}")
