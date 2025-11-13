import anthropic
import json
import urllib.request
import urllib.parse
import os
from datetime import datetime, timezone, timedelta

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
    """Generate a quote/joke that's different from recent ones"""
    print("🤖 Asking Claude for daily inspiration...")
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Build context about previous content to avoid repetition
    context = ""
    if previous_quotes:
        recent_quotes = previous_quotes[-10:]  # Last 10 items
        context = f"\n\nAvoid repeating these recent themes, topics, and content:\n" + "\n".join(f"- {q}" for q in recent_quotes)
    
    # Randomly choose the type of content
    import random
    content_type = random.choice(['personal', 'dev', 'joke'])
    
    if content_type == 'personal':
        prompt = f"""Generate one inspiring personal growth quote that applies to anyone. 

Requirements:
- Make it about: personal growth, resilience, mindset, overcoming challenges, self-improvement, finding purpose, or inner strength
- Keep it concise (1-2 sentences maximum)
- Make it fresh and unique - avoid clichés
- Don't include attribution, quotation marks, or any preamble
- Vary the style: sometimes use metaphors, sometimes be direct, sometimes be poetic{context}"""
    
    elif content_type == 'dev':
        prompt = f"""Generate one inspiring quote about software development, coding, or technology. 

Requirements:
- Make it about: coding mindset, problem-solving, debugging life, continuous learning, building things, innovation, or tech culture
- Keep it concise (1-2 sentences maximum)
- Make it fresh and unique - avoid clichés
- Don't include attribution, quotation marks, or any preamble
- Can be thoughtful or slightly humorous{context}"""
    
    else:  # joke
        prompt = f"""Generate one SHORT, clever programming/tech joke or pun. 

Requirements:
- Keep it super short (1-3 lines max)
- Make it actually funny and relatable to developers/tech people
- Can be a one-liner, a short setup-punchline, or a clever observation
- Avoid overused jokes like "works on my machine" or "undefined is not a function"
- Don't explain the joke or add commentary
- Fresh and original{context}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    
    quote = message.content[0].text.strip()
    print(f"📝 Generated {content_type} content")
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
        
        # Get Manila time properly
        utc_now = datetime.now(timezone.utc)
        manila_tz = timezone(timedelta(hours=8))
        manila_now = utc_now.astimezone(manila_tz)
        day_of_week = manila_now.strftime('%A')
        
        print(f"📅 UTC time: {utc_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"📅 Manila time: {manila_now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📅 Day of week: {day_of_week}")
        
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
