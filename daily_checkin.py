import os
import json
import urllib.request
import random
from datetime import datetime, timezone, timedelta

# Configuration
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL = "recruitmentteam-suicidesquad"

# Motivational Quotes
MONDAY_QUOTES = [
    "The only way to do great work is to love what you do. - Steve Jobs",
    "Success is not final, failure is not fatal: it is the courage to continue that counts. - Winston Churchill",
    "Believe you can and you're halfway there. - Theodore Roosevelt",
    "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
    "Start where you are. Use what you have. Do what you can. - Arthur Ashe",
    "Don't watch the clock; do what it does. Keep going. - Sam Levenson",
    "The secret of getting ahead is getting started. - Mark Twain",
    "Your limitation—it's only your imagination.",
    "Great things never come from comfort zones.",
    "Dream it. Wish it. Do it."
]

WEDNESDAY_QUOTES = [
    "In the middle of difficulty lies opportunity. - Albert Einstein",
    "The mind is everything. What you think you become. - Buddha",
    "Life is 10% what happens to you and 90% how you react to it. - Charles R. Swindoll",
    "The only impossible journey is the one you never begin. - Tony Robbins",
    "We cannot solve problems with the kind of thinking we employed when we came up with them. - Albert Einstein",
    "Learn as if you will live forever, live like you will die tomorrow. - Mahatma Gandhi",
    "Stay away from those people who try to disparage your ambitions. Small minds will always do that, but great minds will give you a feeling that you can become great too. - Mark Twain",
    "When you change your thoughts, remember to also change your world. - Norman Vincent Peale",
    "It is only when we take chances, when our lives improve. The initial and the most difficult risk that we need to take is to become honest. - Walter Anderson",
    "Nature has given us all the pieces required to achieve exceptional wellness and health, but has left it to us to put these pieces together. - Diane McLaren"
]

FUN_FACTS = [
    "Octopuses have three hearts and blue blood! 🐙",
    "Honey never spoils. Archaeologists have found 3,000-year-old honey in Egyptian tombs that's still edible! 🍯",
    "A group of flamingos is called a 'flamboyance.' 💗",
    "Bananas are berries, but strawberries aren't! 🍌",
    "The shortest war in history lasted 38 minutes (Anglo-Zanzibar War, 1896). ⏱️",
    "A single cloud can weigh more than 1 million pounds. ☁️",
    "Dolphins have names for each other and can call out to specific dolphins. 🐬",
    "The inventor of the Pringles can is now buried in one. 🥔",
    "There are more stars in the universe than grains of sand on all Earth's beaches. ⭐",
    "A jiffy is an actual unit of time: 1/100th of a second. ⚡",
    "The Philippines has over 7,641 islands! 🏝️",
    "There's a basketball court on the top floor of the U.S. Supreme Court building. It's known as 'The Highest Court in the Land.' 🏀",
    "Sea otters hold hands while sleeping so they don't drift apart. 🦦",
    "The unicorn is Scotland's national animal. 🦄",
    "Your brain uses 20% of your body's energy but only makes up 2% of your body weight. 🧠"
]

def post_to_slack(message):
    """Post message to Slack channel"""
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
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get("ok"):
                return True
            else:
                print(f"Error posting to Slack: {result.get('error')}")
                return False
    except Exception as e:
        print(f"Error posting to Slack: {e}")
        return False

def get_daily_message():
    """Get the appropriate message based on day of week"""
    manila_tz = timezone(timedelta(hours=8))
    today = datetime.now(manila_tz)
    day_name = today.strftime('%A')
    
    print(f"📅 Today is {day_name}, {today.strftime('%B %d, %Y')}")
    
    # Alternate between quotes and fun facts
    all_quotes = MONDAY_QUOTES + WEDNESDAY_QUOTES
    
    if day_name == "Monday":
        quote = random.choice(all_quotes)
        message = f"""🌅 *Good morning, Recruitment Team!*

✨ _{quote}_

💭 *What's your main focus today?*

Drop your answer in the thread below! 👇"""
        
    elif day_name == "Tuesday":
        fact = random.choice(FUN_FACTS)
        message = f"""🌅 *Good morning, Recruitment Team!*

🎯 *Fun Fact of the Day:*
{fact}

💭 *What's your main focus today?*

Share in the thread below! 👇"""
        
    elif day_name == "Wednesday":
        quote = random.choice(all_quotes)
        message = f"""🌅 *Good morning, Recruitment Team!*

💡 _{quote}_

💭 *What's your main focus today?*

Share in the thread below! 👇"""
        
    elif day_name == "Thursday":
        fact = random.choice(FUN_FACTS)
        message = f"""🌅 *Good morning, Recruitment Team!*

🎯 *Fun Fact of the Day:*
{fact}

💭 *What's your main focus today?*

Share in the thread below! 👇"""
        
    elif day_name == "Friday":
        quote = random.choice(all_quotes)
        message = f"""🌅 *Good morning, Recruitment Team!*

🎉 *It's Friday!*

✨ _{quote}_

💭 *What's your main focus today?*

Share in the thread below! 👇"""
        
    else:  # Weekend
        message = f"""🌅 *Good morning, Recruitment Team!*

😎 *Happy {day_name}!*

Enjoy your weekend and recharge! 💪"""
    
    return message

def send_daily_checkin():
    """Send daily check-in message"""
    print("📋 Starting Daily Check-in Bot...")
    
    message = get_daily_message()
    
    if post_to_slack(message):
        print("✅ Daily check-in posted successfully!")
    else:
        print("❌ Failed to post daily check-in")

if __name__ == "__main__":
    send_daily_checkin()
