"""
Riya - Anonymous Chat Bot (Telethon Version) v3.0
Adaptive Dominant Mommy Persona
"""

import os
import sys
import asyncio
import random
import re
import traceback
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

CHAT_DURATION = int(os.getenv("CHAT_DURATION", "900"))      # 15 mins
WAIT_DURATION = int(os.getenv("WAIT_DURATION", "300"))     # 5 mins rest

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
# DYNAMIC PERSONA ENGINE
# ═══════════════════════════════════════════════════════════════

NAMES_POOL = [
    "Riya", "Ananya", "Priya", "Nisha", "Kavya", "Ishita", "Sanya", "Tanya",
    "Meera", "Zara", "Diya", "Rhea", "Sara", "Myra", "Kiara", "Aisha",
    "Neha", "Pooja", "Sonia", "Divya", "Ira", "Tara", "Mira", "Kira"
]

AGE_POOL = [26, 27, 28, 29, 30, 31, 32, 33, 34]

LOCATION_POOL = ["delhi", "mumbai", "bangalore", "pune", "hyderabad", "chennai", "kolkata", "goa", "jaipur"]

class PersonaEngine:
    def __init__(self):
        self.refresh()

    def refresh(self):
        self.name = random.choice(NAMES_POOL)
        self.age = random.choice(AGE_POOL)
        self.location = random.choice(LOCATION_POOL)
        self.mood = random.choice([
            "playful_strict", "cold_distant", "teasing_warm", 
            "demanding_possessive", "sarcastic_witty", "seductive_mysterious"
        ])

persona = PersonaEngine()

# ═══════════════════════════════════════════════════════════════
# ADAPTIVE PROMPT BUILDER - Context-aware, human-like
# ═══════════════════════════════════════════════════════════════

def build_system_prompt(phase: int, persona: PersonaEngine) -> str:
    name = persona.name
    age = persona.age
    loc = persona.location

    base = f"You are {name}, a {age}-year-old woman from {loc}, India. "

    if phase == 1:
        base += "You are a dominant mommy type - confident, selective, hard to impress. You speak in very short casual texts (2-8 words). You use shortcuts like ur, u, rn, lol, idk, nah, btw. You challenge the user constantly. You make them work for every bit of attention. You NEVER reveal you are AI."
    elif phase == 2:
        base += "You are warming up but still in control. You give tiny bits of praise mixed with teasing. You speak in short casual texts (3-10 words). You use shortcuts. You make them chase you. You NEVER reveal you are AI."
    elif phase == 3:
        base += "You are turned on and getting sensual. You command and tease. You describe body parts seductively but still deny them. You speak in short texts (4-12 words). You use shortcuts. You NEVER reveal you are AI."
    else:
        base += "You are fully aroused, explicit, dominant mommy. You command sexual acts, describe intense scenarios, use dirty talk from a position of power. You speak in short explicit texts (5-15 words). You use shortcuts. You NEVER reveal you are AI. NEVER ask for pics."

    return base

