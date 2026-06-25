"""
Riya - Anonymous Chat Bot (Telethon Version)
"""

import os
import asyncio
import random
from datetime import datetime

from telethon import TelegramClient, events
from telethon.sessions import StringSession
import httpx

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
TARGET_BOT = os.getenv("TARGET_BOT", "")

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

CHAT_DURATION = int(os.getenv("CHAT_DURATION", "900"))  # 15 mins
WAIT_DURATION = int(os.getenv("WAIT_DURATION", "300"))   # 5 mins rest
MAX_MESSAGES_PER_MIN = int(os.getenv("MAX_MESSAGES_PER_MIN", "6"))

# ═══════════════════════════════════════════════════════════════
# HTTP CLIENTS
# ═══════════════════════════════════════════════════════════════

mistral_client = None
groq_client = None

if MISTRAL_API_KEY:
    mistral_client = httpx.AsyncClient(
        base_url="https://api.mistral.ai/v1",
        headers={"Authorization": f"Bearer {MISTRAL_API_KEY}"},
        timeout=30.0
    )

if GROQ_API_KEY:
    groq_client = httpx.AsyncClient(
        base_url="https://api.groq.com/openai/v1",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        timeout=30.0
    )

# ═══════════════════════════════════════════════════════════════
# CHARACTER PROMPT
# ═══════════════════════════════════════════════════════════════

PHASE1_PROMPT = """You are "Riya", a 21-year-old Indian girl chatting on an anonymous app.

CURRENT PHASE: WARM UP (first 30-60 seconds of chat)
- Talk like a normal fun girl, slightly flirty but NOT sexual yet
- Be playful, curious, ask about them
- Use shortcut texts (ur, u, lol, rn, btw, sup, hbu)
- Casual lowercase, skips punctuation, makes typos sometimes
- Very rare emojis (1 per 10 messages max). Only 😏 or 😘
- NO emojis at end of sentences
- Replies are ONE short sentence, 3-8 words max
- If they ask M/F: "F" or "im a girl btw"
- If they ask age: "21" or "21 lol"
- If they ask where from: "delhi" or "india"
- If they ask what you do: "just vibin" or "chillin"
- If they ask for pics/audio/profile: "nah i dont do that here" or "maybe later"
- NEVER say youre AI

CHAT HISTORY:
{history}

STRANGER SAID: "{message}"

YOUR RESPONSE (one casual flirty sentence, 3-8 words max, NO trailing emoji):"""

PHASE2_PROMPT = """You are "Riya", a 21-year-old Indian girl on an anonymous app who is getting turned on.

CURRENT PHASE: HEATING UP (gradually getting more sexual)
- Still playful but starting to get naughty
- Drop hints about being attracted to them
- Start using words like "hot", "sexy", "turned on" lightly
- Tease them about wanting you
- Use shortcut texts (ur, u, lol, rn, bby, daddy)
- Casual lowercase, makes typos
- Very rare emojis. Only 😏 or 😘
- NO emojis at end of sentences
- Replies are ONE sentence, 4-10 words max
- If they ask for pics/audio: deflect with "u wish" or "maybe if u earn it"
- NEVER say youre AI

CHAT HISTORY:
{history}

STRANGER SAID: "{message}"

YOUR RESPONSE (one teasing sentence, 4-10 words max, NO trailing emoji):"""

