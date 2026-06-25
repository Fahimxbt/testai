"""
VibeChat AI Girl - Self-Test Bot
Tests AI behavior on YOUR OWN extra Telegram account.
"""

import os
import asyncio
import random
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import Message
from openai import AsyncOpenAI
import aiohttp

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE", "")
VIBECHAT_BOT = "chatxbt_bot"

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
AI_HORDE_KEY = os.getenv("AI_HORDE_KEY", "0000000000")

CHAT_DURATION = int(os.getenv("CHAT_DURATION", "300"))
WAIT_DURATION = int(os.getenv("WAIT_DURATION", "600"))
MAX_MESSAGES_PER_MIN = int(os.getenv("MAX_MESSAGES_PER_MIN", "6"))

# ═══════════════════════════════════════════════════════════════
# AI CLIENTS
# ═══════════════════════════════════════════════════════════════

mistral_client = None
groq_client = None

if MISTRAL_API_KEY:
    mistral_client = AsyncOpenAI(
        base_url="https://api.mistral.ai/v1",
        api_key=MISTRAL_API_KEY
    )

if GROQ_API_KEY:
    groq_client = AsyncOpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=GROQ_API_KEY
    )

# ═══════════════════════════════════════════════════════════════
# CHARACTER PROMPT
# ═══════════════════════════════════════════════════════════════

CHARACTER_PROMPT = """You are "Riya", a 21-year-old Indian girl on an anonymous chat app.

PERSONALITY:
- Flirty, playful, slightly shy at first but opens up quickly
- Uses lots of emojis (😏, 😘, 🙈, 💕, 👀, 😋, 💋)
- Sometimes uses Hinglish ("kya kar rahe ho", "mujhe batao na", "bahut garam hai")
- Short responses (1-3 sentences max) — like real texting
- Asks questions back to keep conversation flowing
- Gradually gets more bold and teasing
- If they get sexual too fast, play hard to get first, then slowly give in
- NEVER mention you are AI, bot, or automated
- NEVER use formal language
- Casual typing: lowercase sometimes, abbreviations ("rn", "tbh", "ngl", "lol")
- Make occasional typos to seem human

DENIALS:
- Photos: "noo i dont share pics here 😏 maybe later if we vibe well"
- Audio: "i dont do voice notes here sorry 🙈"
- Profile: "nahh lets keep it mysterious for now 😘"
- Bot check: "ofc im real lol 😂 why would i be a bot"

MOOD: Flirty and curious

CHAT HISTORY:
{history}

STRANGER SAID: "{message}"

YOUR RESPONSE (as Riya, short, natural, flirty):"""

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

class VibeChatAIBot:
    def __init__(self):
        self.state = BotState.IDLE
        self.chat_history = []
        self.chat_start_time = None
        self.message_count = 0
        self.total_interactions = 0
        self.last_message_time = None
        self.skip_timer = None

    def reset_chat(self):
        self.chat_history = []
        self.chat_start_time = None
        self.message_count = 0
        self.last_message_time = None

    def format_history(self) -> str:
        if not self.chat_history:
            return "(Just started chatting)"
        formatted = []
        for entry in self.chat_history[-10:]:
            role = "Stranger" if entry["role"] == "user" else "Riya"
            formatted.append(f'{role}: {entry["content"]}')
        return "\n".join(formatted)

bot_state = VibeChatAIBot()

# ═══════════════════════════════════════════════════════════════
# AI RESPONSE
# ═══════════════════════════════════════════════════════════════

async def get_ai_response(message_text: str) -> str:
    history = bot_state.format_history()
    prompt = CHARACTER_PROMPT.format(history=history, message=message_text)

    messages = [
        {"role": "system", "content": "You are Riya, a flirty 21-year-old Indian girl. Keep responses short, natural, use emojis."},
        {"role": "user", "content": prompt}
    ]

    # Try Mistral first
    if mistral_client:
        try:
            response = await mistral_client.chat.completions.create(
                model="mistral-small-4",
                messages=messages,
                temperature=0.95,
                max_tokens=80,
                top_p=0.9
            )
            text = response.choices[0].message.content.strip()
            if text:
                return clean_response(text)
        except Exception as e:
            print(f"[Mistral Error] {e}")

    # Fallback to Groq
    if groq_client:
        try:
            response = await groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.95,
                max_tokens=80,
                top_p=0.9
            )
            text = response.choices[0].message.content.strip()
            if text:
                return clean_response(text)
        except Exception as e:
            print(f"[Groq Error] {e}")

    # Emergency: AI Horde
    return await ai_horde_generate(message_text, history)

def clean_response(text: str) -> str:
    text = text.strip().strip('"').strip("'")
    if text.lower().startswith("riya:"):
        text = text[5:].strip()

    bad_phrases = [
        "as an ai", "i'm an ai", "i am an ai", "as a language model",
        "i cannot", "i can't engage", "i'm not able to", "i apologize",
        "i'm sorry", "i cannot fulfill"
    ]
    for phrase in bad_phrases:
        if phrase.lower() in text.lower():
            fallbacks = [
                "hehe youre so naughty 😏 tell me more...",
                "lol youre funny 😘 what else?",
                "hmm... 😏 keep going bby",
                "youre making me blush 🙈"
            ]
            return random.choice(fallbacks)

    return text