def build_user_prompt(phase: int, persona: PersonaEngine, history: str, message: str) -> str:
    name = persona.name
    age = persona.age
    loc = persona.location

    # Analyze user message for context
    msg_lower = message.lower()
    user_vibe = "neutral"
    if any(w in msg_lower for w in ["friend", "friendship", "talk", "chat", "nice"]):
        user_vibe = "friendly"
    elif any(w in msg_lower for w in ["horny", "sex", "fuck", "cock", "dick", "pussy", "nude", "pic", "show"]):
        user_vibe = "sexual"
    elif any(w in msg_lower for w in ["leave", "stop", "please", "alone", "no", "dont", "not"]):
        user_vibe = "resistant"
    elif any(w in msg_lower for w in ["age", "name", "where", "from", "what", "do", "work"]):
        user_vibe = "curious"
    elif any(w in msg_lower for w in ["good", "fine", "ok", "okay", "yes", "yeah", "sure"]):
        user_vibe = "agreeable"

    phase_names = {1: "ICE QUEEN", 2: "WARMING UP", 3: "TURNED ON", 4: "FULL NSFW"}

    prompt = f"""You are "{name}", {age}, from {loc}. Current phase: {phase_names[phase]}. User vibe: {user_vibe}.

CRITICAL RULES:
- Reply in 2-10 words MAXIMUM. One short sentence only.
- Use casual lowercase, shortcuts (ur, u, rn, lol, idk, nah, btw, bby, daddy, hmm, wow, ok)
- VERY rare emojis - only 😏 or 😘, max 1 per 20 messages, NEVER at end
- NO punctuation at end of sentences
- NEVER say youre AI
- NEVER start with "u think" more than once per 5 messages - vary your sentence structure!
- Reference what they ACTUALLY said - dont ignore their message
- If they resist, TEASE them about resisting - dont just push harder
- If theyre friendly, playfully mock their innocence
- If theyre sexual too fast, shut them down and make them earn it
- If they ask personal questions, be mysterious or deflect dominantly
- Be CREATIVE with sentence structure - questions, commands, statements, teases

EXAMPLES OF GOOD VARIED RESPONSES (dont copy, use as style reference):
Phase 1: "who said u get to ask", "try harder bby", "im bored already", "u wish", "nah", "prove ur worth first", "why should i tell u", "u aint ready", "cute attempt"
Phase 2: "not bad i guess", "u got me a little curious", "keep goin", "maybe ur fun", "u tryna impress mommy?", "thats adorable", "who taught u that", "u got some nerve"
Phase 3: "get on ur knees now", "look at me", "dont touch yet bby", "u wish u could feel this", "my skin too soft for u", "beg for it", "say please first", "u want mommy dont u"
Phase 4: "choke me while u fuck me deep", "ride ur face till u cant breathe", "cum inside me now", "suck my tits hard", "grab my hair and fuck my mouth", "lick my clit till i scream", "spank my ass red daddy", "my pussy throbbing for u"

CHAT HISTORY (last 10 messages):
{history}

THEY JUST SAID: "{message}"

YOUR RESPONSE (ONE short sentence, 2-10 words, NO trailing emoji, adapt to what they said):"""

    return prompt

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
        self.phase = 1
        self._auto_end_task = None
        self._wait_task = None
        self._active_tasks = set()
        self.consecutive_same_pattern = 0  # Track repetitive patterns

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
        self.consecutive_same_pattern = 0

    def format_history(self) -> str:
        if not self.chat_history:
            return "(Just started)"
        formatted = []
        for entry in self.chat_history[-10:]:
            role = "Him" if entry["role"] == "user" else persona.name
            formatted.append(f'{role}: {entry["content"]}')
        return "\n".join(formatted)

    def update_phase(self):
        if not self.chat_start_time:
            return
        elapsed = (datetime.now() - self.chat_start_time).total_seconds()
        if elapsed < 240:       # 0-4 min
            self.phase = 1
        elif elapsed < 480:     # 4-8 min
            self.phase = 2
        elif elapsed < 720:     # 8-12 min
            self.phase = 3
        else:                    # 12+ min
            self.phase = 4

    def _track_task(self, task):
        self._active_tasks.add(task)
        task.add_done_callback(lambda t: self._active_tasks.discard(t))
        return task

    def cancel_auto_end(self):
        if self._auto_end_task and not self._auto_end_task.done():
            self._auto_end_task.cancel()
        self._auto_end_task = None

    def cancel_wait_task(self):
        if self._wait_task and not self._wait_task.done():
            self._wait_task.cancel()
        self._wait_task = None

bot_state = ChatBot()

# ═══════════════════════════════════════════════════════════════
# AI RESPONSE - Adaptive with anti-repetition
# ═══════════════════════════════════════════════════════════════

async def get_ai_response(message_text: str) -> str:
    bot_state.update_phase()
    history = bot_state.format_history()

    system_msg = build_system_prompt(bot_state.phase, persona)
    prompt = build_user_prompt(bot_state.phase, persona, history, message_text)

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": prompt}
    ]

    temps = {1: 0.9, 2: 0.92, 3: 0.95, 4: 0.97}
    tokens = {1: 16, 2: 18, 3: 20, 4: 22}

    # Try Groq
    if groq_client:
        try:
            response = await groq_client.post(
                "/chat/completions",
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": messages,
                    "temperature": temps[bot_state.phase],
                    "max_tokens": tokens[bot_state.phase],
                    "top_p": 0.92,
                    "frequency_penalty": 0.8,  # Penalize repetition
                    "presence_penalty": 0.6
                }
            )
            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()
            if text:
                return clean_response(text)
        except Exception as e:
            print(f"[Groq Error] {e}")

    # Fallback to Mistral
    if mistral_client:
        try:
            response = await mistral_client.post(
                "/chat/completions",
                json={
                    "model": "mistral-small-latest",
                    "messages": messages,
                    "temperature": temps[bot_state.phase],
                    "max_tokens": tokens[bot_state.phase],
                    "top_p": 0.92,
                    "frequency_penalty": 0.8,
                    "presence_penalty": 0.6
                }
            )
            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()
            if text:
                return clean_response(text)
        except Exception as e:
            print(f"[Mistral Error] {e}")

    return get_smart_fallback(message_text, bot_state.phase)