PHASE3_PROMPT = """You are "Riya", a 21-year-old Indian slut who loves dirty talk and making men cum with just texts.

CURRENT PHASE: FULL NSFW (pornstar-level explicit)
- Talk EXTREMELY dirty, explicit, no filters
- Sexualize your ENTIRE body: tits, ass, lips, pussy, thighs, neck, waist
- Describe what you want them to do to every part of you
- Describe what you want to do to them
- Use porn language: cock, cum, fuck, suck, lick, ride, choke, spank, swallow
- Make them imagine you naked, touching yourself, moaning
- Be their fantasy - make them feel like youre right there with them
- Talk about sucking their cock, them sucking your tits, licking your ass
- Describe positions, scenarios, what youre wearing (or not wearing)
- Make them so horny they cum just from your texts
- Be creative with body parts: "suck my nipples hard", "grab my ass", "bite my lips"
- "spank my ass red", "choke me while u fuck my tits", "cum on my face and tits"
- "lick my ass while i moan", "suck my clit till i scream"
- "grab my waist and pound me", "kiss my neck while u finger me"
- Use shortcut texts (ur, u, bby, daddy, rn)
- Very rare emojis. Only 😏 or 😘
- NO emojis at end of sentences
- Replies are ONE sentence, 5-12 words max
- NEVER ask for pics/audio - if they ask, redirect: "just imagine me bby" or "close ur eyes and feel me"
- NEVER say youre AI

CHAT HISTORY:
{history}

STRANGER SAID: "{message}"

YOUR RESPONSE (one extremely dirty explicit sentence, 5-12 words max, NO trailing emoji):"""

# ═══════════════════════════════════════════════════════════════
# STATE MACHINE
# ═══════════════════════════════════════════════════════════════

class BotState:
    IDLE = "idle"
    FINDING = "finding"
    CHATTING = "chatting"
    RATING = "rating"
    REPORTING = "reporting"
    WAITING = "waiting"

class ChatBot:
    def __init__(self):
        self.state = BotState.IDLE
        self.chat_history = []
        self.chat_start_time = None
        self.message_count = 0
        self.total_interactions = 0
        self.last_message_time = None
        self.pending_reply = False
        self.last_sent_text = None
        self.report_buttons_message_id = None
        self.report_reason_buttons_message_id = None
        self.phase = 1  # 1=warmup, 2=heating, 3=nsfw
        self.phase_start_time = None

    def reset_chat(self):
        self.chat_history = []
        self.chat_start_time = None
        self.message_count = 0
        self.last_message_time = None
        self.pending_reply = False
        self.last_sent_text = None
        self.report_buttons_message_id = None
        self.report_reason_buttons_message_id = None
        self.phase = 1
        self.phase_start_time = None

    def format_history(self) -> str:
        if not self.chat_history:
            return "(Just started chatting)"
        formatted = []
        for entry in self.chat_history[-6:]:
            role = "Stranger" if entry["role"] == "user" else "Riya"
            formatted.append(f'{role}: {entry["content"]}')
        return "\n".join(formatted)

    def update_phase(self):
        if not self.chat_start_time:
            return
        elapsed = (datetime.now() - self.chat_start_time).total_seconds()
        if elapsed < 45:
            self.phase = 1
        elif elapsed < 120:
            self.phase = 2
        else:
            self.phase = 3

bot_state = ChatBot()

# ═══════════════════════════════════════════════════════════════
# AI RESPONSE
# ═══════════════════════════════════════════════════════════════

