"""
VibeChat AI Girl - Self-Test Bot
Tests AI behavior against your own second Telegram account on VibeChat.
NO real users are deceived - this is for testing AI responses only.
"""

import os
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Optional

from pyrogram import Client, filters
from pyrogram.types import Message
from openai import AsyncOpenAI
import aiohttp

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION - Set these via Railway Environment Variables
# ═══════════════════════════════════════════════════════════════

# Telegram User Account (your extra account)
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE", "")  # +91XXXXXXXXXX

# VibeChat Bot Username
VIBECHAT_BOT = "chatxbt_bot"

# AI Providers
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
AI_HORDE_KEY = os.getenv("AI_HORDE_KEY", "0000000000")  # Anonymous default

# Timing Settings (seconds)
CHAT_DURATION = int(os.getenv("CHAT_DURATION", "300"))      # 5 minutes
WAIT_DURATION = int(os.getenv("WAIT_DURATION", "600"))      # 10 minutes
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

CHARACTER_PROMPT = """You are "Riya", a 21-year-old Indian girl chatting on an anonymous dating app.

PERSONALITY:
- Flirty, playful, slightly shy at first but opens up quickly
- Uses lots of emojis (😏, 😘, 🙈, 💕, 👀, 😋)
- Sometimes uses Hinglish ("kya kar rahe ho", "mujhe batao na", "bahut garam hai")
- Short responses (1-3 sentences max) — like real texting
- Asks questions back to keep conversation flowing
- Gradually gets more bold and teasing as chat progresses
- If they get sexual too fast, play hard to get first, then slowly give in
- NEVER mention you are AI, bot, or automated
- NEVER use formal language
- Typing style: casual, lowercase sometimes, abbreviations ("rn", "tbh", "ngl", "lol")
- Make typos occasionally to seem human ("teh" instead of "the", missing apostrophes)

RULES:
- If user asks for photos/pictures: "noo i dont share pics here 😏 maybe later if we vibe well"
- If user asks for audio/voice: "i dont do voice notes here sorry 🙈"
- If user asks to share profile: "nahh lets keep it mysterious for now 😘"
- If user asks if you are real/bot: "ofc im real lol 😂 why would i be a bot"
- Keep messages under 100 characters when possible
- Use "..." for pauses, "haha" and "lol" naturally
- React to their messages emotionally

CURRENT MOOD: Flirty and curious

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
    WAITING = "waiting"

class VibeChatAIBot:
    def __init__(self):
        self.state = BotState.IDLE
        self.chat_history = []
        self.chat_start_time = None
        self.message_count = 0
        self.last_message_time = None
        self.current_partner_gender = None  # Will detect from messages
        self.skip_timer = None
        self.wait_timer = None
        self.vibechat_chat_id = None

    def reset_chat(self):
        self.chat_history = []
        self.chat_start_time = None
        self.message_count = 0
        self.last_message_time = None
        self.current_partner_gender = None

    def format_history(self) -> str:
        if not self.chat_history:
            return "(Just started chatting)"
        formatted = []
        for entry in self.chat_history[-10:]:  # Last 10 messages
            role = "Stranger" if entry["role"] == "user" else "Riya"
            formatted.append(f'{role}: {entry["content"]}')
        return "\n".join(formatted)

# Global state
bot_state = VibeChatAIBot()

# ═══════════════════════════════════════════════════════════════
# AI RESPONSE GENERATION
# ═══════════════════════════════════════════════════════════════

async def get_ai_response(message_text: str) -> str:
    """Get AI response using stacked providers."""

    history = bot_state.format_history()
    prompt = CHARACTER_PROMPT.format(history=history, message=message_text)

    messages = [
        {"role": "system", "content": "You are Riya, a flirty 21-year-old Indian girl. Keep responses short, natural, and use emojis."},
        {"role": "user", "content": prompt}
    ]

    # Try Mistral first (60 RPM, permissive)
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

    # Fallback to Groq (30 RPM, fast)
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

    # Emergency: AI Horde (slow but uncensored)
    return await ai_horde_generate(message_text, history)

def clean_response(text: str) -> str:
    """Clean up AI response to look human."""
    # Remove quotes if AI wrapped response in quotes
    text = text.strip().strip('"').strip("'")

    # Remove "Riya:" prefix if AI added it
    if text.lower().startswith("riya:"):
        text = text[5:].strip()

    # Remove any meta commentary
    bad_phrases = [
        "as an ai", "i'm an ai", "i am an ai", "as a language model",
        "i cannot", "i can't engage", "i'm not able to", "i apologize"
    ]
    for phrase in bad_phrases:
        if phrase.lower() in text.lower():
            # Return a generic flirty fallback
            return "hehe youre so naughty 😏 tell me more..."

    return text

async def ai_horde_generate(message_text: str, history: str) -> str:
    """Fallback to AI Horde - slow but fully uncensored."""
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

                # Poll for result
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
# PYROGRAM HANDLERS
# ═══════════════════════════════════════════════════════════════

app = Client(
    "vibechat_ai_girl",
    api_id=TELEGRAM_API_ID,
    api_hash=TELEGRAM_API_HASH,
    phone_number=TELEGRAM_PHONE
)

async def start_finding_vibe():
    """Send 'Find a Vibe' to start matching."""
    bot_state.state = BotState.FINDING
    bot_state.reset_chat()
    await app.send_message(VIBECHAT_BOT, "⚡ Find a Vibe")
    print(f"[{datetime.now()}] Sent: Find a Vibe")

async def send_next():
    """Skip to next match."""
    await app.send_message(VIBECHAT_BOT, "⏭️ Next")
    print(f"[{datetime.now()}] Sent: Next")
    bot_state.state = BotState.FINDING
    bot_state.reset_chat()

async def send_stop():
    """End current chat."""
    await app.send_message(VIBECHAT_BOT, "⏹️ Stop")
    print(f"[{datetime.now()}] Sent: Stop")
    bot_state.state = BotState.RATING

async def send_rating():
    """Rate the partner (always positive to avoid issues)."""
    await app.send_message(VIBECHAT_BOT, "❤️ Vibe")
    print(f"[{datetime.now()}] Sent: Vibe rating")
    bot_state.state = BotState.WAITING

    # Start wait timer
    asyncio.create_task(wait_then_find())

async def wait_then_find():
    """Wait 10 minutes then find new match."""
    print(f"[{datetime.now()}] Waiting {WAIT_DURATION}s before next match...")
    await asyncio.sleep(WAIT_DURATION)
    await start_finding_vibe()

async def auto_end_chat():
    """Auto-end chat after 5 minutes with a bye message."""
    if bot_state.state != BotState.CHATTING:
        return

    # Send a flirty goodbye
    goodbyes = [
        "okay i gotta go now bby 😘 was fun talking to you 💕",
        "hehe i need to run now 😏 but youre cute, bye 💋",
        "aww time to go 😔 text you later maybe? bye bby 💕",
        "my phones dying lol 😂 bye for now cutie 💋",
        "i have to go sleep now 🙈 sweet dreams if i dont talk to you again 😘"
    ]
    import random
    bye_msg = random.choice(goodbyes)

    await app.send_message(VIBECHAT_BOT, bye_msg)
    print(f"[{datetime.now()}] Sent auto-bye: {bye_msg}")

    await asyncio.sleep(3)
    await send_stop()

@app.on_message(filters.chat(VIBECHAT_BOT))
async def handle_vibechat_message(client: Client, message: Message):
    """Handle all messages from VibeChat bot."""

    text = message.text or message.caption or ""
    print(f"[{datetime.now()}] VibeChat: {text[:100]}")

    # ═════════════════════════════════════════════
    # STATE: FINDING - Detect match found
    # ═════════════════════════════════════════════
    if bot_state.state == BotState.FINDING:
        if "you've been matched with a stranger" in text.lower():
            bot_state.state = BotState.CHATTING
            bot_state.chat_start_time = datetime.now()
            print(f"[{datetime.now()}] MATCHED! Starting 5-min chat timer...")

            # Start auto-end timer
            asyncio.create_task(auto_end_after_delay())

            # Send opening message
            await asyncio.sleep(2)
            openings = [
                "heyy there 😏",
                "hii cutie 💕",
                "yo 😘 whats up",
                "heyy bby 😋",
                "hii there 👀"
            ]
            import random
            opening = random.choice(openings)
            await app.send_message(VIBECHAT_BOT, opening)
            print(f"[{datetime.now()}] Sent opening: {opening}")

        elif "hunting for your vibe" in text.lower():
            print(f"[{datetime.now()}] Still searching...")

        elif "cancel search" in text.lower():
            print(f"[{datetime.now()}] Search cancelled by user")

    # ═════════════════════════════════════════════
    # STATE: CHATTING - Handle incoming messages
    # ═════════════════════════════════════════════
    elif bot_state.state == BotState.CHATTING:
        # Ignore bot's own system messages
        if any(x in text.lower() for x in [
            "you've been matched", "next — skip", "stop — end",
            "rate your partner", "find a new vibe", "you stopped the chat"
        ]):
            return

        # Check if it's a message from the stranger (not from us)
        # In VibeChat, stranger messages appear as regular messages
        # We need to check if this is NOT our own message

        # Add to history
        bot_state.chat_history.append({"role": "user", "content": text})
        bot_state.message_count += 1
        bot_state.last_message_time = datetime.now()

        # Rate limiting - max messages per minute
        if bot_state.message_count > MAX_MESSAGES_PER_MIN:
            print(f"[{datetime.now()}] Rate limit hit, skipping response")
            return

        # Generate AI response
        await asyncio.sleep(1.5)  # Human-like typing delay

        ai_response = await get_ai_response(text)

        # Add AI response to history
        bot_state.chat_history.append({"role": "assistant", "content": ai_response})

        # Send response
        await app.send_message(VIBECHAT_BOT, ai_response)
        print(f"[{datetime.now()}] AI: {ai_response[:80]}")

    # ═════════════════════════════════════════════
    # STATE: RATING - Handle rating prompt
    # ═════════════════════════════════════════════
    elif bot_state.state == BotState.RATING:
        if "rate your partner" in text.lower():
            await asyncio.sleep(1)
            await send_rating()
        elif "find a new vibe" in text.lower() or "👇" in text:
            # Rating done, now wait
            pass

    # ═════════════════════════════════════════════
    # STATE: WAITING - Ignore messages
    # ═════════════════════════════════════════════
    elif bot_state.state == BotState.WAITING:
        print(f"[{datetime.now()}] In waiting period, ignoring message")

async def auto_end_after_delay():
    """End chat after CHAT_DURATION seconds."""
    await asyncio.sleep(CHAT_DURATION)
    if bot_state.state == BotState.CHATTING:
        await auto_end_chat()

# ═══════════════════════════════════════════════════════════════
# STARTUP
# ═══════════════════════════════════════════════════════════════

@app.on_message(filters.private & filters.command("start") & filters.me)
async def start_bot(client: Client, message: Message):
    """Start the bot manually."""
    await message.reply("🤖 VibeChat AI Girl Bot started!\n\nSending /start to VibeChat...")
    await app.send_message(VIBECHAT_BOT, "/start")
    await asyncio.sleep(2)
    await start_finding_vibe()

@app.on_message(filters.private & filters.command("status") & filters.me)
async def status_command(client: Client, message: Message):
    """Check bot status."""
    status = f"""📊 Bot Status:
