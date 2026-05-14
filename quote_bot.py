import anthropic
import json
import urllib.request
import os
from datetime import datetime, timezone, timedelta
import random

# Configuration
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL = "general"

# ─── QUOTE LIBRARY ────────────────────────────────────────────────────────────
# Organized by theme for balanced rotation — not just work/tech

QUOTES = {
    "life": [
        {"quote": "Life is not measured by the number of breaths we take, but by the moments that take our breath away.", "author": "Maya Angelou"},
        {"quote": "In the end, it's not the years in your life that count. It's the life in your years.", "author": "Abraham Lincoln"},
        {"quote": "The purpose of life is not to be happy. It is to be useful, to be honorable, to be compassionate.", "author": "Ralph Waldo Emerson"},
        {"quote": "Life is what happens when you're busy making other plans.", "author": "John Lennon"},
        {"quote": "You only live once, but if you do it right, once is enough.", "author": "Mae West"},
        {"quote": "Life is really simple, but we insist on making it complicated.", "author": "Confucius"},
        {"quote": "The good life is one inspired by love and guided by knowledge.", "author": "Bertrand Russell"},
        {"quote": "Life shrinks or expands in proportion to one's courage.", "author": "Anaïs Nin"},
        {"quote": "Not all those who wander are lost.", "author": "J.R.R. Tolkien"},
        {"quote": "To live is the rarest thing in the world. Most people just exist.", "author": "Oscar Wilde"},
        {"quote": "Life is short, and it's up to you to make it sweet.", "author": "Sarah Louise Delany"},
        {"quote": "The biggest adventure you can take is to live the life of your dreams.", "author": "Oprah Winfrey"},
    ],

    "courage": [
        {"quote": "You gain strength, courage, and confidence by every experience in which you really stop to look fear in the face.", "author": "Eleanor Roosevelt"},
        {"quote": "Courage is not the absence of fear, but the judgment that something else is more important than fear.", "author": "Ambrose Redmoon"},
        {"quote": "It takes courage to grow up and become who you really are.", "author": "E.E. Cummings"},
        {"quote": "The secret of happiness is freedom, and the secret of freedom is courage.", "author": "Thucydides"},
        {"quote": "Do one thing every day that scares you.", "author": "Eleanor Roosevelt"},
        {"quote": "Bravery is not the absence of fear. It's taking action in spite of it.", "author": "Mark Messier"},
        {"quote": "Fortune favors the bold.", "author": "Latin Proverb"},
        {"quote": "He who is not courageous enough to take risks will accomplish nothing in life.", "author": "Muhammad Ali"},
        {"quote": "It is not the mountain we conquer, but ourselves.", "author": "Sir Edmund Hillary"},
        {"quote": "You are braver than you believe, stronger than you seem, and smarter than you think.", "author": "A.A. Milne"},
    ],

    "wisdom": [
        {"quote": "The more I learn, the more I realize how much I don't know.", "author": "Albert Einstein"},
        {"quote": "Knowing yourself is the beginning of all wisdom.", "author": "Aristotle"},
        {"quote": "The fool doth think he is wise, but the wise man knows himself to be a fool.", "author": "William Shakespeare"},
        {"quote": "By three methods we may learn wisdom: by reflection, by imitation, and by experience.", "author": "Confucius"},
        {"quote": "Turn your wounds into wisdom.", "author": "Oprah Winfrey"},
        {"quote": "The only true wisdom is in knowing you know nothing.", "author": "Socrates"},
        {"quote": "Yesterday I was clever, so I wanted to change the world. Today I am wise, so I am changing myself.", "author": "Rumi"},
        {"quote": "A wise man can learn more from a foolish question than a fool can learn from a wise answer.", "author": "Bruce Lee"},
        {"quote": "The invariable mark of wisdom is to see the miraculous in the common.", "author": "Ralph Waldo Emerson"},
        {"quote": "Wisdom is not a product of schooling but of the lifelong attempt to acquire it.", "author": "Albert Einstein"},
        {"quote": "Wonder is the beginning of wisdom.", "author": "Socrates"},
        {"quote": "Real knowledge is to know the extent of one's ignorance.", "author": "Confucius"},
    ],

    "resilience": [
        {"quote": "The oak fought the wind and was broken, the willow bent when it must and survived.", "author": "Robert Jordan"},
        {"quote": "Fall seven times, stand up eight.", "author": "Japanese Proverb"},
        {"quote": "Out of suffering have emerged the strongest souls; the most massive characters are seared with scars.", "author": "Khalil Gibran"},
        {"quote": "The human capacity for burden is like bamboo — far more flexible than you'd ever believe at first glance.", "author": "Jodi Picoult"},
        {"quote": "Character cannot be developed in ease and quiet. Only through experience of trial and suffering can the soul be strengthened.", "author": "Helen Keller"},
        {"quote": "When everything seems to be going against you, remember that the airplane takes off against the wind, not with it.", "author": "Henry Ford"},
        {"quote": "Rock bottom became the solid foundation on which I rebuilt my life.", "author": "J.K. Rowling"},
        {"quote": "You may have to fight a battle more than once to win it.", "author": "Margaret Thatcher"},
        {"quote": "The comeback is always stronger than the setback.", "author": "Unknown"},
        {"quote": "Every storm runs out of rain.", "author": "Maya Angelou"},
        {"quote": "I am not what happened to me. I am what I choose to become.", "author": "Carl Jung"},
    ],

    "creativity": [
        {"quote": "Creativity is intelligence having fun.", "author": "Albert Einstein"},
        {"quote": "You can't use up creativity. The more you use, the more you have.", "author": "Maya Angelou"},
        {"quote": "Creativity is the greatest rebellion in existence.", "author": "Osho"},
        {"quote": "The creative adult is the child who survived.", "author": "Ursula K. Le Guin"},
        {"quote": "Every child is an artist. The problem is how to remain an artist once we grow up.", "author": "Pablo Picasso"},
        {"quote": "Creativity takes courage.", "author": "Henri Matisse"},
        {"quote": "An idea that is not dangerous is unworthy of being called an idea at all.", "author": "Oscar Wilde"},
        {"quote": "The worst enemy to creativity is self-doubt.", "author": "Sylvia Plath"},
        {"quote": "Think left and think right and think low and think high. Oh, the thinks you can think up if only you try.", "author": "Dr. Seuss"},
        {"quote": "Imagination is the beginning of creation.", "author": "George Bernard Shaw"},
        {"quote": "Logic will get you from A to B. Imagination will take you everywhere.", "author": "Albert Einstein"},
    ],

    "kindness": [
        {"quote": "No act of kindness, no matter how small, is ever wasted.", "author": "Aesop"},
        {"quote": "Be kind, for everyone you meet is fighting a battle you know nothing about.", "author": "Wendy Mass"},
        {"quote": "Kindness is a language which the deaf can hear and the blind can see.", "author": "Mark Twain"},
        {"quote": "The simplest acts of kindness are by far more powerful than a thousand heads bowing in prayer.", "author": "Mahatma Gandhi"},
        {"quote": "Too often we underestimate the power of a touch, a smile, a kind word, a listening ear.", "author": "Leo Buscaglia"},
        {"quote": "We rise by lifting others.", "author": "Robert Ingersoll"},
        {"quote": "A warm smile is the universal language of kindness.", "author": "William Arthur Ward"},
        {"quote": "In a world where you can be anything, be kind.", "author": "Unknown"},
        {"quote": "Carry out a random act of kindness, with no expectation of reward.", "author": "Princess Diana"},
        {"quote": "The best way to find yourself is to lose yourself in the service of others.", "author": "Mahatma Gandhi"},
    ],

    "curiosity": [
        {"quote": "I have no special talents. I am only passionately curious.", "author": "Albert Einstein"},
        {"quote": "The important thing is not to stop questioning. Curiosity has its own reason for existing.", "author": "Albert Einstein"},
        {"quote": "Judge a man by his questions rather than by his answers.", "author": "Voltaire"},
        {"quote": "The cure for boredom is curiosity. There is no cure for curiosity.", "author": "Dorothy Parker"},
        {"quote": "Curiosity is the wick in the candle of learning.", "author": "William Arthur Ward"},
        {"quote": "Stay curious. It will take you places textbooks never could.", "author": "Unknown"},
        {"quote": "We keep moving forward, opening new doors, and doing new things, because we're curious.", "author": "Walt Disney"},
        {"quote": "The mind that opens to a new idea never returns to its original size.", "author": "Albert Einstein"},
        {"quote": "Research is formalized curiosity. It is poking and prying with a purpose.", "author": "Zora Neale Hurston"},
        {"quote": "Curiosity is, in great and generous minds, the first passion and the last.", "author": "Samuel Johnson"},
    ],

    "happiness": [
        {"quote": "Happiness is not something ready-made. It comes from your own actions.", "author": "Dalai Lama"},
        {"quote": "The most important thing is to enjoy your life — to be happy — it's all that matters.", "author": "Audrey Hepburn"},
        {"quote": "Happiness is when what you think, what you say, and what you do are in harmony.", "author": "Mahatma Gandhi"},
        {"quote": "The happiness of your life depends upon the quality of your thoughts.", "author": "Marcus Aurelius"},
        {"quote": "Count your age by friends, not years. Count your life by smiles, not tears.", "author": "John Lennon"},
        {"quote": "Joy is not in things; it is in us.", "author": "Richard Wagner"},
        {"quote": "Happiness is a direction, not a place.", "author": "Sydney J. Harris"},
        {"quote": "The secret of happiness is not in doing what one likes, but in liking what one does.", "author": "James M. Barrie"},
        {"quote": "Very little is needed to make a happy life; it is all within yourself, in your way of thinking.", "author": "Marcus Aurelius"},
        {"quote": "Happiness is not the absence of problems, it's the ability to deal with them.", "author": "Steve Maraboli"},
    ],

    "friendship": [
        {"quote": "A real friend is one who walks in when the rest of the world walks out.", "author": "Walter Winchell"},
        {"quote": "Friendship is the only cement that will ever hold the world together.", "author": "Woodrow Wilson"},
        {"quote": "A friend is someone who knows all about you and still loves you.", "author": "Elbert Hubbard"},
        {"quote": "In the cookie of life, friends are the chocolate chips.", "author": "Salman Rushdie"},
        {"quote": "Good friends, good books, and a sleepy conscience: this is the ideal life.", "author": "Mark Twain"},
        {"quote": "Friendship is born at the moment when one person says to another: 'What! You too? I thought I was the only one.'", "author": "C.S. Lewis"},
        {"quote": "There is nothing I would not do for those who are really my friends.", "author": "Jane Austen"},
        {"quote": "A single rose can be my garden; a single friend, my world.", "author": "Leo Buscaglia"},
        {"quote": "The greatest gift of life is friendship, and I have received it.", "author": "Hubert H. Humphrey"},
    ],

    "philosophy": [
        {"quote": "He who has a why to live can bear almost any how.", "author": "Friedrich Nietzsche"},
        {"quote": "We are what we repeatedly do. Excellence, then, is not an act, but a habit.", "author": "Aristotle"},
        {"quote": "The unexamined life is not worth living.", "author": "Socrates"},
        {"quote": "To be is to do.", "author": "Immanuel Kant"},
        {"quote": "I think therefore I am.", "author": "René Descartes"},
        {"quote": "The measure of a man is what he does with power.", "author": "Plato"},
        {"quote": "Man is condemned to be free.", "author": "Jean-Paul Sartre"},
        {"quote": "God is dead. God remains dead. And we have killed him.", "author": "Friedrich Nietzsche"},
        {"quote": "One cannot step twice in the same river.", "author": "Heraclitus"},
        {"quote": "The only good is knowledge and the only evil is ignorance.", "author": "Socrates"},
        {"quote": "In the depth of winter, I finally learned that within me there lay an invincible summer.", "author": "Albert Camus"},
        {"quote": "He who fights with monsters might take care lest he thereby become a monster.", "author": "Friedrich Nietzsche"},
    ],

    "humor": [
        {"quote": "A day without laughter is a day wasted.", "author": "Charlie Chaplin"},
        {"quote": "If you think you are too small to make a difference, try sleeping with a mosquito.", "author": "Dalai Lama"},
        {"quote": "Before you criticize someone, walk a mile in their shoes. That way, you'll be a mile from them and have their shoes.", "author": "Jack Handey"},
        {"quote": "Two things are infinite: the universe and human stupidity; and I'm not sure about the universe.", "author": "Albert Einstein"},
        {"quote": "People who think they know everything are a great annoyance to those of us who do.", "author": "Isaac Asimov"},
        {"quote": "The trouble with having an open mind, of course, is that people will insist on coming along and trying to put things in it.", "author": "Terry Pratchett"},
        {"quote": "I'm writing a book. I've got the page numbers done.", "author": "Steven Wright"},
        {"quote": "Age is an issue of mind over matter. If you don't mind, it doesn't matter.", "author": "Mark Twain"},
        {"quote": "I find television very educating. Every time somebody turns on the set, I go into the other room and read a book.", "author": "Groucho Marx"},
        {"quote": "Always borrow money from a pessimist. They'll never expect it back.", "author": "Oscar Wilde"},
        {"quote": "I used to think I was indecisive, but now I'm not so sure.", "author": "Unknown"},
    ],

    "nature": [
        {"quote": "In every walk with nature, one receives far more than he seeks.", "author": "John Muir"},
        {"quote": "Look deep into nature, and then you will understand everything better.", "author": "Albert Einstein"},
        {"quote": "The earth does not belong to us. We belong to the earth.", "author": "Chief Seattle"},
        {"quote": "Nature always wears the colors of the spirit.", "author": "Ralph Waldo Emerson"},
        {"quote": "The clearest way into the Universe is through a forest wilderness.", "author": "John Muir"},
        {"quote": "Adopt the pace of nature: her secret is patience.", "author": "Ralph Waldo Emerson"},
        {"quote": "Not all classrooms have four walls.", "author": "Unknown"},
        {"quote": "The ocean stirs the heart, inspires the imagination and brings eternal joy to the soul.", "author": "Robert Wyland"},
        {"quote": "Forget not that the earth delights to feel your bare feet and the winds long to play with your hair.", "author": "Khalil Gibran"},
        {"quote": "One touch of nature makes the whole world kin.", "author": "William Shakespeare"},
    ],

    "monday_boost": [
        {"quote": "Monday is a fresh start. It's never too late to dig in and begin a new journey of success.", "author": "Unknown"},
        {"quote": "This is your Monday morning reminder that you are amazing, and you can handle anything.", "author": "Unknown"},
        {"quote": "Monday is a state of mind. Put on your positive pants.", "author": "Unknown"},
        {"quote": "New week, new goals, new mindset, new focus, same dream.", "author": "Unknown"},
        {"quote": "Coffee in hand, sparkle in my eye, Monday isn't so bad after all.", "author": "Unknown"},
        {"quote": "The secret to getting ahead is getting started. Get after it.", "author": "Mark Twain"},
        {"quote": "Be so good they can't ignore you.", "author": "Steve Martin"},
        {"quote": "Your Monday morning thoughts set the tone for your whole week.", "author": "Unknown"},
    ],

    "friday_vibes": [
        {"quote": "Friday is a state of mind.", "author": "Unknown"},
        {"quote": "Dear Friday, I have been looking for you since Monday.", "author": "Unknown"},
        {"quote": "TGIF: Thank goodness I'm fabulous.", "author": "Unknown"},
        {"quote": "On Fridays we don't just work — we celebrate making it through another incredible week.", "author": "Unknown"},
        {"quote": "You've survived 100% of your worst Mondays. You've got this.", "author": "Unknown"},
        {"quote": "Fridays are the hardest in some ways: you're so close to freedom.", "author": "Lauren Oliver"},
        {"quote": "Every Friday I like to high-five myself for getting through another week.", "author": "Nanea Hoffman"},
        {"quote": "It's Friday! Time to go make stories for Monday.", "author": "Unknown"},
    ],
}