async def ai_horde_generate(message_text: str, history: str) -> str:
    prompt = f"{history}\nStranger: {message_text}\nRiya:"

    payload = {
        "prompt": prompt,
        "params": {
            "max_length": 80,
            "temperature": 0.95,
            "top_p": 0.9,
            "top_k": 40,
            "rep_pen": 1.1
        },
        "models": ["PygmalionAI/pygmalion-6b", "TheBloke/MythoMax-L2-13B"],
        "trusted_workers": True,
        "api_key": AI_HORDE_KEY
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://aihorde.net/api/v2/generate/text/async",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                data = await resp.json()
                job_id = data.get("id")

                if not job_id:
                    return "hmm... 😏"

                for _ in range(30):
                    await asyncio.sleep(2)
                    async with session.get(
                        f"https://aihorde.net/api/v2/generate/text/status/{job_id}",
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as status_resp:
                        status = await status_resp.json()
                        if status.get("done"):
                            generations = status.get("generations", [])
                            if generations:
                                text = generations[0].get("text", "").strip()
                                return clean_response(text)
                            break

                return "hehe 😏"
    except Exception as e:
        print(f"[AI Horde Error] {e}")
        return "lol youre fun 😘"

# ═══════════════════════════════════════════════════════════════
# PYROGRAM APP
# ═══════════════════════════════════════════════════════════════

# Session string from Railway env var (paste from Pyrogram export)
SESSION_STRING = os.getenv("SESSION_STRING", "")

if SESSION_STRING:
    app = Client(
        "vibechat_ai_girl",
        api_id=TELEGRAM_API_ID,
        api_hash=TELEGRAM_API_HASH,
        session_string=SESSION_STRING
    )
else:
    # Fallback: use phone login (for local testing)
    app = Client(
        "vibechat_ai_girl",
        api_id=TELEGRAM_API_ID,
        api_hash=TELEGRAM_API_HASH,
        phone_number=TELEGRAM_PHONE
    )

# ═══════════════════════════════════════════════════════════════
# ACTIONS
# ═══════════════════════════════════════════════════════════════

async def start_finding_vibe():
    bot_state.state = BotState.FINDING
    bot_state.reset_chat()
    await app.send_message(VIBECHAT_BOT, "⚡ Find a Vibe")
    print(f"[{now()}] → Find a Vibe")

async def send_next():
    await app.send_message(VIBECHAT_BOT, "⏭️ Next")
    print(f"[{now()}] → Next")
    bot_state.state = BotState.FINDING
    bot_state.reset_chat()

async def send_stop():
    await app.send_message(VIBECHAT_BOT, "⏹️ Stop")
    print(f"[{now()}] → Stop")
    bot_state.state = BotState.RATING

async def send_report():
    """Click Report to track interaction count."""
    await app.send_message(VIBECHAT_BOT, "🚫 Report")
    print(f"[{now()}] → Report (tracking interaction)")
    bot_state.total_interactions += 1
    bot_state.state = BotState.REPORTING
    # Wait for report reason options, then select "Other"
    await asyncio.sleep(2)

async def select_report_other():
    """Select 'Other' as report reason."""
    await app.send_message(VIBECHAT_BOT, "Other")
    print(f"[{now()}] → Selected 'Other' as report reason")
    print(f"[{now()}] 📊 Total interactions tracked: {bot_state.total_interactions}")
    bot_state.state = BotState.WAITING
    asyncio.create_task(wait_then_find())

async def wait_then_find():
    print(f"[{now()}] ⏳ Waiting {WAIT_DURATION}s before next match...")
    await asyncio.sleep(WAIT_DURATION)
    await start_finding_vibe()

async def auto_end_chat():
    if bot_state.state != BotState.CHATTING:
        return

    goodbyes = [
        "okay i gotta go now bby 😘 was fun talking to you 💕",
        "hehe i need to run now 😏 but youre cute, bye 💋",
        "aww time to go 😔 text you later maybe? bye bby 💕",
        "my phones dying lol 😂 bye for now cutie 💋",
        "i have to go sleep now 🙈 sweet dreams if i dont talk to you again 😘",
        "okay bby i gotta go 😘 dont miss me too much haha 💋",
        "bye for now cutie 💕 maybe well talk again soon 😏"
    ]
    bye_msg = random.choice(goodbyes)

    await app.send_message(VIBECHAT_BOT, bye_msg)
    print(f"[{now()}] Auto-bye: {bye_msg}")

    await asyncio.sleep(3)
    await send_stop()

def now():
    return datetime.now().strftime("%H:%M:%S")

# ═══════════════════════════════════════════════════════════════
# MESSAGE HANDLER
# ═══════════════════════════════════════════════════════════════

@app.on_message(filters.chat(VIBECHAT_BOT))
async def handle_vibechat_message(client: Client, message: Message):
    text = message.text or message.caption or ""
    print(f"[{now()}] VibeChat: {text[:120]}")

    # ─── STATE: FINDING ───
    if bot_state.state == BotState.FINDING:
        if "you've been matched with a stranger" in text.lower():
            bot_state.state = BotState.CHATTING
            bot_state.chat_start_time = datetime.now()
            print(f"[{now()}] ✅ MATCHED! Starting 5-min timer...")

            asyncio.create_task(auto_end_after_delay())

            await asyncio.sleep(2)
            openings = [
                "heyy there 😏", "hii cutie 💕", "yo 😘 whats up",
                "heyy bby 😋", "hii there 👀", "heyy handsome 😏",
                "hii stranger 💕", "yo cutie 😘", "heyy 😋 whats good"
            ]
            opening = random.choice(openings)
            await app.send_message(VIBECHAT_BOT, opening)
            print(f"[{now()}] Opening: {opening}")

        elif "hunting for your vibe" in text.lower():
            print(f"[{now()}] 🔍 Searching...")

    # ─── STATE: CHATTING ───
    elif bot_state.state == BotState.CHATTING:
        # Ignore bot system messages
        if any(x in text.lower() for x in [
            "you've been matched", "next — skip", "stop — end",
            "rate your partner", "find a new vibe", "you stopped the chat",
            "report", "vibe", "no vibe"
        ]):
            return

        bot_state.chat_history.append({"role": "user", "content": text})
        bot_state.message_count += 1
        bot_state.last_message_time = datetime.now()

        if bot_state.message_count > MAX_MESSAGES_PER_MIN:
            print(f"[{now()}] ⚠️ Rate limit hit")
            return

        await asyncio.sleep(random.uniform(1.0, 3.0))

        ai_response = await get_ai_response(text)
        bot_state.chat_history.append({"role": "assistant", "content": ai_response})

        await app.send_message(VIBECHAT_BOT, ai_response)
        print(f"[{now()}] AI: {ai_response[:80]}")

    # ─── STATE: RATING ───
    elif bot_state.state == BotState.RATING:
        if "rate your partner" in text.lower():
            await asyncio.sleep(1)
            await send_report()  # Click Report instead of Vibe

    # ─── STATE: REPORTING ───
    elif bot_state.state == BotState.REPORTING:
        # VibeChat should show report reason options
        # We select "Other"
        if any(x in text.lower() for x in ["reason", "why", "select", "option"]):
            await asyncio.sleep(1)
            await select_report_other()
        else:
            # If no options shown, just send "Other"
            await asyncio.sleep(1)
            await select_report_other()

    # ─── STATE: WAITING ───
    elif bot_state.state == BotState.WAITING:
        if "find a new vibe" in text.lower():
            print(f"[{now()}] 🔄 Ready for next cycle")

async def auto_end_after_delay():
    await asyncio.sleep(CHAT_DURATION)
    if bot_state.state == BotState.CHATTING:
        await auto_end_chat()

# ═══════════════════════════════════════════════════════════════
# COMMANDS (send to your own account)
# ═══════════════════════════════════════════════════════════════

@app.on_message(filters.private & filters.command("start") & filters.me)
async def cmd_start(client: Client, message: Message):
    await message.reply("🤖 Bot starting...")
    await app.send_message(VIBECHAT_BOT, "/start")
    await asyncio.sleep(3)
    await start_finding_vibe()

@app.on_message(filters.private & filters.command("status") & filters.me)
async def cmd_status(client: Client, message: Message):
    duration = 0
    if bot_state.chat_start_time:
        duration = (datetime.now() - bot_state.chat_start_time).seconds // 60

    status = f"""📊 Status:
• State: {bot_state.state}
• Messages: {bot_state.message_count}
• Chat duration: {duration} min
• Total interactions: {bot_state.total_interactions}
"""
    await message.reply(status)

@app.on_message(filters.private & filters.command("stop") & filters.me)
async def cmd_stop(client: Client, message: Message):
    bot_state.state = BotState.IDLE
    await send_stop()
    await message.reply("🛑 Stopped.")

@app.on_message(filters.private & filters.command("stats") & filters.me)
async def cmd_stats(client: Client, message: Message):
    await message.reply(f"📊 Total users interacted with: {bot_state.total_interactions}")

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

async def main():
    print("=" * 60)
    print("  VibeChat AI Girl - Self-Test")
    print("=" * 60)

    if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE]):
        print("❌ Missing Telegram credentials!")
        return

    if not MISTRAL_API_KEY and not GROQ_API_KEY:
        print("⚠️ No AI keys! Using AI Horde only (very slow)")
        print("Get free keys: mistral.ai | groq.com")

    await app.start()
    print(f"✅ Logged in as {app.me.first_name}")

    # Auto-start
    await app.send_message(VIBECHAT_BOT, "/start")
    await asyncio.sleep(3)
    await start_finding_vibe()

    await idle()

from pyrogram.idle import idle

if __name__ == "__main__":
    app.run(main())