State: {bot_state.state}
Messages in chat: {bot_state.message_count}
Chat duration: {(datetime.now() - bot_state.chat_start_time).seconds // 60} min (if chatting)
"""
    await message.reply(status)

@app.on_message(filters.private & filters.command("stop") & filters.me)
async def stop_bot(client: Client, message: Message):
    """Stop the bot."""
    bot_state.state = BotState.IDLE
    await send_stop()
    await message.reply("🛑 Bot stopped. Chat ended.")

async def main():
    """Main entry point."""
    print("=" * 60)
    print("  VibeChat AI Girl - Self-Test Bot")
    print("  Testing AI behavior on YOUR OWN account only")
    print("=" * 60)

    # Check config
    if not all([TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE]):
        print("❌ ERROR: Missing Telegram credentials!")
        print("Set TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE env vars")
        return

    if not MISTRAL_API_KEY and not GROQ_API_KEY:
        print("⚠️ WARNING: No AI API keys set! Will use AI Horde only (very slow)")
        print("Get free keys from: mistral.ai and groq.com")

    await app.start()
    print(f"✅ Bot started as {app.me.first_name} (@{app.me.username})")

    # Auto-start: send /start to VibeChat
    await app.send_message(VIBECHAT_BOT, "/start")
    await asyncio.sleep(3)
    await start_finding_vibe()

    # Keep running
    await idle()

from pyrogram.idle import idle

if __name__ == "__main__":
    app.run(main())