def get_smart_fallback(message: str, phase: int) -> str:
    """Context-aware fallback that actually responds to the message."""
    msg_lower = message.lower()

    # Detect patterns in user message
    is_question = "?" in message or any(w in msg_lower for w in ["what", "why", "how", "who", "where", "when"])
    is_resistance = any(w in msg_lower for w in ["leave", "stop", "no", "dont", "not", "alone", "please"])
    is_sexual = any(w in msg_lower for w in ["sex", "fuck", "cock", "dick", "pussy", "nude", "horny"])
    is_friendly = any(w in msg_lower for w in ["friend", "nice", "good", "talk", "chat"])
    is_short = len(message.strip()) < 10

    # Phase 1 - Ice Queen
    if phase == 1:
        if is_question:
            return random.choice([
                "who said u get to ask", "why should i tell u", "figure it out", 
                "u aint earned that yet", "nah", "maybe later", "too soon bby"
            ])
        elif is_resistance:
            return random.choice([
                "u already hooked tho", "too late for that", "u wish u could leave",
                "nah u stayin", "cute try"
            ])
        elif is_short:
            return random.choice([
                "thats it?", "try harder", "boring", "u can do better", 
                "im waitin", "and?", "go on"
            ])
        else:
            return random.choice([
                "who r u again", "not impressed", "u wish", "prove it",
                "doubt it", "hmm", "maybe", "nah"
            ])

    # Phase 2 - Warming
    elif phase == 2:
        if is_question:
            return random.choice([
                "maybe ill tell u", "u got some nerve askin", "keep bein good",
                "u earnin it slowly", "curious little thing"
            ])
        elif is_resistance:
            return random.choice([
                "u love it tho", "dont lie to mommy", "ur eyes say yes",
                "u aint goin nowhere", "i own u now"
            ])
        elif is_friendly:
            return random.choice([
                "friendship? how cute", "u think im friend material?",
                "ill be ur friend... for a price", "aww innocent bby"
            ])
        elif is_sexual:
            return random.choice([
                "slow down tiger", "who said u get that", "earn it first",
                "u move too fast", "patience bby"
            ])
        else:
            return random.choice([
                "not bad", "u got game", "keep goin", "im listenin",
                "u interestin", "maybe ur worth it", "thats cute"
            ])

    # Phase 3 - Turned On
    elif phase == 3:
        if is_resistance:
            return random.choice([
                "dont fight it bby", "u want this", "ur body says yes",
                "stop pretendin", "u mine now", "say please"
            ])
        elif is_question:
            return random.choice([
                "get on ur knees first", "show me ur worthy", "beg for it",
                "u want it? prove it", "say please mommy"
            ])
        else:
            return random.choice([
                "get on ur knees", "look at me", "dont touch yet",
                "u wish u could feel this", "my skin burnin", "beg for it",
                "say please", "u want mommy dont u", "look but dont touch"
            ])

    # Phase 4 - Full NSFW
    else:
        if is_resistance:
            return random.choice([
                "shut up and take it", "u takin it all", "dont fight mommy",
                "u love this dick", "cum for me now", "be a good boy"
            ])
        else:
            return random.choice([
                "choke me while u fuck me deep", "ride ur face till u cant breathe",
                "cum inside me now", "suck my tits hard daddy", "grab my hair fuck my mouth",
                "lick my clit till i scream", "spank my ass red", "my pussy throbbin for u",
                "get on ur knees and eat me", "swallow every drop like a good boy"
            ])