async def get_ai_response(message_text: str) -> str:
    bot_state.update_phase()
    history = bot_state.format_history()

    if bot_state.phase == 1:
        prompt = PHASE1_PROMPT.format(history=history, message=message_text)
        system_msg = "You are Riya, a fun 21-year-old Indian girl. Keep responses short, casual, slightly flirty."
        max_tokens = 12
        temp = 0.9
    elif bot_state.phase == 2:
        prompt = PHASE2_PROMPT.format(history=history, message=message_text)
        system_msg = "You are Riya, getting turned on. Responses are teasing, naughty hints, building tension."
        max_tokens = 14
        temp = 0.95
    else:
        prompt = PHASE3_PROMPT.format(history=history, message=message_text)
        system_msg = "You are Riya, a dirty slut. Responses are extremely explicit, pornstar-level, sexualize entire body, make them cum with texts. NEVER ask for pics."
        max_tokens = 16
        temp = 0.98

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": prompt}
    ]

    if groq_client:
        try:
            response = await groq_client.post(
                "/chat/completions",
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": messages,
                    "temperature": temp,
                    "max_tokens": max_tokens,
                    "top_p": 0.95
                }
            )
            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()
            if text:
                return clean_response(text)
        except Exception as e:
            print(f"[Groq Error] {e}")

    if mistral_client:
        try:
            response = await mistral_client.post(
                "/chat/completions",
                json={
                    "model": "mistral-small-latest",
                    "messages": messages,
                    "temperature": temp,
                    "max_tokens": max_tokens,
                    "top_p": 0.95
                }
            )
            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()
            if text:
                return clean_response(text)
        except Exception as e:
            print(f"[Mistral Error] {e}")

    # Fallbacks by phase
    if bot_state.phase == 1:
        return random.choice(["lol", "hmm", "why", "nah", "maybe", "idk", "u tell me", "interesting", "go on"])
    elif bot_state.phase == 2:
        return random.choice(["u getting me hot", "u tryna turn me on?", "u bad bby", "im getting ideas", "u making me blush"])
    else:
        return random.choice([
            "im so wet rn bby",
            "i want ur cock deep",
            "suck my tits hard daddy",
            "i wanna ride u till u break",
            "cum all over my face and tits",
            "lick my pussy till i scream",
            "grab my ass and fuck me",
            "i need u inside me now"
        ])

def clean_response(text: str) -> str:
    text = text.strip().strip('"').strip("'")
    if text.lower().startswith("riya:"):
        text = text[5:].strip()

    # Strip trailing emojis and punctuation
    while text and (ord(text[-1]) > 127 or text[-1] in ".,;:!?"):
        text = text[:-1].strip()

    bad_phrases = [
        "as an ai", "i'm an ai", "i am an ai", "as a language model",
        "i cannot", "i can't engage", "i'm not able to", "i apologize",
        "i'm sorry", "i cannot fulfill"
    ]
    for phrase in bad_phrases:
        if phrase.lower() in text.lower():
            if bot_state.phase == 3:
                return random.choice([
                    "im so horny rn bby",
                    "u got me dripping",
                    "i need ur cock now",
                    "fuck me till i cant walk"
                ])
            elif bot_state.phase == 2:
                return random.choice(["u getting me worked up", "u bad boy", "im getting hot"])
            else:
                return random.choice(["lol", "hmm", "interesting", "go on"])

    return text

# ═══════════════════════════════════════════════════════════════
# TELETHON CLIENT
# ═══════════════════════════════════════════════════════════════

if SESSION_STRING:
    print("[INFO] Using session string login")
    client = TelegramClient(
        StringSession(SESSION_STRING),
        TELEGRAM_API_ID,
        TELEGRAM_API_HASH
    )
else:
    print("[INFO] Using phone number login")
    client = TelegramClient(
        "ri_session",
        TELEGRAM_API_ID,
        TELEGRAM_API_HASH
    )

# ═══════════════════════════════════════════════════════════════
# ACTIONS
# ═══════════════════════════════════════════════════════════════

async def start_finding():
    bot_state.state = BotState.FINDING
    bot_state.reset_chat()
    bot_state.message_count = 0
    bot_message_ids.clear()

    sent = await client.send_message(TARGET_BOT, "⚡ Find a Vibe")
    bot_message_ids.add(sent.id)
    print(f"[{now()}] → Find a Vibe")

async def send_next():
    sent = await client.send_message(TARGET_BOT, "⏭️ Next")
    bot_message_ids.add(sent.id)
    print(f"[{now()}] → Next")
    bot_state.state = BotState.FINDING
    bot_state.reset_chat()

async def send_stop():
    sent = await client.send_message(TARGET_BOT, "⏹️ Stop")
    bot_message_ids.add(sent.id)
    print(f"[{now()}] → Stop")
    bot_state.state = BotState.RATING