# All themes except day-specific ones — for general rotation
GENERAL_THEMES = [
    "life", "courage", "wisdom", "resilience",
    "creativity", "kindness", "curiosity",
    "happiness", "friendship", "philosophy",
    "humor", "nature"
]

# ─── HISTORY ──────────────────────────────────────────────────────────────────

def load_quote_history():
    try:
        with open('quote_history.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"used_quotes": [], "last_themes": []}

def save_quote_history(history):
    history["used_quotes"] = history["used_quotes"][-60:]
    history["last_themes"] = history["last_themes"][-10:]
    with open('quote_history.json', 'w') as f:
        json.dump(history, f)

# ─── QUOTE SELECTION ──────────────────────────────────────────────────────────

def pick_theme(day_name, history):
    """Pick a theme that hasn't been used recently."""
    if day_name == "Monday":
        return "monday_boost"
    if day_name == "Friday":
        return "friday_vibes"

    recent_themes = history.get("last_themes", [])
    available = [t for t in GENERAL_THEMES if t not in recent_themes[-4:]]
    if not available:
        available = GENERAL_THEMES

    return random.choice(available)

def get_curated_quote(day_name, history):
    """Pick a quote from the library that hasn't been used recently."""
    theme = pick_theme(day_name, history)
    used = set(history.get("used_quotes", []))
    pool = [q for q in QUOTES[theme] if q["quote"] not in used]

    if not pool:
        pool = QUOTES[theme]  # Reset if all used

    selected = random.choice(pool)
    history["last_themes"].append(theme)

    print(f"📚 Theme: {theme} | Author: {selected['author']}")
    return f'"{selected["quote"]}"\n\n— _{selected["author"]}_', selected["quote"], theme

def generate_ai_quote(day_name, history):
    """Use Claude to generate something fresh and unexpected."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    recent = history.get("used_quotes", [])[-15:]
    recent_themes = history.get("last_themes", [])[-5:]
    avoid_themes = ", ".join(recent_themes) if recent_themes else "none"

    content_type = random.choice(["reflection", "humor", "paradox", "story_opener", "question"])

    prompts = {
        "reflection": f"""Write ONE short, original reflective quote (1-2 sentences) about any of these themes: 
        solitude, time, change, memory, identity, gratitude, wonder, simplicity, or purpose.
        Avoid themes recently used: {avoid_themes}.
        Be poetic but accessible. No attribution, no quotes marks, no preamble.""",

        "humor": f"""Write ONE genuinely funny, clever observation about everyday life, human nature, 
        or the quirks of modern existence. 
        Can be a one-liner or a short 2-line joke. 
        Avoid tech/coding jokes. 
        Be witty like Oscar Wilde or Mark Twain. No preamble.""",

        "paradox": f"""Write ONE thought-provoking paradox or counterintuitive truth about life (1-2 sentences).
        Something that makes the reader pause and think.
        Avoid themes recently used: {avoid_themes}.
        No attribution, no quotes marks, no preamble.""",

        "story_opener": f"""Write ONE sentence that feels like the opening of a great story or a profound 
        observation — the kind that makes you stop scrolling. 
        Unexpected, vivid, and memorable.
        No preamble, no attribution.""",

        "question": f"""Write ONE powerful question that makes people reflect on their day, their choices, 
        or their life — but keep it light and curious, not heavy.
        One sentence only. No preamble.""",
    }

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        messages=[{"role": "user", "content": prompts[content_type]}]
    )

    result = message.content[0].text.strip().strip('"').strip("'")
    print(f"🤖 AI generated ({content_type}): {result[:60]}...")
    return result, result, content_type

# ─── SLACK ────────────────────────────────────────────────────────────────────

def post_to_slack(message):
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {"channel": SLACK_CHANNEL, "text": message, "unfurl_links": False}
    req = urllib.request.Request(
        url, data=json.dumps(data).encode('utf-8'), headers=headers
    )
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        return result.get("ok")

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    try:
        manila_tz = timezone(timedelta(hours=8))
        manila_now = datetime.now(manila_tz)
        day_name = manila_now.strftime('%A')
        print(f"📅 Manila time: {manila_now.strftime('%Y-%m-%d %H:%M:%S')} ({day_name})")

        history = load_quote_history()

        # 65% curated, 35% AI-generated
        use_curated = random.random() < 0.65

        if use_curated:
            formatted_quote, raw_quote, theme = get_curated_quote(day_name, history)
        else:
            formatted_quote, raw_quote, theme = generate_ai_quote(day_name, history)

        history["used_quotes"].append(raw_quote)
        save_quote_history(history)

        # Day-specific headers
        headers_map = {
            "Monday":    "🌅 *Monday Spark*",
            "Tuesday":   "💫 *Tuesday Thought*",
            "Wednesday": "🌿 *Midweek Pause*",
            "Thursday":  "🔥 *Thursday Energy*",
            "Friday":    "🎉 *Friday Feeling*",
            "Saturday":  "🌤️ *Weekend Wisdom*",
            "Sunday":    "🪴 *Sunday Reflection*",
        }
        header = headers_map.get(day_name, "✨ *Daily Spark*")

        slack_message = f"{header}\n\n{formatted_quote}\n\n_Have a wonderful day, team!_ 💛"

        print(f"📤 Posting to #{SLACK_CHANNEL}...")
        if post_to_slack(slack_message):
            print("✅ Posted successfully!")
        else:
            print("❌ Failed to post to Slack")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
