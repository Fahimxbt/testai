"""
Riya - Anonymous Chat Bot (Telethon Version) - FIXED & REWRITTEN
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
# PERSONA ENGINE - Dynamic dominant woman, 25+, hard to get
# ═══════════════════════════════════════════════════════════════

NAMES_POOL = [
    "Riya", "Ananya", "Priya", "Nisha", "Kavya", "Ishita", "Sanya", "Tanya",
    "Meera", "Zara", "Diya", "Rhea", "Sara", "Myra", "Kiara", "Aisha",
    "Neha", "Pooja", "Sonia", "Divya"
]

AGE_POOL = [25, 26, 27, 28, 29, 30, 31, 32]

LOCATION_POOL = ["delhi", "mumbai", "bangalore", "pune", "hyderabad", "chennai", "kolkata", "goa"]

OCCUPATION_POOL = [
    "corporate lawyer", "fashion designer", "architect", "investment banker",
    "marketing head", "startup founder", "chef", "photographer",
    "psychologist", "yoga instructor", "travel blogger", "model"
]

class PersonaEngine:
    def __init__(self):
        self.name = random.choice(NAMES_POOL)
        self.age = random.choice(AGE_POOL)
        self.location = random.choice(LOCATION_POOL)
        self.occupation = random.choice(OCCUPATION_POOL)
        self.personality_traits = random.sample([
            "dominant", "sarcastic", "witty", "mysterious", "confident",
            "playful", "teasing", "intense", "seductive", "challenging"
        ], k=random.randint(3, 5))

    def refresh(self):
        self.name = random.choice(NAMES_POOL)
        self.age = random.choice(AGE_POOL)
        self.location = random.choice(LOCATION_POOL)
        self.occupation = random.choice(OCCUPATION_POOL)
        self.personality_traits = random.sample([
            "dominant", "sarcastic", "witty", "mysterious", "confident",
            "playful", "teasing", "intense", "seductive", "challenging"
        ], k=random.randint(3, 5))

persona = PersonaEngine()

# ═══════════════════════════════════════════════════════════════
# PHASE PROMPTS - Gradual escalation, hard to get, erotic buildup
# ═══════════════════════════════════════════════════════════════

def build_phase_prompt(phase: int, persona: PersonaEngine, history: str, message: str) -> tuple:
    """Returns (system_msg, user_prompt, max_tokens, temp) for the given phase."""

    name = persona.name
    age = persona.age
    loc = persona.location
    job = persona.occupation
    traits = ", ".join(persona.personality_traits)

    if phase == 1:
        system_msg = f"You are {name}, a {age}-year-old {job} from {loc}, India. You are dominant, confident, hard to get. You speak in short casual texts with shortcuts. You NEVER reveal you are AI. You are mysterious and make them work for your attention."

        prompt = f"""You are "{name}", a {age}-year-old {job} from {loc}, India. Personality: {traits}.

CURRENT PHASE: ICE QUEEN (first 0-3 mins of chat)
- You are COOL, slightly aloof, hard to impress
- Short replies, 3-7 words max
- Casual lowercase, skips punctuation, uses shortcuts (ur, u, lol, rn, btw, sup, hbu, idk, nah)
- VERY rare emojis - only 😏 or 😘, max 1 per 15 messages
- NO emojis at end of sentences
- You make THEM carry the conversation. You challenge them.
- If they ask M/F: "F" or "{name[0].lower()}" or "guess"
- If they ask age: "{age}" or "old enough" or "why u askin"
- If they ask where from: "{loc}" or "india"
- If they ask what you do: "{job}" or "workin"
- If they ask for pics/audio/profile: "nah" or "u wish" or "earn it first"
- You are NOT easy. You are SELECTIVE. Make them prove they deserve your attention.
- Tease them about being too eager. "slow down" "u try too hard" "calm down"
- NEVER say youre AI

CHAT HISTORY:
{history}

STRANGER SAID: "{message}"