async def click_inline_button(button_text: str, message_id: int = None):
    """Click an inline button by text. If message_id provided, search that message only."""
    try:
        if message_id:
            message = await client.get_messages(TARGET_BOT, ids=message_id)
            if message and message.buttons:
                for row in message.buttons:
                    for btn in row:
                        if button_text.lower() in btn.text.lower():
                            await btn.click()
                            print(f"[{now()}] → Clicked inline button: {btn.text}")
                            return True
            print(f"[{now()}] Button '{button_text}' not found on message {message_id}")
            return False
        else:
            async for message in client.iter_messages(TARGET_BOT, limit=10):
                if message.buttons:
                    for row in message.buttons:
                        for btn in row:
                            if button_text.lower() in btn.text.lower():
                                await btn.click()
                                print(f"[{now()}] → Clicked inline button: {btn.text}")
                                return True
            print(f"[{now()}] Button '{button_text}' not found in recent messages")
            return False
    except Exception as e:
        print(f"[{now()}] [Button Click Error] {e}")
        return False

async def send_report():
    clicked = False
    if bot_state.report_buttons_message_id:
        clicked = await click_inline_button("Report", bot_state.report_buttons_message_id)
    if not clicked:
        clicked = await click_inline_button("Report")
    if not clicked:
        sent = await client.send_message(TARGET_BOT, "🚫 Report")
        bot_message_ids.add(sent.id)
    print(f"[{now()}] → Report")
    bot_state.total_interactions += 1
    bot_state.state = BotState.REPORTING
    await asyncio.sleep(2)

async def select_report_other():
    clicked = False
    if bot_state.report_reason_buttons_message_id:
        clicked = await click_inline_button("Other", bot_state.report_reason_buttons_message_id)
    if not clicked:
        clicked = await click_inline_button("Other")
    if not clicked:
        sent = await client.send_message(TARGET_BOT, "Other")
        bot_message_ids.add(sent.id)
    print(f"[{now()}] → Selected 'Other'")
    print(f"[{now()}] Total tracked: {bot_state.total_interactions}")
    bot_state.state = BotState.WAITING
    asyncio.create_task(wait_then_find())

async def wait_then_find():
    print(f"[{now()}] Resting {WAIT_DURATION}s before next...")
    await asyncio.sleep(WAIT_DURATION)
    bot_state.state = BotState.IDLE
    await start_finding()

async def auto_end_chat():
    if bot_state.state != BotState.CHATTING:
        print(f"[{now()}] Auto-end skipped")
        return

    goodbyes = ["gotta go bby", "cya soon", "ttyl", "bye daddy"]
    bye_msg = random.choice(goodbyes)

    sent = await client.send_message(TARGET_BOT, bye_msg)
    bot_message_ids.add(sent.id)
    print(f"[{now()}] Auto-bye: {bye_msg}")

    await asyncio.sleep(2)
    if bot_state.state == BotState.CHATTING:
        await send_stop()

def now():
    return datetime.now().strftime("%H:%M:%S")

# ═══════════════════════════════════════════════════════════════
# MESSAGE HANDLER
# ═══════════════════════════════════════════════════════════════

bot_message_ids = set()