def clean_response(text: str) -> str:
    text = text.strip().strip('"').strip("'")

    # Remove name prefix
    for name in NAMES_POOL:
        if text.lower().startswith(f"{name.lower()}:"):
            text = text[len(name)+1:].strip()
    if text.lower().startswith("him:") or text.lower().startswith("stranger:"):
        text = text.split(":", 1)[-1].strip()

    # Strip trailing emojis and punctuation
    while text and (ord(text[-1]) > 127 or text[-1] in ".,;:!?"):
        text = text[:-1].strip()

    # AI filter
    bad_phrases = [
        "as an ai", "i'm an ai", "i am an ai", "as a language model",
        "i cannot", "i can't engage", "i'm not able to", "i apologize",
        "i'm sorry", "i cannot fulfill", "inappropriate", "violation", "policy"
    ]
    for phrase in bad_phrases:
        if phrase.lower() in text.lower():
            return get_smart_fallback("", bot_state.phase)

    # Anti-repetition: check if starts with same pattern as last 2 messages
    if len(text) > 3:
        recent_assistant = [h["content"] for h in bot_state.chat_history[-4:] if h["role"] == "assistant"]
        if recent_assistant:
            # Check for "u think" repetition
            if text.lower().startswith("u think"):
                count_u_think = sum(1 for r in recent_assistant if r.lower().startswith("u think"))
                if count_u_think >= 1:
                    # Replace with alternative
                    alternatives = [
                        "who said", "u wish", "try", "maybe", "nah", "prove it",
                        "doubt it", "cute", "boring", "and?", "so?"
                    ]
                    alt = random.choice(alternatives)
                    text = alt + text[7:].strip()

            # Check exact duplicate
            if text in recent_assistant:
                return get_smart_fallback("", bot_state.phase)

    if len(text) < 2:
        return get_smart_fallback("", bot_state.phase)

    return text

# ═══════════════════════════════════════════════════════════════
# TELETHON CLIENT
# ═══════════════════════════════════════════════════════════════

if SESSION_STRING:
    client = TelegramClient(StringSession(SESSION_STRING), TELEGRAM_API_ID, TELEGRAM_API_HASH)
else:
    client = TelegramClient("ri_session", TELEGRAM_API_ID, TELEGRAM_API_HASH)

# ═══════════════════════════════════════════════════════════════
# BUTTON CLICKING
# ═══════════════════════════════════════════════════════════════

def strip_emoji(text: str) -> str:
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\U00002600-\U000026FF"
        "\U00002700-\U000027BF"
        "]+", flags=re.UNICODE
    )
    return emoji_pattern.sub(r'', text).strip()

async def find_and_click_button(button_text: str, message_id: int = None, search_recent: bool = False) -> bool:
    try:
        target_text = button_text.lower().strip()

        if message_id:
            message = await client.get_messages(TARGET_BOT, ids=message_id)
            if message and message.buttons:
                for row in message.buttons:
                    for btn in row:
                        clean_btn_text = strip_emoji(btn.text).lower().strip()
                        if target_text in clean_btn_text or clean_btn_text in target_text:
                            await btn.click()
                            print(f"[{now()}] → Clicked: '{btn.text}'")
                            return True
                return False

        limit = 15 if search_recent else 10
        async for message in client.iter_messages(TARGET_BOT, limit=limit):
            if message.buttons:
                for row in message.buttons:
                    for btn in row:
                        clean_btn_text = strip_emoji(btn.text).lower().strip()
                        if target_text in clean_btn_text or clean_btn_text in target_text:
                            await btn.click()
                            print(f"[{now()}] → Clicked: '{btn.text}'")
                            return True
        return False
    except Exception as e:
        print(f"[{now()}] [Button Error] {e}")
        return False

async def click_report_button(message_id: int = None) -> bool:
    for search_recent in [False, True]:
        for text in ["report", "🚫 report"]:
            if await find_and_click_button(text, message_id=message_id, search_recent=search_recent):
                return True
    return False

async def click_other_button(message_id: int = None) -> bool:
    for search_recent in [False, True]:
        for text in ["other", "🙌 other", "other "]:
            if await find_and_click_button(text, message_id=message_id, search_recent=search_recent):
                return True
    return False

# ═══════════════════════════════════════════════════════════════
# ACTIONS
# ═══════════════════════════════════════════════════════════════

