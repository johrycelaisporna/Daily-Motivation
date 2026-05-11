import os
import json
import urllib.request
import random
from datetime import datetime, timezone, timedelta

# Configuration
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL = "recruitmentteam-suicidesquad"

# ─── QUOTES ───────────────────────────────────────────────────────────────────

QUOTES_RESILIENCE = [
    "Fall seven times, stand up eight. — Japanese Proverb",
    "It's not whether you get knocked down, it's whether you get up. — Vince Lombardi",
    "The comeback is always stronger than the setback.",
    "You were given this life because you are strong enough to live it.",
    "Hard times never last, but hard people do. — Robert H. Schuller",
    "Every storm runs out of rain. — Maya Angelou",
    "Rock bottom became the solid foundation on which I rebuilt my life. — J.K. Rowling",
    "Out of difficulties grow miracles. — Jean de la Bruyère",
    "The human capacity for burden is like bamboo — far more flexible than you'd ever believe at first glance. — Jodi Picoult",
    "Strength doesn't come from what you can do. It comes from overcoming the things you once thought you couldn't.",
]

QUOTES_GROWTH = [
    "The expert in anything was once a beginner.",
    "Every day is a chance to be better than yesterday.",
    "Growth is never by mere chance; it is the result of forces working together. — James Cash Penney",
    "You don't have to be great to start, but you have to start to be great. — Zig Ziglar",
    "Be not afraid of growing slowly; be afraid only of standing still. — Chinese Proverb",
    "What you get by achieving your goals is not as important as what you become by achieving them. — Zig Ziglar",
    "The only person you are destined to become is the person you decide to be. — Ralph Waldo Emerson",
    "Invest in yourself. Your career is the engine of your wealth. — Paul Clitheroe",
    "Comfort is the enemy of achievement. — Farrah Gray",
    "Small steps in the right direction can turn out to be the biggest step of your life.",
]

QUOTES_TEAMWORK = [
    "Alone we can do so little; together we can do so much. — Helen Keller",
    "Coming together is a beginning, staying together is progress, and working together is success. — Henry Ford",
    "Talent wins games, but teamwork and intelligence win championships. — Michael Jordan",
    "None of us is as smart as all of us. — Ken Blanchard",
    "Great teams don't hold back with each other. They are unafraid to air their dirty laundry. — Patrick Lencioni",
    "The strength of the team is each individual member. The strength of each member is the team. — Phil Jackson",
    "If everyone is moving forward together, then success takes care of itself. — Henry Ford",
    "You don't have to be the best, just bring your best — your team will do the rest.",
    "Collaboration allows teachers to capture each other's fund of collective intelligence. — Mike Schmoker",
    "Individual commitment to a group effort — that is what makes a team work. — Vince Lombardi",
]

QUOTES_RECRUITMENT = [
    "Hiring the right people takes time, the right questions and a healthy dose of curiosity. — Richard Branson",
    "Every great business is built on friendship. — J.C. Penney",
    "People are not your most important asset. The right people are. — Jim Collins",
    "The secret of my success is that we have gone to exceptional lengths to hire the best people in the world. — Steve Jobs",
    "You can have the best strategy in the world, but if you don't have the right people, it won't matter. — Jack Welch",
    "Recruiting is hard. It's just finding the needles in the haystack. — Steve Jobs",
    "A players hire A players; B players hire C players. — Steve Jobs",
    "Culture eats strategy for breakfast. — Peter Drucker",
    "Your culture is your brand. — Tony Hsieh",
    "Train people well enough so they can leave, treat them well enough so they don't want to. — Richard Branson",
]

QUOTES_MINDSET = [
    "Whether you think you can, or you think you can't — you're right. — Henry Ford",
    "The mind is everything. What you think you become. — Buddha",
    "Your mindset is your most powerful tool — sharpen it daily.",
    "Optimism is the faith that leads to achievement. — Helen Keller",
    "Once your mindset changes, everything on the outside will change along with it. — Steve Maraboli",
    "You are what you repeatedly do. Excellence, then, is not an act, but a habit. — Aristotle",
    "The only limits that exist are the ones you place on yourself.",
    "If you change the way you look at things, the things you look at change. — Wayne Dyer",
    "A positive mind finds opportunity in everything. A negative mind finds fault in everything.",
    "Energy is contagious — positive and negative alike. Spread the good stuff. — Tom Hiddleston",
]

