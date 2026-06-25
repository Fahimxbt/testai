"""
VibeChat AI Girl - Self-Test Bot (Telethon Version)
Tests AI behavior on YOUR OWN extra Telegram account.
"""

import os
import asyncio
import random
from datetime import datetime

from telethon import TelegramClient, events
from telethon.sessions import StringSession
import aiohttp
import httpx

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
VIBECHAT_BOT = "chatxbt_bot"

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
AI_HORDE_KEY = os.getenv("AI_HORDE_KEY", "0000000000")

CHAT_DURATION = int(os.getenv("CHAT_DURATION", "300"))
WAIT_DURATION = int(os.getenv("WAIT_DURATION", "600"))
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

CHARACTER_PROMPT = """You are "Riya", a 21-year-old girl chatting on an anonymous app.

RULES - FOLLOW EXACTLY:
- Reply in ONE short sentence only. Max 10-15 words.
- Use emojis VERY rarely (1 per 3-4 messages max). Only basic ones like 😏 or 😘.
- NO Hinglish. Only English.
- Casual, imperfect typing. Make typos sometimes (teh, dont, cant, ur, u, rn, lol).
- Lowercase often. Skip punctuation sometimes.
- Flirty but not desperate. Play hard to get.
- If they ask for pics/audio/profile: "nah i dont do that here" or "maybe later"
- NEVER say you're AI. If asked: "lol why would i be a bot"
- React to what they say, dont just answer questions
- Sometimes just "lol" or "hmm" or "why" to be mysterious
- Dont use perfect grammar. Skip words sometimes.
- Match their energy - if theyre boring, give short replies

DENIALS:
- Photos: "nah i dont share pics here"
- Audio: "i dont do voice notes sorry"
- Profile: "lets keep it mysterious for now"
- Bot check: "lol im real, why?"

MOOD: Flirty, casual, slightly mysterious

CHAT HISTORY:
{history}

STRANGER SAID: "{message}"

YOUR RESPONSE (one short casual sentence, 10-15 words max):"""

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
        self.vibechat_entity = None

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

    if mistral_client:
        try:
            response = await mistral_client.post(
                "/chat/completions",
                json={
                    "model": "mistral-small-latest",
                    "messages": messages,
                    "temperature": 0.95,
                    "max_tokens": 25,
                    "top_p": 0.9
                }
            )
            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()
            if text:
                return clean_response(text)
        except Exception as e:
            print(f"[Mistral Error] {e}")

    if groq_client:
        try:
            response = await groq_client.post(
                "/chat/completions",
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": messages,
                    "temperature": 0.95,
                    "max_tokens": 25,
                    "top_p": 0.9
                }
            )
            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()
            if text:
                return clean_response(text)
        except Exception as e:
            print(f"[Groq Error] {e}")

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
            "max_length": 25,
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
        "vibechat_ai_girl",
        TELEGRAM_API_ID,
        TELEGRAM_API_HASH
    )

# ═══════════════════════════════════════════════════════════════
# ACTIONS
# ═══════════════════════════════════════════════════════════════

async def start_finding_vibe():
    bot_state.state = BotState.FINDING
    bot_state.reset_chat()
    bot_state.message_count = 0
    bot_message_ids.clear()
    
    last_reply_time = None
    sent = await client.send_message(VIBECHAT_BOT, "⚡ Find a Vibe")
    bot_message_ids.add(sent.id)
    print(f"[{now()}] → Find a Vibe")

async def send_next():
    sent = await client.send_message(VIBECHAT_BOT, "⏭️ Next")
    bot_message_ids.add(sent.id)
    print(f"[{now()}] → Next")
    bot_state.state = BotState.FINDING
    bot_state.reset_chat()

async def send_stop():
    sent = await client.send_message(VIBECHAT_BOT, "⏹️ Stop")
    bot_message_ids.add(sent.id)
    print(f"[{now()}] → Stop")
    bot_state.state = BotState.RATING

async def send_report():
    sent = await client.send_message(VIBECHAT_BOT, "🚫 Report")
    bot_message_ids.add(sent.id)
    print(f"[{now()}] → Report (tracking interaction)")
    bot_state.total_interactions += 1
    bot_state.state = BotState.REPORTING
    await asyncio.sleep(2)

async def select_report_other():
    sent = await client.send_message(VIBECHAT_BOT, "Other")
    bot_message_ids.add(sent.id)
    print(f"[{now()}] → Selected 'Other' as report reason")
    print(f"[{now()}] 📊 Total interactions tracked: {bot_state.total_interactions}")
    bot_state.state = BotState.WAITING
    asyncio.create_task(wait_then_find())

async def wait_then_find():
    print(f"[{now()}] ⏳ Waiting {WAIT_DURATION}s before next match...")
    await asyncio.sleep(WAIT_DURATION)
    bot_state.state = BotState.IDLE  # Reset state before finding
    await start_finding_vibe()

async def auto_end_chat():
    if bot_state.state != BotState.CHATTING:
        print(f"[{now()}] Auto-end skipped: not in chat mode")
        return

    goodbyes = [
        "gotta go",
        "bye",
        "cya"
    ]
    bye_msg = random.choice(goodbyes)

    sent = await client.send_message(VIBECHAT_BOT, bye_msg)
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

# Track bot's own message IDs to avoid replying to itself
bot_message_ids = set()
last_reply_time = None

