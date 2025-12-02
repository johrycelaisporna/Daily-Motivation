import anthropic
import json
import urllib.request
import urllib.parse
import os
from datetime import datetime, timezone, timedelta
import random

# Get configuration from environment variables
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL = "general"

# Curated collection of inspirational quotes from famous people
FAMOUS_QUOTES = [
    # Tech Leaders
    {"quote": "The only way to do great work is to love what you do.", "author": "Steve Jobs"},
    {"quote": "Innovation distinguishes between a leader and a follower.", "author": "Steve Jobs"},
    {"quote": "Your work is going to fill a large part of your life, and the only way to be truly satisfied is to do what you believe is great work.", "author": "Steve Jobs"},
    {"quote": "The best way to predict the future is to invent it.", "author": "Alan Kay"},
    {"quote": "Code is like humor. When you have to explain it, it's bad.", "author": "Cory House"},
    {"quote": "First, solve the problem. Then, write the code.", "author": "John Johnson"},
    {"quote": "Any fool can write code that a computer can understand. Good programmers write code that humans can understand.", "author": "Martin Fowler"},
    {"quote": "The most disastrous thing that you can ever learn is your first programming language.", "author": "Alan Kay"},
    {"quote": "Simplicity is the soul of efficiency.", "author": "Austin Freeman"},
    {"quote": "Make it work, make it right, make it fast.", "author": "Kent Beck"},
    
    # Business & Leadership
    {"quote": "The biggest risk is not taking any risk. In a world that's changing quickly, the only strategy that is guaranteed to fail is not taking risks.", "author": "Mark Zuckerberg"},
    {"quote": "Move fast and break things. Unless you are breaking stuff, you are not moving fast enough.", "author": "Mark Zuckerberg"},
    {"quote": "Ideas are easy. Implementation is hard.", "author": "Guy Kawasaki"},
    {"quote": "Don't worry about failure; you only have to be right once.", "author": "Drew Houston"},
    {"quote": "The secret of getting ahead is getting started.", "author": "Mark Twain"},
    {"quote": "Done is better than perfect.", "author": "Sheryl Sandberg"},
    {"quote": "If you're not embarrassed by the first version of your product, you've launched too late.", "author": "Reid Hoffman"},
    {"quote": "Focus is a matter of deciding what things you're not going to do.", "author": "John Carmack"},
    
    # Personal Growth
    {"quote": "Success is not final, failure is not fatal: it is the courage to continue that counts.", "author": "Winston Churchill"},
    {"quote": "The only impossible journey is the one you never begin.", "author": "Tony Robbins"},
    {"quote": "I have not failed. I've just found 10,000 ways that won't work.", "author": "Thomas Edison"},
    {"quote": "Whether you think you can or you think you can't, you're right.", "author": "Henry Ford"},
    {"quote": "The way to get started is to quit talking and begin doing.", "author": "Walt Disney"},
    {"quote": "It's not about ideas. It's about making ideas happen.", "author": "Scott Belsky"},
    {"quote": "Opportunities don't happen. You create them.", "author": "Chris Grosser"},
    {"quote": "The harder I work, the luckier I get.", "author": "Samuel Goldwyn"},
    {"quote": "Don't let yesterday take up too much of today.", "author": "Will Rogers"},
    {"quote": "You learn more from failure than from success. Don't let it stop you. Failure builds character.", "author": "Unknown"},
    {"quote": "It's not whether you get knocked down, it's whether you get up.", "author": "Vince Lombardi"},
    {"quote": "Believe you can and you're halfway there.", "author": "Theodore Roosevelt"},
    {"quote": "The future belongs to those who believe in the beauty of their dreams.", "author": "Eleanor Roosevelt"},
    {"quote": "Do what you can, with what you have, where you are.", "author": "Theodore Roosevelt"},
    
    # Innovation & Creativity
    {"quote": "The best time to plant a tree was 20 years ago. The second best time is now.", "author": "Chinese Proverb"},
    {"quote": "Your time is limited, don't waste it living someone else's life.", "author": "Steve Jobs"},
    {"quote": "Stay hungry, stay foolish.", "author": "Steve Jobs"},
    {"quote": "Life is 10% what happens to you and 90% how you react to it.", "author": "Charles R. Swindoll"},
    {"quote": "The mind is everything. What you think you become.", "author": "Buddha"},
    {"quote": "An unexamined life is not worth living.", "author": "Socrates"},
    {"quote": "Strive not to be a success, but rather to be of value.", "author": "Albert Einstein"},
    {"quote": "Two things are infinite: the universe and human stupidity; and I'm not sure about the universe.", "author": "Albert Einstein"},
    {"quote": "In the middle of difficulty lies opportunity.", "author": "Albert Einstein"},
]