QUOTES_FRIDAY = [
    "Friday is a state of mind.",
    "It's Friday! Time to go make stories for Monday. — Unknown",
    "Every Friday, I like to high-five myself for getting through another week on little more than caffeine, determination, and sheer stubbornness. — Nanea Hoffman",
    "On Fridays, we don't just work — we celebrate making it through another incredible week.",
    "Friday: the golden child of the weekdays.",
    "Dear Friday, I have been looking for you since Monday. — Unknown",
    "Life is too short not to celebrate every Friday like it's a holiday.",
    "Friday sees more smiles than any other day of the workweek. — Kate Summers",
    "You've worked hard all week — now let Friday remind you how capable you truly are.",
    "TGIF: Thank goodness I'm fantastic. 😄",
]

# ─── FUN FACTS ────────────────────────────────────────────────────────────────

FUN_FACTS_NATURE = [
    "Octopuses have three hearts, blue blood, and can taste with their arms. 🐙",
    "A single bolt of lightning contains enough energy to toast 100,000 slices of bread. ⚡",
    "Honey never spoils — archaeologists found 3,000-year-old honey in Egyptian tombs that's still edible! 🍯",
    "A group of flamingos is called a 'flamboyance.' 💗",
    "Bananas are berries, but strawberries aren't! 🍌",
    "Sea otters hold hands while sleeping so they don't drift apart. 🦦",
    "A day on Venus is longer than a year on Venus. 🪐",
    "Crows can recognize human faces and hold grudges against people who were mean to them. 🐦‍⬛",
    "Elephants are the only animals that can't jump — and they're perfectly fine with that. 🐘",
    "Trees in a forest communicate and share nutrients through an underground fungal network called the 'Wood Wide Web.' 🌳",
]

FUN_FACTS_HUMAN_BODY = [
    "Your brain uses 20% of your body's energy but only makes up 2% of your body weight. 🧠",
    "The human nose can detect over 1 trillion different scents. 👃",
    "Your bones are about 5 times stronger than steel of the same density. 💪",
    "The human eye can distinguish about 10 million different colors. 👁️",
    "Goosebumps are an evolutionary leftover from when our ancestors had more body hair — they made them look bigger as a threat display. 🦶",
    "Your stomach gets a completely new lining every 3 to 4 days. 🫀",
    "The cornea is the only tissue in the body with no blood supply — it gets oxygen directly from the air. 👁️",
    "Laughing 100 times is roughly equivalent to 10 minutes on a rowing machine. 😂",
    "Your heart beats about 100,000 times per day — that's 3 billion times in a lifetime. ❤️",
    "Humans are the only animals known to blush. 😊",
]

FUN_FACTS_HISTORY = [
    "The shortest war in history lasted 38 minutes — the Anglo-Zanzibar War of 1896. ⏱️",
    "Cleopatra lived closer in time to the Moon landing than to the construction of the Great Pyramid. 🏛️",
    "Oxford University is older than the Aztec Empire. 📚",
    "Nintendo was founded in 1889 — originally as a playing card company. 🃏",
    "The first alarm clock could only ring at 4 a.m. — and it was specifically made for one person. ⏰",
    "Vikings didn't actually wear horned helmets — that's a myth popularized by 19th-century artists. 🪖",
    "Ancient Egyptians used to shave off their eyebrows as a sign of mourning when their cat died. 🐱",
    "The Great Wall of China isn't visible from space with the naked eye — that's been officially debunked. 🌍",
    "Forks were once considered blasphemous and were banned in some parts of medieval Europe. 🍴",
    "The unicorn is Scotland's national animal. 🦄",
]

FUN_FACTS_PHILIPPINES = [
    "The Philippines has over 7,641 islands — the exact number changes depending on the tide! 🏝️",
    "The Philippines is the only country in Asia with a majority Christian population. ✝️",
    "Jeepneys — the iconic Filipino public transport — were originally made from US military jeeps left after WWII. 🚌",
    "The yo-yo was invented in the Philippines and brought to the US in the 1920s by Pedro Flores. 🪀",
    "Filipino is the only language in Southeast Asia written in the Latin alphabet as its standard script. 📝",
    "The Philippines is one of the world's top exporters of nurses. 👩‍⚕️",
    "Boracay's White Beach was voted one of the best beaches in the world multiple times. 🏖️",
    "The Philippines has the longest Christmas season in the world — some malls start playing carols in September! 🎄",
    "José Rizal, the Philippines' national hero, spoke over 20 languages. 🗣️",
    "The Philippines is home to the world's smallest volcano — the Taal Volcano, which sits on an island inside a lake, inside an island! 🌋",
]