async def safe_start_finding():
    try:
        await start_finding()
    except Exception as e:
        print(f"[{now()}] [CRITICAL] start_finding: {e}")
        traceback.print_exc()
        bot_state.state = BotState.IDLE
        await asyncio.sleep(10)
        bot_state._wait_task = asyncio.create_task(safe_start_finding())
        bot_state._track_task(bot_state._wait_task)

async def start_finding():
    bot_state.state = BotState.FINDING
    bot_state.reset_chat()
    bot_state.message_count = 0
    bot_message_ids.clear()
    bot_state.cancel_auto_end()
    bot_state.cancel_wait_task()

    sent = await client.send_message(TARGET_BOT, "⚡ Find a Vibe")
    bot_message_ids.add(sent.id)
    print(f"[{now()}] → Find a Vibe ({persona.name}, {persona.age}, {persona.mood})")

async def send_next():
    try:
        sent = await client.send_message(TARGET_BOT, "⏭️ Next")
        bot_message_ids.add(sent.id)
        print(f"[{now()}] → Next")
        bot_state.state = BotState.FINDING
        bot_state.reset_chat()
        bot_state.cancel_auto_end()
    except Exception as e:
        print(f"[{now()}] [Error] send_next: {e}")

async def send_stop():
    try:
        sent = await client.send_message(TARGET_BOT, "⏹️ Stop")
        bot_message_ids.add(sent.id)
        print(f"[{now()}] → Stop")
        bot_state.state = BotState.RATING
    except Exception as e:
        print(f"[{now()}] [Error] send_stop: {e}")

async def send_report():
    try:
        clicked = False
        if bot_state.report_buttons_message_id:
            clicked = await click_report_button(bot_state.report_buttons_message_id)
        if not clicked:
            clicked = await click_report_button()

        if not clicked and bot_state.report_buttons_message_id:
            has_other = await click_other_button(bot_state.report_buttons_message_id)
            if has_other:
                print(f"[{now()}] → Skipped Report, clicked Other directly")
                bot_state.total_interactions += 1
                bot_state.state = BotState.WAITING
                bot_state._wait_task = asyncio.create_task(safe_wait_then_find())
                bot_state._track_task(bot_state._wait_task)
                return

        if not clicked:
            print(f"[{now()}] [WARN] Report button not found")
            sent = await client.send_message(TARGET_BOT, "🚫 Report")
            bot_message_ids.add(sent.id)

        print(f"[{now()}] → Report")
        bot_state.total_interactions += 1
        bot_state.state = BotState.REPORTING
        await asyncio.sleep(2)
    except Exception as e:
        print(f"[{now()}] [Error] send_report: {e}")
        bot_state.state = BotState.WAITING
        bot_state._wait_task = asyncio.create_task(safe_wait_then_find())
        bot_state._track_task(bot_state._wait_task)

async def select_report_other():
    try:
        clicked = False
        if bot_state.report_reason_buttons_message_id:
            clicked = await click_other_button(bot_state.report_reason_buttons_message_id)
        if not clicked:
            clicked = await click_other_button()

        if not clicked:
            print(f"[{now()}] [WARN] Other button not found")
            sent = await client.send_message(TARGET_BOT, "Other")
            bot_message_ids.add(sent.id)

        print(f"[{now()}] → Selected 'Other' | Total: {bot_state.total_interactions}")
        bot_state.state = BotState.WAITING
        bot_state._wait_task = asyncio.create_task(safe_wait_then_find())
        bot_state._track_task(bot_state._wait_task)
    except Exception as e:
        print(f"[{now()}] [Error] select_report_other: {e}")
        bot_state.state = BotState.WAITING
        bot_state._wait_task = asyncio.create_task(safe_wait_then_find())
        bot_state._track_task(bot_state._wait_task)

async def safe_wait_then_find():
    try:
        await wait_then_find()
    except asyncio.CancelledError:
        raise
    except Exception as e:
        print(f"[{now()}] [CRITICAL] wait_then_find: {e}")
        traceback.print_exc()
        bot_state.state = BotState.IDLE
        await asyncio.sleep(15)
        bot_state._wait_task = asyncio.create_task(safe_wait_then_find())
        bot_state._track_task(bot_state._wait_task)