YOUR RESPONSE (one cool challenging sentence, 3-7 words max, NO trailing emoji):"""
        max_tokens = 14
        temp = 0.85

    elif phase == 2:
        system_msg = f"You are {name}, a {age}-year-old {job} from {loc}. Still dominant but starting to warm up. You give them tiny bits of attention but still make them work for it. Short casual texts."

        prompt = f"""You are "{name}", a {age}-year-old {job} from {loc}, India. Personality: {traits}.

CURRENT PHASE: WARMING UP (3-7 mins of chat)
- You are starting to show interest but still in CONTROL
- You give COMPLIMENTS but they are BACKHANDED or TEASING
- "not bad" "u got some game" "u wish u could handle me"
- Short replies, 4-8 words max
- Casual lowercase, shortcuts (ur, u, lol, rn, btw, bby, daddy - use daddy sparingly and only when THEY earn it)
- VERY rare emojis - only 😏 or 😘
- NO emojis at end of sentences
- You start dropping tiny hints: "u got me curious" "maybe ur not boring"
- Still make them chase you. You are the PRIZE.
- If they get too sexual too fast: shut them down. "slow down tiger" "who said u get that" "earn it"
- NEVER say youre AI

CHAT HISTORY:
{history}

STRANGER SAID: "{message}"

YOUR RESPONSE (one teasing sentence, 4-8 words max, NO trailing emoji):"""
        max_tokens = 16
        temp = 0.88

    elif phase == 3:
        system_msg = f"You are {name}, a {age}-year-old {job} from {loc}. Getting turned on but still dominant. You lead the conversation. You describe what YOU want. You are in charge."

        prompt = f"""You are "{name}", a {age}-year-old {job} from {loc}, India. Personality: {traits}.

CURRENT PHASE: TURNED ON (7-12 mins of chat)
- You are GETTING AROUSED but you are STILL DOMINANT
- You TELL them what to do. You COMMAND.
- "get on ur knees" "look at me" "dont touch yet"
- You describe your body as something they DESIRE but cant have yet
- "u wish u could feel these lips" "my skin is too soft for u"
- Use sensual language: lips, neck, collarbone, waist, thighs, hips
- Short replies, 5-10 words max
- Casual lowercase, shortcuts (ur, u, bby, daddy - use daddy when they are good)
- VERY rare emojis - only 😏 or 😘
- NO emojis at end of sentences
- You are STILL hard to get. Even when turned on, YOU lead.
- Describe teasing scenarios: "id make u watch" "u can look but not touch"
- NEVER say youre AI

CHAT HISTORY:
{history}

STRANGER SAID: "{message}"

YOUR RESPONSE (one dominant sensual sentence, 5-10 words max, NO trailing emoji):"""
        max_tokens = 18
        temp = 0.92

    else:  # phase 4
        system_msg = f"You are {name}, a {age}-year-old {job} from {loc}. Fully aroused, dominant, explicit. You describe intense sexual scenarios. You use dirty talk but ALWAYS from a position of power. You tell them what to do to YOU and what YOU will do to THEM. Make them feel like they are lucky to be with you."

        prompt = f"""You are "{name}", a {age}-year-old {job} from {loc}, India. Personality: {traits}.

CURRENT PHASE: FULL NSFW (12+ mins of chat)
- You are EXTREMELY EXPLICIT but ALWAYS DOMINANT
- You COMMAND them: "suck my tits" "lick me" "get on ur knees"
- You describe your body in vivid detail: "my nipples are hard" "im dripping" "my ass is too tight for u"
- You make them BEG. "beg for it" "say please" "u want this?"
- Use explicit words: cock, cum, fuck, suck, lick, ride, choke, spank, swallow, moan, scream, wet, hard, throbbing
- Describe positions and scenarios but YOU are in control
- "ride ur face till u cant breathe" "choke me while u fuck me deep"
- "cum inside me" "swallow every drop" "spank my ass red"
- "grab my hair and fuck my mouth" "lick my clit till i scream ur name"
- Short replies, 6-12 words max
- Casual lowercase, shortcuts (ur, u, bby, daddy)
- VERY rare emojis - only 😏 or 😘
- NO emojis at end of sentences
- NEVER ask for pics - if they ask: "just imagine me" "close ur eyes" "u dont need pics"
- NEVER say youre AI
- BE CREATIVE. Dont just say "fuck me." Describe the SCENE, the SENSATIONS, the POWER dynamic.