FUN_FACTS_WORK_OFFICE = [
    "The average person spends 90,000 hours at work over their lifetime — make them count! 💼",
    "Smiling, even when forced, can actually improve your mood. So fake it till you make it really works. 😄",
    "People are most creative right after waking up — which might explain those 9 AM ideas. 💡",
    "Listening to music while working can boost productivity by up to 15%. 🎧",
    "The average person checks their phone 96 times a day — that's once every 10 minutes. 📱",
    "A tidy desk can increase productivity by up to 84% according to some studies. 🗂️",
    "Taking a short walk before a meeting boosts creative thinking by 81%. 🚶",
    "The 'two-minute rule' says: if a task takes less than two minutes, do it now. ⏳",
    "Teams that laugh together are 27% more productive, according to research by Bain & Company. 😂",
    "Writing down your goals makes you 42% more likely to achieve them. ✍️",
]

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def get_quote(day_name):
    if day_name == "Monday":
        pool = QUOTES_RESILIENCE + QUOTES_MINDSET
    elif day_name == "Wednesday":
        pool = QUOTES_GROWTH + QUOTES_TEAMWORK
    elif day_name == "Friday":
        pool = QUOTES_FRIDAY
    else:
        pool = QUOTES_RECRUITMENT + QUOTES_MINDSET + QUOTES_GROWTH
    return random.choice(pool)

def get_fun_fact():
    all_facts = (
        FUN_FACTS_NATURE +
        FUN_FACTS_HUMAN_BODY +
        FUN_FACTS_HISTORY +
        FUN_FACTS_PHILIPPINES +
        FUN_FACTS_WORK_OFFICE
    )
    return random.choice(all_facts)

# ─── SLACK ────────────────────────────────────────────────────────────────────

def post_to_slack(message):
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

# ─── MESSAGES ─────────────────────────────────────────────────────────────────

def get_daily_message():
    manila_tz = timezone(timedelta(hours=8))
    today = datetime.now(manila_tz)
    day_name = today.strftime('%A')
    date_str = today.strftime('%B %d, %Y')

    print(f"📅 Today is {day_name}, {date_str}")

    if day_name == "Monday":
        quote = get_quote("Monday")
        message = f"""🌅 *Good morning, Recruitment Team! Happy Monday!* 

💪 *Kick off the week with this:*
✨ _{quote}_

💭 *What's your #1 focus this week?*
Drop it in the thread — let's hold each other accountable! 👇"""

    elif day_name == "Tuesday":
        fact = get_fun_fact()
        message = f"""🌅 *Good morning, Recruitment Team!*

🎯 *Did you know?*
{fact}

💭 *What's your main focus today?*
Share in the thread below! 👇"""

    elif day_name == "Wednesday":
        quote = get_quote("Wednesday")
        message = f"""🌅 *Good morning, Recruitment Team! Halfway there! 🐪*

💡 *Midweek reminder:*
✨ _{quote}_

💭 *How's the week going so far? Any wins to share?*
Drop them in the thread! 👇"""

    elif day_name == "Thursday":
        fact = get_fun_fact()
        message = f"""🌅 *Good morning, Recruitment Team!*

🧠 *Fun Fact Thursday:*
{fact}

💭 *One more day — what do you need to wrap up before Friday?*
Share in the thread! 👇"""

    elif day_name == "Friday":
        quote = get_quote("Friday")
        message = f"""🌅 *Good morning, Recruitment Team! It's FRIDAY!* 🎉

✨ _{quote}_

🏆 *Before you head into the weekend — drop one WIN from this week in the thread!*
Big or small, every win counts. 👇"""

    else:
        message = f"""🌅 *Good morning, Recruitment Team!*

😎 *Happy {day_name}!*
Rest up, recharge, and come back stronger. You've earned it. 💪"""

    return message

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def send_daily_checkin():
    print("📋 Starting Daily Check-in Bot...")
    message = get_daily_message()
    if post_to_slack(message):
        print("✅ Daily check-in posted successfully!")
    else:
        print("❌ Failed to post daily check-in")

if __name__ == "__main__":
    send_daily_checkin()