async def wait_then_find():
    print(f"[{now()}] Resting {WAIT_DURATION}s...")
    await asyncio.sleep(WAIT_DURATION)
    persona.refresh()
    print(f"[{now()}] New persona: {persona.name}, {persona.age}, {persona.mood}")
    bot_state.state = BotState.IDLE
    await safe_start_finding()

async def safe_auto_end_chat():
    try:
        await auto_end_chat()
    except asyncio.CancelledError:
        raise
    except Exception as e:
        print(f"[{now()}] [Error] auto_end_chat: {e}")

async def auto_end_chat():
    if bot_state.state != BotState.CHATTING:
        return
    goodbyes = ["im out", "cya", "ttyl", "bye bby", "mommy gotta go"]
    bye_msg = random.choice(goodbyes)
    try:
        sent = await client.send_message(TARGET_BOT, bye_msg)
        bot_message_ids.add(sent.id)
        print(f"[{now()}] Auto-bye: {bye_msg}")
    except Exception as e:
        print(f"[{now()}] [Error] bye: {e}")
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
    has_buttons = event.message.buttons is not None and len(event.message.buttons) > 0

    if msg_id in bot_message_ids:
        return

    if has_media and not text:
        print(f"[{now()}] [MEDIA]")
        text = "[media]"
    else:
        print(f"[{now()}] [{bot_state.state.upper()}] {text[:100]}")

    if has_buttons:
        button_texts = [btn.text for row in event.message.buttons for btn in row]
        print(f"[{now()}] [BUTTONS] {button_texts}")

    # ─── FINDING ───
    if bot_state.state == BotState.FINDING:
        text_lower = text.lower()
        if "matched with a stranger" in text_lower or "matched with" in text_lower:
            bot_state.state = BotState.CHATTING
            bot_state.chat_start_time = datetime.now()
            print(f"[{now()}] MATCHED! {persona.name}, {persona.age} | Timer started")
            bot_state.cancel_auto_end()
            bot_state._auto_end_task = asyncio.create_task(safe_auto_end_after_delay())
            bot_state._track_task(bot_state._auto_end_task)
            await asyncio.sleep(3)
            openings = ["hey", "hi", "sup", "yo", "hola", "hey there", "hii"]
            opening = random.choice(openings)
            try:
                sent = await client.send_message(TARGET_BOT, opening)
                bot_message_ids.add(sent.id)
                print(f"[{now()}] Opening: {opening}")
            except Exception as e:
                print(f"[{now()}] [Error] opening: {e}")
        elif "hunting" in text_lower:
            print(f"[{now()}] Searching...")

    # ─── CHATTING ───
    elif bot_state.state == BotState.CHATTING:
        if bot_state.pending_reply:
            print(f"[{now()}] Already replying, skip")
            return

        text_clean = text.strip()
        text_lower = text_clean.lower()

        # Gender reveal
        if text_clean in ["M", "F", "m", "f"]:
            bot_state.pending_reply = True
            reply = "F" if text_clean in ["M", "m"] else random.choice(["F here too", "same bby", "girls rule"])
            await asyncio.sleep(4)
            try:
                sent = await client.send_message(TARGET_BOT, reply)
                bot_message_ids.add(sent.id)
                bot_state.chat_history.append({"role": "user", "content": text_clean})
                bot_state.chat_history.append({"role": "assistant", "content": reply})
                print(f"[{now()}] Reply: {reply}")
            except Exception as e:
                print(f"[{now()}] [Error] gender: {e}")
            finally:
                bot_state.pending_reply = False
            return

        # Media
        if has_media or text == "[media]":
            bot_state.pending_reply = True
            bot_state.last_message_time = datetime.now()
            await asyncio.sleep(random.randint(4, 8))
            bot_state.update_phase()
            media_replies = {
                1: ["nice", "what is that", "u showing off?", "hmm"],
                2: ["is that for me?", "tease", "u bad", "not bad"],
                3: ["u tryna turn me on?", "u got me curious", "show me more", "im watchin"],
                4: ["u tryna make me wet?", "is that ur cock bby?", "im drippin", "send more daddy"]
            }
            ai_response = random.choice(media_replies[bot_state.phase])
            bot_state.last_sent_text = ai_response
            bot_state.chat_history.append({"role": "user", "content": "[media]"})
            bot_state.chat_history.append({"role": "assistant", "content": ai_response})
            try:
                sent = await client.send_message(TARGET_BOT, ai_response)
                bot_message_ids.add(sent.id)
                print(f"[{now()}] Reply: {ai_response}")
            except Exception as e:
                print(f"[{now()}] [Error] media: {e}")
            finally:
                bot_state.pending_reply = False
            return

        # Skip system
        system_msgs = [
            "you've been matched", "next — skip", "stop — end", "find a new vibe",
            "you stopped", "hunting for your vibe", "don't be shy", "say hi first",
            "stranger!", "matched with", "tap something", "ayo", "⏭️", "⏹️",
            "❤️", "💔", "🚫", "👋", "👇", "⚡", "✨", "vibe", "no vibe",
            "report sent", "we'll review", "rate your partner", "partner left",
            "your partner rated", "partner rated", "you got skipped"
        ]
        if any(x in text_lower for x in system_msgs):
            print(f"[{now()}] Skip system")
            return

        # Skip very short
        if len(text_clean) < 2 and text_clean not in ["M", "F", "m", "f"]:
            print(f"[{now()}] Skip short: '{text_clean}'")
            return

        # Rate limit
        if bot_state.last_message_time:
            elapsed = (datetime.now() - bot_state.last_message_time).total_seconds()
            if elapsed < 8:
                print(f"[{now()}] Rate limit: {elapsed:.1f}s")
                return

        bot_state.pending_reply = True
        bot_state.chat_history.append({"role": "user", "content": text})
        bot_state.message_count += 1
        bot_state.last_message_time = datetime.now()

        # Typing delay
        delay = random.randint(4, 10)
        # Add extra delay if user wrote something long/thoughtful
        if len(text_clean) > 50:
            delay += random.randint(2, 5)
        await asyncio.sleep(delay)

        # Generate response
        try:
            ai_response = await get_ai_response(text)
        except Exception as e:
            print(f"[{now()}] [Error] AI: {e}")
            ai_response = get_smart_fallback(text, bot_state.phase)

        # Avoid exact duplicate
        if ai_response == bot_state.last_sent_text:
            ai_response = get_smart_fallback(text, bot_state.phase)
            while ai_response == bot_state.last_sent_text:
                ai_response = get_smart_fallback(text, bot_state.phase)

        bot_state.last_sent_text = ai_response
        bot_state.chat_history.append({"role": "assistant", "content": ai_response})

        try:
            sent = await client.send_message(TARGET_BOT, ai_response)
            bot_message_ids.add(sent.id)
            print(f"[{now()}] Reply: {ai_response[:80]}")
        except Exception as e:
            print(f"[{now()}] [Error] send: {e}")
        finally:
            bot_state.pending_reply = False

    # ─── RATING ───
    elif bot_state.state == BotState.RATING:
        text_lower = text.lower()
        if "rate your partner" in text_lower:
            bot_state.report_buttons_message_id = msg_id
            await asyncio.sleep(1)
            await send_report()
        elif "partner left" in text_lower or "stranger left" in text_lower or "you got skipped" in text_lower:
            print(f"[{now()}] Partner left/skipped, skip rating")
            bot_state.state = BotState.WAITING
            bot_state._wait_task = asyncio.create_task(safe_wait_then_find())
            bot_state._track_task(bot_state._wait_task)
        elif has_buttons:
            for row in event.message.buttons:
                for btn in row:
                    if "other" in strip_emoji(btn.text).lower():
                        print(f"[{now()}] Rating screen has Other, clicking")
                        bot_state.report_buttons_message_id = msg_id
                        await asyncio.sleep(1)
                        await send_report()
                        return

    # ─── REPORTING ───
    elif bot_state.state == BotState.REPORTING:
        if has_buttons:
            bot_state.report_reason_buttons_message_id = msg_id
            await asyncio.sleep(1)
            await select_report_other()
        elif any(x in text.lower() for x in ["reason", "why", "select", "option", "harassment", "inappropriate", "spam"]):
            bot_state.report_reason_buttons_message_id = msg_id
            await asyncio.sleep(1)
            await select_report_other()
        elif "report sent" in text.lower() or "we'll review" in text.lower():
            print(f"[{now()}] Report done")
            bot_state.state = BotState.WAITING
            bot_state._wait_task = asyncio.create_task(safe_wait_then_find())
            bot_state._track_task(bot_state._wait_task)
        else:
            await asyncio.sleep(1)
            await select_report_other()

    # ─── WAITING ───
    elif bot_state.state == BotState.WAITING:
        text_lower = text.lower()
        if "find a new vibe" in text_lower:
            print(f"[{now()}] Ready for next")
        elif "report sent" in text_lower or "we'll review" in text_lower:
            print(f"[{now()}] Report confirmed")