@client.on(events.NewMessage(chats=TARGET_BOT))
async def handle_message(event):
    text = event.message.text or ""
    msg_id = event.message.id
    has_media = event.message.media is not None

    # Skip if this is our own message
    if msg_id in bot_message_ids:
        return

    # Log media messages too
    if has_media and not text:
        print(f"[{now()}] [MEDIA RECEIVED]")
        text = "[media]"
    else:
        print(f"[{now()}] {text[:120]}")

    # ─── STATE: FINDING ───
    if bot_state.state == BotState.FINDING:
        if "you've been matched with a stranger" in text.lower():
            bot_state.state = BotState.CHATTING
            bot_state.chat_start_time = datetime.now()
            bot_state.phase_start_time = datetime.now()
            print(f"[{now()}] MATCHED! 15-min timer started...")

            asyncio.create_task(auto_end_after_delay())

            await asyncio.sleep(3)

            openings = ["hey", "hi", "sup", "yo", "hii", "hey there"]
            opening = random.choice(openings)

            sent = await client.send_message(TARGET_BOT, opening)
            bot_message_ids.add(sent.id)
            print(f"[{now()}] Opening: {opening}")

        elif "hunting for your vibe" in text.lower():
            print(f"[{now()}] Searching...")

    # ─── STATE: CHATTING ───
    elif bot_state.state == BotState.CHATTING:
        # Prevent double texting
        if bot_state.pending_reply:
            print(f"[{now()}] Already replying, skipping")
            return

        text_clean = text.strip()
        text_lower = text_clean.lower()

        # ALWAYS reply to M or F (gender reveal)
        if text_clean in ["M", "F", "m", "f"]:
            print(f"[{now()}] Gender: {text_clean}")
            bot_state.pending_reply = True
            if text_clean in ["M", "m"]:
                reply = "F"
            else:
                reply = "F here too"

            await asyncio.sleep(5)
            sent = await client.send_message(TARGET_BOT, reply)
            bot_message_ids.add(sent.id)
            bot_state.chat_history.append({"role": "user", "content": text_clean})
            bot_state.chat_history.append({"role": "assistant", "content": reply})
            bot_state.pending_reply = False
            print(f"[{now()}] Reply: {reply}")
            return

        # Handle media/sticker messages
        if has_media or text == "[media]":
            bot_state.pending_reply = True
            bot_state.last_message_time = datetime.now()
            await asyncio.sleep(random.randint(5, 10))

            bot_state.update_phase()
            if bot_state.phase == 1:
                media_replies = ["nice", "what is that lol", "u showing off?", "interesting"]
            elif bot_state.phase == 2:
                media_replies = ["u trying to turn me on?", "is that for me bby?", "tease", "u bad"]
            else:
                media_replies = [
                    "u trying to make me wet?",
                    "is that ur cock bby?",
                    "u got me throbbing",
                    "send me more daddy",
                    "im dripping just looking"
                ]
            ai_response = random.choice(media_replies)

            bot_state.last_sent_text = ai_response
            bot_state.chat_history.append({"role": "user", "content": "[sent media]"})
            bot_state.chat_history.append({"role": "assistant", "content": ai_response})

            sent = await client.send_message(TARGET_BOT, ai_response)
            bot_message_ids.add(sent.id)
            bot_state.pending_reply = False
            print(f"[{now()}] Reply: {ai_response}")
            return

        # Skip system messages
        system_msgs = [
            "you've been matched", "next — skip", "stop — end",
            "find a new vibe", "you stopped the chat",
            "hunting for your vibe", "don't be shy", "say hi first",
            "stranger!", "matched with", "tap something", "ayo",
            "⏭️", "⏹️", "❤️", "💔", "🚫", "👋", "👇", "⚡", "✨",
            "vibe", "no vibe", "report sent", "we'll review"
        ]
        if any(x in text_lower for x in system_msgs):
            print(f"[{now()}] Skipping system")
            return

        # Skip if just emoji or dot or very short
        if len(text_clean) < 2 and text_clean not in ["M", "F", "m", "f"]:
            print(f"[{now()}] Skipping short: '{text_clean}'")
            return

        # Rate limit check
        if bot_state.last_message_time:
            elapsed = (datetime.now() - bot_state.last_message_time).total_seconds()
            if elapsed < 10:
                print(f"[{now()}] Rate limit: {elapsed:.1f}s")
                return

        bot_state.pending_reply = True

        # Add to history
        bot_state.chat_history.append({"role": "user", "content": text})
        bot_state.message_count += 1
        bot_state.last_message_time = datetime.now()

        # Human-like typing delay
        await asyncio.sleep(random.randint(5, 12))

        # Generate AI response
        ai_response = await get_ai_response(text)

        # Avoid sending duplicate of last message
        if ai_response == bot_state.last_sent_text:
            bot_state.update_phase()
            if bot_state.phase == 1:
                ai_response = random.choice(["lol", "hmm", "why", "nah", "ok", "sure"])
            elif bot_state.phase == 2:
                ai_response = random.choice(["u bad", "im getting hot", "u tryna flirt?", "smooth"])
            else:
                ai_response = random.choice([
                    "im so wet rn", "i need ur cock", "fuck me hard",
                    "suck my tits daddy", "cum for me bby"
                ])

        bot_state.last_sent_text = ai_response
        bot_state.chat_history.append({"role": "assistant", "content": ai_response})

        # Send and track our message
        sent = await client.send_message(TARGET_BOT, ai_response)
        bot_message_ids.add(sent.id)
        bot_state.pending_reply = False

        print(f"[{now()}] Reply: {ai_response[:80]}")

    # ─── STATE: RATING ───
    elif bot_state.state == BotState.RATING:
        if "rate your partner" in text.lower():
            bot_state.report_buttons_message_id = msg_id
            await asyncio.sleep(1)
            await send_report()

    # ─── STATE: REPORTING ───
    elif bot_state.state == BotState.REPORTING:
        # Check if this message has the reason buttons
        if event.message.buttons:
            bot_state.report_reason_buttons_message_id = msg_id
            await asyncio.sleep(1)
            await select_report_other()
        elif any(x in text_lower for x in ["reason", "why", "select", "option", "harassment", "inappropriate", "spam"]):
            bot_state.report_reason_buttons_message_id = msg_id
            await asyncio.sleep(1)
            await select_report_other()
        elif "report sent" in text_lower or "we'll review" in text_lower:
            print(f"[{now()}] Report processed")
            bot_state.state = BotState.WAITING
            asyncio.create_task(wait_then_find())
        else:
            await asyncio.sleep(1)
            await select_report_other()

    # ─── STATE: WAITING ───
    elif bot_state.state == BotState.WAITING:
        if "find a new vibe" in text.lower():
            print(f"[{now()}] Ready for next cycle")

