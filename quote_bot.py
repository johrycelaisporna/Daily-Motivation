import anthropic
import json
import urllib.request
import urllib.parse
import os
from datetime import datetime

# Get configuration from environment variables
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL = "general"

# Track conversation history to avoid repetition
CONVERSATION_HISTORY = []

def load_quote_history():
    """Load recent quotes from a file to avoid repetition"""
    try:
        with open('quote_history.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_quote_history(quotes):
    """Save quote history to file (keep last 30 quotes)"""
    with open('quote_history.json', 'w') as f:
        json.dump(quotes[-30:], f)  # Keep only last 30 quotes

def generate_unique_quote(previous_quotes):
    """Generate a quote that's different from recent ones"""
    print("🤖 Asking Claude for a motivational quote...")
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Build context about previous quotes to avoid repetition
    context = ""
    if previous_quotes:
        recent_quotes = previous_quotes[-10:]  # Last 10 quotes
        context = f"\n\nAvoid repeating these recent themes and quotes:\n" + "\n".join(f"- {q}" for q in recent_quotes)
    
    prompt = f"""Generate one inspiring motivational quote for a tech recruitment team at Adaca. 

Requirements:
- Make it uplifting and relevant to their work in recruitment, connecting talent with opportunities
- Focus on themes like: impact, growth, perseverance, teamwork, making a difference, or innovation
- Keep it concise (1-2 sentences maximum)
- Make it fresh and unique - avoid clichés
- Don't include attribution, quotation marks, or any preamble
- Vary the style: sometimes use metaphors, sometimes be direct, sometimes be poetic{context}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    
    quote = message.content[0].text.strip()
    return quote

def post_to_slack(message):
    """Post message to Slack"""
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "channel": SLACK_CHANNEL,
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

def main():
    try:
        # Load previous quotes
        quote_history = load_quote_history()
        
        # Generate unique quote
        quote = generate_unique_quote(quote_history)
        print(f"✨ Quote generated: {quote}")
        
        # Add to history
        quote_history.append(quote)
        save_quote_history(quote_history)
        
        # Get day of week for variation
        day_of_week = datetime.now().strftime('%A')
        
        # Vary the greeting based on day
        greetings = {
            'Monday': "☀️ *Monday Motivation*",
            'Tuesday': "💫 *Tuesday Inspiration*",
            'Wednesday': "🌟 *Midweek Motivation*",
            'Thursday': "✨ *Thursday Thoughts*",
            'Friday': "🎉 *Friday Inspiration*",
            'Saturday': "🌅 *Weekend Wisdom*",
            'Sunday': "🌤️ *Sunday Reflection*"
        }
        
        greeting = greetings.get(day_of_week, "☀️ *Daily Motivation*")
        
        # Build Slack message
        slack_message = f"{greeting}\n\n{quote}\n\n_Have a great day, team!_"
        
        # Post to Slack
        print(f"📤 Posting to #{SLACK_CHANNEL}...")
        if post_to_slack(slack_message):
            print("✅ SUCCESS! Quote posted to Slack!")
        else:
            print("❌ Error posting to Slack")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