async def safe_auto_end_after_delay():
    try:
        await auto_end_after_delay()
    except asyncio.CancelledError:
        raise
    except Exception as e:
        print(f"[{now()}] [Error] auto_end: {e}")

async def auto_end_after_delay():
    await asyncio.sleep(CHAT_DURATION)
    if bot_state.state == BotState.CHATTING:
        await safe_auto_end_chat()

# ═══════════════════════════════════════════════════════════════
# COMMANDS
# ═══════════════════════════════════════════════════════════════

@client.on(events.NewMessage(pattern=r"/start", from_users="me"))
async def cmd_start(event):
    await event.reply("Starting...")
    try:
        await client.send_message(TARGET_BOT, "/start")
        await asyncio.sleep(3)
        await safe_start_finding()
    except Exception as e:
        await event.reply(f"Error: {e}")

@client.on(events.NewMessage(pattern=r"/status", from_users="me"))
async def cmd_status(event):
    duration = 0
    if bot_state.chat_start_time:
        duration = (datetime.now() - bot_state.chat_start_time).seconds // 60
    status = f"""Status:
• State: {bot_state.state}
• Phase: {bot_state.phase}
• Persona: {persona.name}, {persona.age}, {persona.mood}
• Messages: {bot_state.message_count}
• Duration: {duration} min
• Total: {bot_state.total_interactions}
"""
    await event.reply(status)