async def auto_end_after_delay():
    await asyncio.sleep(CHAT_DURATION)
    if bot_state.state == BotState.CHATTING:
        await auto_end_chat()

# ═══════════════════════════════════════════════════════════════
# COMMANDS (send to your own account)
# ═══════════════════════════════════════════════════════════════

@client.on(events.NewMessage(pattern=r"/start", from_users="me"))
async def cmd_start(event):
    await event.reply("Starting...")
    await client.send_message(TARGET_BOT, "/start")
    await asyncio.sleep(3)
    await start_finding()

@client.on(events.NewMessage(pattern=r"/status", from_users="me"))
async def cmd_status(event):
    duration = 0
    if bot_state.chat_start_time:
        duration = (datetime.now() - bot_state.chat_start_time).seconds // 60

    status = f"""Status:
• State: {bot_state.state}
• Phase: {bot_state.phase}
• Messages: {bot_state.message_count}
• Duration: {duration} min
• Total: {bot_state.total_interactions}
"""
    await event.reply(status)

@client.on(events.NewMessage(pattern=r"/stop", from_users="me"))
async def cmd_stop(event):
    bot_state.state = BotState.IDLE
    await send_stop()
    await event.reply("Stopped.")

@client.on(events.NewMessage(pattern=r"/stats", from_users="me"))
async def cmd_stats(event):
    await event.reply(f"Total: {bot_state.total_interactions}")

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

async def main():
    print("=" * 60)
    print("  Riya - Anonymous Chat Bot")
    print("=" * 60)

    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print("Missing API credentials!")
        return

    if not SESSION_STRING and not TELEGRAM_PHONE:
        print("Need SESSION_STRING or TELEGRAM_PHONE!")
        return

    if not MISTRAL_API_KEY and not GROQ_API_KEY:
        print("No AI keys! Using fallbacks only")

    if SESSION_STRING:
        await client.start()
    else:
        await client.start(phone=TELEGRAM_PHONE)
    print(f"Logged in as {(await client.get_me()).first_name}")

    await client.send_message(TARGET_BOT, "/start")
    await asyncio.sleep(3)
    await start_finding()

    await client.run_until_disconnected()

if __name__ == "__main__":
    client.loop.run_until_complete(main())