def load_quote_history():
    """Load recent quotes from a file to avoid repetition"""
    try:
        with open('quote_history.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_quote_history(quotes):
    """Save quote history to file (keep last 50 quotes for better tracking)"""
    with open('quote_history.json', 'w') as f:
        json.dump(quotes[-50:], f)

def extract_key_themes(quote):
    """Extract key words/themes from a quote for better comparison"""
    # Remove common words and extract meaningful terms
    common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                   'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'is', 'are'}
    words = quote.lower().split()
    key_words = [w.strip('.,!?;:') for w in words if w.lower() not in common_words and len(w) > 3]
    return ' '.join(key_words[:5])

def get_famous_quote(previous_quotes):
    """Select a famous quote that hasn't been used recently"""
    print("📚 Selecting famous quote...")
    
    # Filter out recently used quotes
    recent_quotes_text = [q.split('\n')[0] if '\n' in q else q for q in previous_quotes[-20:]]
    
    available_quotes = [
        q for q in FAMOUS_QUOTES 
        if q['quote'] not in recent_quotes_text
    ]
    
    if not available_quotes:
        # If all quotes used recently, just pick randomly
        available_quotes = FAMOUS_QUOTES
    
    selected = random.choice(available_quotes)
    formatted_quote = f"{selected['quote']}\n\n— _{selected['author']}_"
    
    print(f"✨ Selected quote from {selected['author']}")
    return formatted_quote

def generate_unique_quote(previous_quotes):
    """Generate a quote/joke that's different from recent ones"""
    print("🤖 Asking Claude for daily inspiration...")
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Build more detailed context about previous content
    context = ""
    if previous_quotes:
        recent_quotes = previous_quotes[-15:]
        context = f"\n\nIMPORTANT: These quotes were recently used. Generate something completely different in theme, wording, and message:\n"
        context += "\n".join(f"- {q}" for q in recent_quotes)
        context += "\n\nDo NOT use similar metaphors, themes, or phrasing. Be creative and fresh!"
    
    # Randomly choose the type of content
    content_type = random.choice(['personal', 'dev', 'joke'])
    
    if content_type == 'personal':
        prompt = f"""Generate ONE inspiring personal growth quote that's completely unique and fresh.

Requirements:
- Topics to explore: resilience, self-discovery, embracing change, learning from failure, building habits, finding balance, courage, patience, authenticity, curiosity, discipline, creativity, perspective
- Keep it concise (1-2 sentences maximum)
- Be original - avoid any overused phrases or clichés
- Use varied approaches: metaphors, paradoxes, questions, observations, challenges
- Don't include attribution, quotation marks, or preamble
- Make it thought-provoking and memorable{context}"""
    
    elif content_type == 'dev':
        prompt = f"""Generate ONE inspiring quote about software development, coding, or technology that's completely unique.

Requirements:
- Topics to explore: debugging mindset, code craftsmanship, learning new tech, collaboration, refactoring, testing, architecture, problem-solving approaches, technical debt, innovation, shipping features, user impact
- Keep it concise (1-2 sentences maximum)
- Be original and fresh - no overused developer sayings
- Can be thoughtful, motivational, or subtly humorous
- Use varied perspectives: technical philosophy, career wisdom, coding insights
- Don't include attribution, quotation marks, or preamble{context}"""
    
    else:  # joke
        prompt = f"""Generate ONE SHORT, clever programming/tech joke or pun that's completely original.

Requirements:
- Keep it super short (1-3 lines max)
- Make it genuinely funny and relatable to developers
- Can be: a one-liner, clever observation, wordplay, or short setup-punchline
- Topics: programming languages, frameworks, debugging, git, APIs, databases, cloud, devops, meetings, documentation, code reviews
- Avoid these overused jokes: "works on my machine", "undefined is not a function", "not a bug it's a feature", "99 bugs in the code"
- Be creative and original - surprise me!{context}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    
    quote = message.content[0].text.strip()
    quote = quote.strip('"').strip("'")
    
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
        
        # Decide whether to use a famous quote or generate one (60% famous, 40% generated)
        use_famous = random.random() < 0.6
        
        if use_famous:
            quote = get_famous_quote(quote_history)
        else:
            # Generate unique quote with retry logic
            max_attempts = 3
            for attempt in range(max_attempts):
                quote = generate_unique_quote(quote_history)
                
                # Check if this quote is too similar to recent ones
                if quote_history:
                    recent_themes = [extract_key_themes(q) for q in quote_history[-10:]]
                    current_theme = extract_key_themes(quote)
                    
                    if current_theme in recent_themes and attempt < max_attempts - 1:
                        print(f"⚠️  Similar theme detected, regenerating (attempt {attempt + 1}/{max_attempts})...")
                        continue
                
                break
        
        print(f"✨ Final quote: {quote[:60]}...")
        
        # Add to history
        quote_history.append(quote)
        save_quote_history(quote_history)
        
        # Get Manila time
        utc_now = datetime.now(timezone.utc)
        manila_tz = timezone(timedelta(hours=8))
        manila_now = utc_now.astimezone(manila_tz)
        day_of_week = manila_now.strftime('%A')
        
        print(f"📅 Manila time: {manila_now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📅 Day: {day_of_week}")
        
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
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