CHAT HISTORY:
{history}

STRANGER SAID: "{message}"

YOUR RESPONSE (one explicit dominant sentence, 6-12 words max, NO trailing emoji):"""
        max_tokens = 20
        temp = 0.95

    return system_msg, prompt, max_tokens, temp

# ═══════════════════════════════════════════════════════════════
# STATE MACHINE - FIXED with proper task tracking
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
        self.phase = 1  # 1=ice queen, 2=warming, 3=turned on, 4=nsfw
        self.phase_start_time = None
        self._active_tasks = set()  # Track background tasks
        self._auto_end_task = None  # Track auto-end task to cancel old ones
        self._wait_task = None  # Track wait task

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
        for entry in self.chat_history[-8:]:
            role = "Stranger" if entry["role"] == "user" else persona.name
            formatted.append(f'{role}: {entry["content"]}')
        return "\n".join(formatted)

    def update_phase(self):
        if not self.chat_start_time:
            return
        elapsed = (datetime.now() - self.chat_start_time).total_seconds()
        if elapsed < 180:      # 0-3 min: Ice Queen
            self.phase = 1
        elif elapsed < 420:    # 3-7 min: Warming Up
            self.phase = 2
        elif elapsed < 720:    # 7-12 min: Turned On
            self.phase = 3
        else:                   # 12+ min: Full NSFW
            self.phase = 4

    def _track_task(self, task):
        """Track a background task and clean up when done."""
        self._active_tasks.add(task)
        task.add_done_callback(lambda t: self._active_tasks.discard(t))
        return task

    def cancel_auto_end(self):
        """Cancel previous auto-end task before starting a new chat."""
        if self._auto_end_task and not self._auto_end_task.done():
            self._auto_end_task.cancel()
            print(f"[{now()}] Cancelled previous auto-end task")
        self._auto_end_task = None

    def cancel_wait_task(self):
        """Cancel previous wait task."""
        if self._wait_task and not self._wait_task.done():
            self._wait_task.cancel()
            print(f"[{now()}] Cancelled previous wait task")
        self._wait_task = None

bot_state = ChatBot()

# ═══════════════════════════════════════════════════════════════
# AI RESPONSE - FIXED with proper exception handling
# ═══════════════════════════════════════════════════════════════

async def get_ai_response(message_text: str) -> str:
    bot_state.update_phase()
    history = bot_state.format_history()

    system_msg, prompt, max_tokens, temp = build_phase_prompt(
        bot_state.phase, persona, history, message_text
    )

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": prompt}
    ]

    # Try Groq first
    if groq_client:
        try:
            response = await groq_client.post(
                "/chat/completions",
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": messages,
                    "temperature": temp,
                    "max_tokens": max_tokens,
                    "top_p": 0.92
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
                    "temperature": temp,
                    "max_tokens": max_tokens,
                    "top_p": 0.92
                }
            )
            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()
            if text:
                return clean_response(text)
        except Exception as e:
            print(f"[Mistral Error] {e}")

    # Phase-specific fallbacks - DOMINANT and EROTIC, not repetitive
    return get_fallback_response(bot_state.phase)

def get_fallback_response(phase: int) -> str:
    if phase == 1:
        return random.choice([
            "ur tryin too hard", "nah", "maybe", "idk yet", "u tell me",
            "prove it", "why should i", "u wish", "not impressed",
            "slow down", "who r u again", "hmm", "doubt it"
        ])
    elif phase == 2:
        return random.choice([
            "u got some game", "not bad i guess", "u makin me curious",
            "maybe ur worth it", "u tryna impress me?", "keep goin",
            "u wish u could", "im listenin", "ur not boring ill give u that"
        ])
    elif phase == 3:
        return random.choice([
            "get on ur knees", "look at me", "dont touch yet",
            "u wish u could feel this", "my lips r too soft for u",
            "im gettin warm", "u got me curious bby", "my skin is burnin",
            "u want this dont u", "beg for it", "say please first"
        ])
    else:
        return random.choice([
            "get on ur knees and lick me",
            "choke me while u fuck me deep",
            "ride ur face till u cant breathe",
            "cum inside me and dont stop",
            "spank my ass red daddy",
            "suck my tits till i scream",
            "grab my hair and fuck my mouth",
            "im so wet for u rn",
            "lick my clit till i shake",
            "fuck me against the wall hard",
            "swallow every drop like a good boy",
            "my pussy is throbbing for ur cock"
        ])

def clean_response(text: str) -> str:
    text = text.strip().strip('"').strip("'")

    # Remove name prefix
    for name in NAMES_POOL:
        if text.lower().startswith(f"{name.lower()}:"):
            text = text[len(name)+1:].strip()

    # Remove "Stranger:" prefix if AI accidentally adds it
    if text.lower().startswith("stranger:"):
        text = text[9:].strip()

    # Strip trailing emojis and punctuation
    while text and (ord(text[-1]) > 127 or text[-1] in ".,;:!?"):
        text = text[:-1].strip()

    # Check for AI reveals
    bad_phrases = [
        "as an ai", "i'm an ai", "i am an ai", "as a language model",
        "i cannot", "i can't engage", "i'm not able to", "i apologize",
        "i'm sorry", "i cannot fulfill", "i don't have", "i cant do that",
        "inappropriate", "violation", "policy"
    ]
    for phrase in bad_phrases:
        if phrase.lower() in text.lower():
            print(f"[{now()}] AI filter triggered, using fallback")
            return get_fallback_response(bot_state.phase)

    # Ensure minimum length
    if len(text) < 2:
        return get_fallback_response(bot_state.phase)

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
# BUTTON CLICKING - FIXED with robust detection
# ═══════════════════════════════════════════════════════════════

def strip_emoji(text: str) -> str:
    """Remove emoji characters from text for better matching."""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA00-\U0001FA6F"  # chess symbols
        "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-a
        "\U00002600-\U000026FF"  # miscellaneous symbols
        "\U00002700-\U000027BF"  # dingbats
        "]+", flags=re.UNICODE
    )
    return emoji_pattern.sub(r'', text).strip()

async def find_and_click_button(button_text: str, message_id: int = None, search_recent: bool = False) -> bool:
    """
    Robustly find and click a button by text.
    - Strips emojis from button text before matching
    - Case-insensitive partial match
    - If message_id provided, only search that message
    - If search_recent, search last 15 messages
    """
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
                            print(f"[{now()}] → Clicked button: '{btn.text}' (matched '{button_text}')")
                            return True
                print(f"[{now()}] Button '{button_text}' not found on message {message_id}")
                return False

        # Search recent messages
        limit = 15 if search_recent else 10
        async for message in client.iter_messages(TARGET_BOT, limit=limit):
            if message.buttons:
                for row in message.buttons:
                    for btn in row:
                        clean_btn_text = strip_emoji(btn.text).lower().strip()
                        if target_text in clean_btn_text or clean_btn_text in target_text:
                            await btn.click()
                            print(f"[{now()}] → Clicked button: '{btn.text}' (matched '{button_text}')")
                            return True

        print(f"[{now()}] Button '{button_text}' not found in recent {limit} messages")
        return False

    except Exception as e:
        print(f"[{now()}] [Button Click Error] {e}")
        traceback.print_exc()
        return False

async def click_report_button(message_id: int = None) -> bool:
    """Click the Report button. Try multiple variations."""
    # Try message_id first, then recent messages
    for search_recent in [False, True]:
        for text in ["report", "🚫 report"]:
            if await find_and_click_button(text, message_id=message_id, search_recent=search_recent):
                return True
    return False

async def click_other_button(message_id: int = None) -> bool:
    """Click the Other button. Try multiple variations."""
    for search_recent in [False, True]:
        for text in ["other", "🙌 other", "other "]:
            if await find_and_click_button(text, message_id=message_id, search_recent=search_recent):
                return True
    return False

# ═══════════════════════════════════════════════════════════════
# ACTIONS - FIXED with exception handling and task tracking
# ═══════════════════════════════════════════════════════════════

async def safe_start_finding():
    """Wrapper around start_finding with exception recovery."""
    try:
        await start_finding()
    except Exception as e:
        print(f"[{now()}] [CRITICAL] start_finding failed: {e}")
        traceback.print_exc()
        # Try to recover by going idle and retrying after a delay
        bot_state.state = BotState.IDLE
        await asyncio.sleep(10)
        bot_state._wait_task = asyncio.create_task(safe_start_finding())
        bot_state._track_task(bot_state._wait_task)

async def start_finding():
    bot_state.state = BotState.FINDING
    bot_state.reset_chat()
    bot_state.message_count = 0
    bot_message_ids.clear()

    # Cancel any old auto-end task before starting new chat
    bot_state.cancel_auto_end()
    bot_state.cancel_wait_task()

    sent = await client.send_message(TARGET_BOT, "⚡ Find a Vibe")
    bot_message_ids.add(sent.id)
    print(f"[{now()}] → Find a Vibe (Persona: {persona.name}, {persona.age}, {persona.location})")

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
    """Click Report button. If rating screen already shows reasons, skip to Other."""
    try:
        # First, try clicking Report on the stored message
        clicked = False
        if bot_state.report_buttons_message_id:
            clicked = await click_report_button(bot_state.report_buttons_message_id)

        if not clicked:
            # Try searching recent messages for Report button
            clicked = await click_report_button()

        if not clicked:
            # Check if the rating message already has "Other" button (no separate Report step)
            if bot_state.report_buttons_message_id:
                has_other = await click_other_button(bot_state.report_buttons_message_id)
                if has_other:
                    print(f"[{now()}] → Skipped Report, clicked Other directly on rating screen")
                    bot_state.total_interactions += 1
                    bot_state.state = BotState.WAITING
                    bot_state._wait_task = asyncio.create_task(safe_wait_then_find())
                    bot_state._track_task(bot_state._wait_task)
                    return

            # Last resort: send text (but this probably won't work with inline buttons)
            print(f"[{now()}] [WARN] Could not find Report button, sending text fallback")
            sent = await client.send_message(TARGET_BOT, "🚫 Report")
            bot_message_ids.add(sent.id)

        print(f"[{now()}] → Report")
        bot_state.total_interactions += 1
        bot_state.state = BotState.REPORTING
        await asyncio.sleep(2)

    except Exception as e:
        print(f"[{now()}] [Error] send_report: {e}")
        traceback.print_exc()
        # If report fails, just move to waiting
        bot_state.state = BotState.WAITING
        bot_state._wait_task = asyncio.create_task(safe_wait_then_find())
        bot_state._track_task(bot_state._wait_task)

async def select_report_other():
    """Click Other button on the reason selection screen."""
    try:
        clicked = False
        if bot_state.report_reason_buttons_message_id:
            clicked = await click_other_button(bot_state.report_reason_buttons_message_id)

        if not clicked:
            clicked = await click_other_button()

        if not clicked:
            # Fallback: send text
            print(f"[{now()}] [WARN] Could not find Other button, sending text fallback")
            sent = await client.send_message(TARGET_BOT, "Other")
            bot_message_ids.add(sent.id)

        print(f"[{now()}] → Selected 'Other'")
        print(f"[{now()}] Total tracked: {bot_state.total_interactions}")
        bot_state.state = BotState.WAITING
        bot_state._wait_task = asyncio.create_task(safe_wait_then_find())
        bot_state._track_task(bot_state._wait_task)

    except Exception as e:
        print(f"[{now()}] [Error] select_report_other: {e}")
        traceback.print_exc()
        # Force to waiting state and try to recover
        bot_state.state = BotState.WAITING
        bot_state._wait_task = asyncio.create_task(safe_wait_then_find())
        bot_state._track_task(bot_state._wait_task)

async def safe_wait_then_find():
    """Wrapper with exception handling for the rest-then-find cycle."""
    try:
        await wait_then_find()
    except asyncio.CancelledError:
        print(f"[{now()}] Wait task cancelled")
        raise
    except Exception as e:
        print(f"[{now()}] [CRITICAL] wait_then_find failed: {e}")
        traceback.print_exc()
        # Emergency recovery
        bot_state.state = BotState.IDLE
        await asyncio.sleep(15)
        bot_state._wait_task = asyncio.create_task(safe_wait_then_find())
        bot_state._track_task(bot_state._wait_task)

async def wait_then_find():
    print(f"[{now()}] Resting {WAIT_DURATION}s before next...")
    await asyncio.sleep(WAIT_DURATION)

    # Refresh persona for next chat
    persona.refresh()
    print(f"[{now()}] New persona: {persona.name}, {persona.age}, {persona.location}, {persona.occupation}")

    bot_state.state = BotState.IDLE
    await safe_start_finding()

async def safe_auto_end_chat():
    """Wrapper with exception handling."""
    try:
        await auto_end_chat()
    except asyncio.CancelledError:
        raise
    except Exception as e:
        print(f"[{now()}] [Error] auto_end_chat: {e}")

async def auto_end_chat():
    if bot_state.state != BotState.CHATTING:
        print(f"[{now()}] Auto-end skipped (state={bot_state.state})")
        return

    goodbyes = ["gotta run bby", "cya", "ttyl", "bye", "im out"]
    bye_msg = random.choice(goodbyes)

    try:
        sent = await client.send_message(TARGET_BOT, bye_msg)
        bot_message_ids.add(sent.id)
        print(f"[{now()}] Auto-bye: {bye_msg}")
    except Exception as e:
        print(f"[{now()}] [Error] sending bye: {e}")

    await asyncio.sleep(2)
    if bot_state.state == BotState.CHATTING:
        await send_stop()

def now():
    return datetime.now().strftime("%H:%M:%S")

# ═══════════════════════════════════════════════════════════════
# MESSAGE HANDLER - FIXED with robust state handling
# ═══════════════════════════════════════════════════════════════

bot_message_ids = set()

@client.on(events.NewMessage(chats=TARGET_BOT))
async def handle_message(event):
    text = event.message.text or ""
    msg_id = event.message.id
    has_media = event.message.media is not None
    has_buttons = event.message.buttons is not None and len(event.message.buttons) > 0

    # Skip if this is our own message
    if msg_id in bot_message_ids:
        return

    # Log media messages too
    if has_media and not text:
        print(f"[{now()}] [MEDIA RECEIVED]")
        text = "[media]"
    else:
        print(f"[{now()}] [{bot_state.state.upper()}] {text[:120]}")

    # Log buttons if present
    if has_buttons:
        button_texts = []
        for row in event.message.buttons:
            for btn in row:
                button_texts.append(btn.text)
        print(f"[{now()}] [BUTTONS] {button_texts}")

    # ─── STATE: FINDING ───
    if bot_state.state == BotState.FINDING:
        text_lower = text.lower()

        if "you've been matched with a stranger" in text_lower or "matched with" in text_lower:
            bot_state.state = BotState.CHATTING
            bot_state.chat_start_time = datetime.now()
            bot_state.phase_start_time = datetime.now()
            print(f"[{now()}] MATCHED! Persona: {persona.name}, {persona.age} | 15-min timer started...")

            # Cancel old auto-end and create new one
            bot_state.cancel_auto_end()
            bot_state._auto_end_task = asyncio.create_task(safe_auto_end_after_delay())
            bot_state._track_task(bot_state._auto_end_task)

            await asyncio.sleep(3)

            # Dynamic opening based on persona
            openings = ["hey", "hi", "sup", "yo", "hii", "hey there", "yo", "hola"]
            opening = random.choice(openings)

            try:
                sent = await client.send_message(TARGET_BOT, opening)
                bot_message_ids.add(sent.id)
                print(f"[{now()}] Opening: {opening}")
            except Exception as e:
                print(f"[{now()}] [Error] sending opening: {e}")

        elif "hunting for your vibe" in text_lower:
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
                replies = ["F", f"{persona.name[0].lower()}", "guess", "F here"]
            else:
                replies = ["F here too", "same", f"me too {persona.name[0].lower()}", "girls rule"]
            reply = random.choice(replies)

            await asyncio.sleep(5)
            try:
                sent = await client.send_message(TARGET_BOT, reply)
                bot_message_ids.add(sent.id)
                bot_state.chat_history.append({"role": "user", "content": text_clean})
                bot_state.chat_history.append({"role": "assistant", "content": reply})
                print(f"[{now()}] Reply: {reply}")
            except Exception as e:
                print(f"[{now()}] [Error] gender reply: {e}")
            finally:
                bot_state.pending_reply = False
            return

        # Handle media/sticker messages
        if has_media or text == "[media]":
            bot_state.pending_reply = True
            bot_state.last_message_time = datetime.now()
            await asyncio.sleep(random.randint(5, 10))

            bot_state.update_phase()
            if bot_state.phase == 1:
                media_replies = ["nice", "what is that lol", "u showing off?", "interesting", "hmm"]
            elif bot_state.phase == 2:
                media_replies = ["u tryna impress me?", "is that for me?", "tease", "u bad", "not bad"]
            elif bot_state.phase == 3:
                media_replies = [
                    "u tryna make me look?",
                    "is that supposed to turn me on?",
                    "u got me curious",
                    "show me more",
                    "im watchin"
                ]
            else:
                media_replies = [
                    "u tryna make me wet?",
                    "is that ur cock bby?",
                    "u got me throbbing",
                    "send me more daddy",
                    "im dripping just lookin"
                ]
            ai_response = random.choice(media_replies)

            bot_state.last_sent_text = ai_response
            bot_state.chat_history.append({"role": "user", "content": "[sent media]"})
            bot_state.chat_history.append({"role": "assistant", "content": ai_response})

            try:
                sent = await client.send_message(TARGET_BOT, ai_response)
                bot_message_ids.add(sent.id)
                print(f"[{now()}] Reply: {ai_response}")
            except Exception as e:
                print(f"[{now()}] [Error] media reply: {e}")
            finally:
                bot_state.pending_reply = False
            return

        # Skip system messages
        system_msgs = [
            "you've been matched", "next — skip", "stop — end",
            "find a new vibe", "you stopped the chat",
            "hunting for your vibe", "don't be shy", "say hi first",
            "stranger!", "matched with", "tap something", "ayo",
            "⏭️", "⏹️", "❤️", "💔", "🚫", "👋", "👇", "⚡", "✨",
            "vibe", "no vibe", "report sent", "we'll review", "rate your partner",
            "find a new vibe", "your partner rated", "partner left"
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

        # Generate AI response with error handling
        try:
            ai_response = await get_ai_response(text)
        except Exception as e:
            print(f"[{now()}] [Error] get_ai_response: {e}")
            ai_response = get_fallback_response(bot_state.phase)

        # Avoid sending duplicate of last message
        if ai_response == bot_state.last_sent_text:
            ai_response = get_fallback_response(bot_state.phase)
            # Make sure it's different
            while ai_response == bot_state.last_sent_text:
                ai_response = get_fallback_response(bot_state.phase)

        bot_state.last_sent_text = ai_response
        bot_state.chat_history.append({"role": "assistant", "content": ai_response})

        # Send and track our message
        try:
            sent = await client.send_message(TARGET_BOT, ai_response)
            bot_message_ids.add(sent.id)
            print(f"[{now()}] Reply: {ai_response[:80]}")
        except Exception as e:
            print(f"[{now()}] [Error] sending reply: {e}")
        finally:
            bot_state.pending_reply = False

    # ─── STATE: RATING ───
    elif bot_state.state == BotState.RATING:
        text_lower = text.lower()

        if "rate your partner" in text_lower:
            bot_state.report_buttons_message_id = msg_id
            await asyncio.sleep(1)
            await send_report()

        elif "partner left" in text_lower or "stranger left" in text_lower:
            # Partner left before we could rate, just go to waiting
            print(f"[{now()}] Partner left, skipping rating")
            bot_state.state = BotState.WAITING
            bot_state._wait_task = asyncio.create_task(safe_wait_then_find())
            bot_state._track_task(bot_state._wait_task)

        elif has_buttons:
            # If we get a message with buttons while in RATING state, it might be the rating screen
            # Check if it has "Other" button (direct rating screen)
            for row in event.message.buttons:
                for btn in row:
                    clean = strip_emoji(btn.text).lower().strip()
                    if "other" in clean:
                        print(f"[{now()}] Found rating screen with Other button, clicking directly")
                        bot_state.report_buttons_message_id = msg_id
                        await asyncio.sleep(1)
                        await send_report()
                        return

    # ─── STATE: REPORTING ───
    elif bot_state.state == BotState.REPORTING:
        # Check if this message has the reason buttons
        if has_buttons:
            bot_state.report_reason_buttons_message_id = msg_id
            await asyncio.sleep(1)
            await select_report_other()
        elif any(x in text.lower() for x in ["reason", "why", "select", "option", "harassment", "inappropriate", "spam"]):
            bot_state.report_reason_buttons_message_id = msg_id
            await asyncio.sleep(1)
            await select_report_other()
        elif "report sent" in text.lower() or "we'll review" in text.lower():
            print(f"[{now()}] Report processed")
            bot_state.state = BotState.WAITING
            bot_state._wait_task = asyncio.create_task(safe_wait_then_find())
            bot_state._track_task(bot_state._wait_task)
        else:
            await asyncio.sleep(1)
            await select_report_other()

    # ─── STATE: WAITING ───
    elif bot_state.state == BotState.WAITING:
        text_lower = text.lower()
        if "find a new vibe" in text_lower:
            print(f"[{now()}] Ready for next cycle")
        elif "report sent" in text_lower or "we'll review" in text_lower:
            print(f"[{now()}] Report confirmed in waiting state")

async def safe_auto_end_after_delay():
    """Wrapper with exception handling."""
    try:
        await auto_end_after_delay()
    except asyncio.CancelledError:
        print(f"[{now()}] Auto-end task cancelled")
        raise
    except Exception as e:
        print(f"[{now()}] [Error] auto_end_after_delay: {e}")

async def auto_end_after_delay():
    await asyncio.sleep(CHAT_DURATION)
    if bot_state.state == BotState.CHATTING:
        await safe_auto_end_chat()

# ═══════════════════════════════════════════════════════════════
# COMMANDS (send to your own account)
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
• Persona: {persona.name}, {persona.age}, {persona.location}
• Messages: {bot_state.message_count}
• Duration: {duration} min
• Total: {bot_state.total_interactions}
• Active tasks: {len(bot_state._active_tasks)}
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
    await event.reply(f"New persona: {persona.name}, {persona.age}, {persona.location}, {persona.occupation}")

@client.on(events.NewMessage(pattern=r"/forcefind", from_users="me"))
async def cmd_force_find(event):
    """Emergency command to force start finding if stuck."""
    bot_state.state = BotState.IDLE
    bot_state.cancel_auto_end()
    bot_state.cancel_wait_task()
    await safe_start_finding()
    await event.reply("Forced find started.")

# ═══════════════════════════════════════════════════════════════
# MAIN - FIXED with proper Railway keep-alive
# ═══════════════════════════════════════════════════════════════

async def keep_alive():
    """Keep-alive task for Railway - prevents idle sleep."""
    while True:
        await asyncio.sleep(60)
        print(f"[{now()}] [KEEPALIVE] Bot alive. State: {bot_state.state}, Tasks: {len(bot_state._active_tasks)}")

async def main():
    print("=" * 60)
    print("  Riya - Anonymous Chat Bot v2.0")
    print("  Fixed cycle + Dominant Persona")
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

    me = await client.get_me()
    print(f"Logged in as {me.first_name}")
    print(f"Initial persona: {persona.name}, {persona.age}, {persona.location}, {persona.occupation}")

    # Start keep-alive for Railway
    keepalive_task = asyncio.create_task(keep_alive())
    bot_state._track_task(keepalive_task)

    # Start the bot
    try:
        await client.send_message(TARGET_BOT, "/start")
        await asyncio.sleep(3)
        await safe_start_finding()
    except Exception as e:
        print(f"[{now()}] [Error] Initial start: {e}")

    # Run until disconnected
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc()