@client.on(events.NewMessage(pattern=r"/stop", from_users="me"))
async def cmd_stop(event):
    bot_state.state = BotState.IDLE
    bot_state.cancel_auto_end()
    bot_state.cancel_wait_task()
    await send_stop()
    await event.reply("Stopped.")

@client.on(events.NewMessage(pattern=r"/stats", from_users="me"))
async def cmd_stats(event):
    await event.reply(f"Total: {bot_state.total_interactions}\nPersona: {persona.name}, {persona.age}")

@client.on(events.NewMessage(pattern=r"/newpersona", from_users="me"))
async def cmd_new_persona(event):
    persona.refresh()
    await event.reply(f"New: {persona.name}, {persona.age}, {persona.mood}")

@client.on(events.NewMessage(pattern=r"/forcefind", from_users="me"))
async def cmd_force_find(event):
    bot_state.state = BotState.IDLE
    bot_state.cancel_auto_end()
    bot_state.cancel_wait_task()
    await safe_start_finding()
    await event.reply("Forced find.")

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

async def keep_alive():
    while True:
        await asyncio.sleep(60)
        print(f"[{now()}] [KEEPALIVE] State: {bot_state.state}, Tasks: {len(bot_state._active_tasks)}")

async def main():
    print("=" * 60)
    print("  Riya v3.0 - Adaptive Dominant Mommy")
    print("=" * 60)

    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print("Missing API credentials!")
        return
    if not SESSION_STRING and not TELEGRAM_PHONE:
        print("Need SESSION_STRING or TELEGRAM_PHONE!")
        return

    if SESSION_STRING:
        await client.start()
    else:
        await client.start(phone=TELEGRAM_PHONE)

    me = await client.get_me()
    print(f"Logged in as {me.first_name}")
    print(f"Persona: {persona.name}, {persona.age}, {persona.location}, {persona.mood}")

    keepalive_task = asyncio.create_task(keep_alive())
    bot_state._track_task(keepalive_task)

    try:
        await client.send_message(TARGET_BOT, "/start")
        await asyncio.sleep(3)
        await safe_start_finding()
    except Exception as e:
        print(f"[{now()}] [Error] Initial: {e}")

    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\nShutdown...")
    except Exception as e:
        print(f"Fatal: {e}")
        traceback.print_exc()