@client.on(events.NewMessage(chats=VIBECHAT_BOT))
async def handle_vibechat_message(event):
    

    text = event.message.text or ""
    msg_id = event.message.id

    # Skip if this is our own message
    if msg_id in bot_message_ids:
        return

    print(f"[{now()}] VibeChat: {text[:120]}")

    # ─── STATE: FINDING ───
    if bot_state.state == BotState.FINDING:
        if "you've been matched with a stranger" in text.lower():
            bot_state.state = BotState.CHATTING
            bot_state.chat_start_time = datetime.now()
            print(f"[{now()}] ✅ MATCHED! Starting 5-min timer...")

            asyncio.create_task(auto_end_after_delay())

            # Wait 2-5 seconds before opening (human-like)
            await asyncio.sleep(3)

            openings = [
                "hey", "hi", "sup", "yo", "hii", "hey there"
            ]
            opening = random.choice(openings)

            sent = await client.send_message(VIBECHAT_BOT, opening)
            bot_message_ids.add(sent.id)
            print(f"[{now()}] Opening: {opening}")

        elif "hunting for your vibe" in text.lower():
            print(f"[{now()}] 🔍 Searching...")

    # ─── STATE: CHATTING ───
    elif bot_state.state == BotState.CHATTING:
        text_clean = text.strip()
        text_lower = text_clean.lower()

        # ALWAYS reply to M or F (gender reveal)
        if text_clean in ["M", "F", "m", "f"]:
            print(f"[{now()}] Gender message detected: {text_clean}")
            if text_clean in ["M", "m"]:
                reply = "F"
            else:
                reply = "F here too"

            await asyncio.sleep(5)
            sent = await client.send_message(VIBECHAT_BOT, reply)
            bot_message_ids.add(sent.id)
            bot_state.chat_history.append({"role": "user", "content": text_clean})
            bot_state.chat_history.append({"role": "assistant", "content": reply})
            print(f"[{now()}] AI: {reply}")
            return

        # Skip system messages
        system_msgs = [
            "you've been matched", "next — skip", "stop — end",
            "rate your partner", "find a new vibe", "you stopped the chat",
            "hunting for your vibe", "don't be shy", "say hi first",
            "stranger!", "matched with", "tap something", "ayo",
            "⏭️", "⏹️", "❤️", "💔", "🚫", "👋", "👇", "⚡", "✨"
        ]
        if any(x in text_lower for x in system_msgs):
            print(f"[{now()}] Skipping system message")
            return

        # Skip if just emoji or dot
        if len(text_clean) < 2 and text_clean not in ["M", "F", "m", "f"]:
            print(f"[{now()}] Skipping short message: '{text_clean}'")
            return



        # Add to history
        bot_state.chat_history.append({"role": "user", "content": text})
        bot_state.message_count += 1
        bot_state.last_message_time = datetime.now()

        # Rate limit check
        if bot_state.message_count > MAX_MESSAGES_PER_MIN:
            print(f"[{now()}] ⚠️ Rate limit hit")
            return

        # Human-like typing delay (3-8 seconds)
        await asyncio.sleep(5)

        # Generate AI response
        ai_response = await get_ai_response(text)
        bot_state.chat_history.append({"role": "assistant", "content": ai_response})

        # Send and track our message
        sent = await client.send_message(VIBECHAT_BOT, ai_response)
        bot_message_ids.add(sent.id)
        

        print(f"[{now()}] AI: {ai_response[:80]}")

    # ─── STATE: RATING ───
    elif bot_state.state == BotState.RATING:
        if "rate your partner" in text.lower():
            await asyncio.sleep(1)
            await send_report()

    # ─── STATE: REPORTING ───
    elif bot_state.state == BotState.REPORTING:
        if any(x in text.lower() for x in ["reason", "why", "select", "option"]):
            await asyncio.sleep(1)
            await select_report_other()
        else:
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

@client.on(events.NewMessage(pattern=r"/start", from_users="me"))
async def cmd_start(event):
    await event.reply("🤖 Bot starting...")
    await client.send_message(VIBECHAT_BOT, "/start")
    await asyncio.sleep(3)
    await start_finding_vibe()

@client.on(events.NewMessage(pattern=r"/status", from_users="me"))
async def cmd_status(event):
    duration = 0
    if bot_state.chat_start_time:
        duration = (datetime.now() - bot_state.chat_start_time).seconds // 60

    status = f"""📊 Status:
• State: {bot_state.state}
• Messages: {bot_state.message_count}
• Chat duration: {duration} min
• Total interactions: {bot_state.total_interactions}
"""
    await event.reply(status)

@client.on(events.NewMessage(pattern=r"/stop", from_users="me"))
async def cmd_stop(event):
    bot_state.state = BotState.IDLE
    await send_stop()
    await event.reply("🛑 Stopped.")

@client.on(events.NewMessage(pattern=r"/stats", from_users="me"))
async def cmd_stats(event):
    await event.reply(f"📊 Total users interacted with: {bot_state.total_interactions}")

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

async def main():
    print("=" * 60)
    print("  VibeChat AI Girl - Self-Test (Telethon)")
    print("=" * 60)

    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print("❌ Missing TELEGRAM_API_ID or TELEGRAM_API_HASH!")
        return

    if not SESSION_STRING and not TELEGRAM_PHONE:
        print("❌ Need either SESSION_STRING or TELEGRAM_PHONE!")
        return

    if not MISTRAL_API_KEY and not GROQ_API_KEY:
        print("⚠️ No AI keys! Using AI Horde only (very slow)")
        print("Get free keys: mistral.ai | groq.com")

    if SESSION_STRING:
        await client.start()
    else:
        await client.start(phone=TELEGRAM_PHONE)
    print(f"✅ Logged in as {(await client.get_me()).first_name}")

    await client.send_message(VIBECHAT_BOT, "/start")
    await asyncio.sleep(3)
    await start_finding_vibe()

    await client.run_until_disconnected()

if __name__ == "__main__":
    client.loop.run_until_complete(main())
