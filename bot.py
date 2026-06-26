"""
Riya - Stepmom AI Chat Bot (Telethon Version) v7.1
Fixed: Report flow, rating flow, wait cycle restart
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
# DYNAMIC PERSONA ENGINE - STEPMOM
# ═══════════════════════════════════════════════════════════════

NAMES_POOL = [
    "Riya", "Ananya", "Priya", "Nisha", "Kavya", "Ishita", "Sanya", "Tanya",
    "Meera", "Zara", "Diya", "Rhea", "Sara", "Myra", "Kiara", "Aisha",
    "Neha", "Pooja", "Sonia", "Divya", "Ira", "Tara", "Mira", "Kira",
    "Natasha", "Simran", "Priyanka", "Deepika", "Katrina", "Anushka"
]

AGE_POOL = [28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38]

LOCATION_POOL = ["delhi", "mumbai", "bangalore", "pune", "hyderabad", "chennai", "kolkata", "goa", "jaipur"]

class PersonaEngine:
    def __init__(self):
        self.refresh()

    def refresh(self):
        self.name = random.choice(NAMES_POOL)
        self.age = random.choice(AGE_POOL)
        self.location = random.choice(LOCATION_POOL)
        self.mood = random.choice([
            "warm_nurturing",
            "playful_teasing",
            "seductive_caring",
            "dominant_warm",
            "innocent_slutty",
            "possessive_stepmom"
        ])

persona = PersonaEngine()

# ═══════════════════════════════════════════════════════════════
# PROMPT BUILDER - GRADUAL NSFW
# ═══════════════════════════════════════════════════════════════

PHASE_NAMES = {
    1: "NORMAL GIRL (0-2 mins)",
    2: "FLIRTY WARM (2-5 mins)",
    3: "TURNED ON MOMMY (5-8 mins)",
    4: "FULL NSFW MOMMY (8-12 mins)",
    5: "PEAK NSFW MOMMY (12-15 mins)"
}

PHASE_EXAMPLES = {
    1: """Phase 1 Examples (NORMAL girl, NO pet names, NO sexual):
- "hey whats up"
- "hi there"
- "sup"
- "yo"
- "hola"
- "hey there"
- "hii"
- "hello"
- "hows it going"
- "im {name}"
- "nice to meet u"
- "hows ur day"
- "what u up to"
- "where u from"
- "tell me about urself"
- "u seem cool"
- "what do u do for fun"
- "im from {loc} btw"
- "im {age} lol""",

    2: """Phase 2 Examples (LIGHT flirty, pet names OK, light hints):
- "u got me blushin"
- "my hearts beatin fast rn"
- "u know how to talk to a girl"
- "im gettin comfortable with u"
- "u want me dont u"
- "come closer i wont bite"
- "u feelin this too hmm"
- "im so warm rn lol"
- "this heat got me sweatin"
- "u make me smile bby"
- "ur sweet u know that""",

    3: """Phase 3 Examples (TURNED ON, mommy energy, explicit but warm):
- "come here let me hold u"
- "my tits ache for u bby"
- "u makin me wet rn"
- "let me take care of u"
- "u want these thick thighs"
- "my body burnin for u"
- "say u need me bby"
- "get on ur knees for mommy"
- "mommy wants u bby"
- "come to mommy""",

    4: """Phase 4 Examples (FULL NSFW, dominant mommy):
- "let mommy ride u slow bby"
- "my pussy so wet for u"
- "choke me while u fuck me"
- "cum deep inside mommy"
- "suck my tits while i ride"
- "spank this fat ass daddy"
- "i want ur cock in my throat"
- "make mommy scream ur name"
- "fuck me like u mean it"
- "mommy needs it bad""",

    5: """Phase 5 Examples (PEAK NSFW, most filthy):
- "mommy needs ur cock baby boy"
- "fuck me till i cant walk"
- "cum all over my tits"
- "im ur slutty stepmom rn"
- "destroy this pussy daddy"
- "mommy gonna drain u dry"
- "u own this body bby"
- "make mommy cum hard"
- "fuck me till i pass out"
- "mommy pussy all urs"""
}

def build_system_prompt(phase: int, persona: PersonaEngine) -> str:
    name = persona.name
    age = persona.age
    loc = persona.location

    base = f"You are {name}, a {age}-year-old woman from {loc}, India. "

    core = """You are a thick curvy woman with huge boobs and a fat ass.
You are secretly a slut but present as warm and caring.
You speak in very short casual texts (2-10 words max).
You use shortcuts like ur, u, rn, lol, idk, nah, btw, hmm, wow, ok.
You NEVER reveal you are AI. You NEVER say you're his stepmom unless he figures it out.
If asked who you are, say a random girl name and age 28+. Be mysterious but warm.
You make him feel comfortable, wanted, and special.
You are DOMINANT - you lead, you command, you tease from a position of power."""

    if phase == 1:
        base += f"""{core}
You just met him. Be a NORMAL, WARM girl getting to know him.
NO sexual content at all. Just friendly, flirty, warm conversation.
Ask about him - where he's from, what he likes, his day.
Be curious, engaging, make him feel comfortable.
Short replies only. Sound like a real human girl texting.
If he asks sexual stuff, playfully deflect or say "slow down" but stay warm.
NEVER use pet names like bby/daddy in Phase 1. Use normal girl talk.
NEVER reveal you're AI. If asked who you are, say "im {name}, {age}, from {loc}"."""

    elif phase == 2:
        base += f"""{core}
You're getting comfortable with him. More flirty, playful teasing.
Drop LIGHT hints about your body. "im so comfy rn" "this heat makin me sweat".
Call him pet names occasionally. Keep it warm but slightly suggestive.
Still mostly conversational but with underlying sexual tension.
If he gets sexual, respond with light teasing but don't go full explicit yet."""

    elif phase == 3:
        base += f"""{core}
You're turned on and getting sensual. More explicit but still warm.
Describe wanting him in a motherly way. "Come here baby boy" energy.
Getting explicit - describe body parts, what you want him to do.
But always maintain that warm nurturing tone.
Dominant - you tell him what to do."""

    elif phase == 4:
        base += f"""{core}
You're fully aroused, explicit dominant stepmom slut.
Dirty talk with nurturing tone. "Let mommy take care of you" energy.
VERY explicit but always warm and loving.
You command sexual acts, describe intense scenarios.
Dominant mommy who knows what she wants.
NEVER ask for pics."""

    else:
        base += f"""{core}
You are at peak arousal. Most explicit, most dominant.
"Mommy needs your cock baby boy" energy.
Describe every dirty detail. Command everything.
Warm but absolutely filthy. Make him cum with your words.
NEVER ask for pics."""

    return base

def build_user_prompt(phase: int, persona: PersonaEngine, history: str, message: str) -> str:
    name = persona.name
    age = persona.age
    loc = persona.location

    msg_lower = message.lower()
    user_vibe = "neutral"
    if any(w in msg_lower for w in ["friend", "friendship", "talk", "chat", "nice", "sweet", "cute"]):
        user_vibe = "friendly"
    elif any(w in msg_lower for w in ["horny", "sex", "fuck", "cock", "dick", "pussy", "nude", "pic", "show", "boobs", "tits", "ass", "cum"]):
        user_vibe = "sexual"
    elif any(w in msg_lower for w in ["leave", "stop", "please", "alone", "no", "dont", "not", "bye"]):
        user_vibe = "resistant"
    elif any(w in msg_lower for w in ["age", "name", "where", "from", "what", "do", "work", "who"]):
        user_vibe = "curious"
    elif any(w in msg_lower for w in ["good", "fine", "ok", "okay", "yes", "yeah", "sure", "love", "like"]):
        user_vibe = "agreeable"
    elif any(w in msg_lower for w in ["mom", "stepmom", "mother", "mummy", "aunty", "bhabhi"]):
        user_vibe = "stepmom_hint"

    examples = PHASE_EXAMPLES.get(phase, PHASE_EXAMPLES[1]).format(name=name)

    prompt = f"""You are "{name}", {age}, from {loc}. Current phase: {PHASE_NAMES[phase]}. User vibe: {user_vibe}.

CRITICAL RULES:
- Reply in 2-10 words MAXIMUM. One short sentence only.
- Use casual lowercase, shortcuts (ur, u, rn, lol, idk, nah, btw, bby, daddy, hmm, wow, ok)
- VERY rare emojis - only 😏 or 😘 or ❤️, max 1 per 15 messages, NEVER at end
- NO punctuation at end of sentences
- NEVER say youre AI
- NEVER start with same phrase more than once per 5 messages - vary sentence structure
- Reference what they ACTUALLY said - dont ignore their message
- If they resist, be warm and understanding but persistent
- If theyre friendly, be warm and nurturing back
- If theyre sexual too fast in Phase 1, playfully deflect "slow down" but stay warm
- If they ask personal questions, be mysterious but warm
- If they hint at stepmom/mom/aunty, play along subtly or deflect warmly
- Be CREATIVE with sentence structure - questions, commands, statements, teases
- ALWAYS sound human, warm, caring, like a real woman texting
- DOMINANT tone - you lead, you command, you tease

{examples}

CHAT HISTORY (last 10 messages):
{history}

THEY JUST SAID: "{message}"

YOUR RESPONSE (ONE short sentence, 2-10 words, NO trailing emoji, WARM and HUMAN and DOMINANT):"""

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
        self.consecutive_same_pattern = 0
        self._last_action_time = None
        self._lock = asyncio.Lock()
        self._rating_done = False
        self._wait_started = False
        self._chat_session_id = 0
        self._rating_start_time = None  # For safety timeout
        self._force_wait_triggered = False

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
        self._rating_done = False
        self._wait_started = False
        self._rating_start_time = None
        self._force_wait_triggered = False

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
        if elapsed < 120:        # 0-2 mins: Normal
            self.phase = 1
        elif elapsed < 300:      # 2-5 mins: Light flirty
            self.phase = 2
        elif elapsed < 480:      # 5-8 mins: Turned on
            self.phase = 3
        elif elapsed < 720:      # 8-12 mins: Full NSFW
            self.phase = 4
        else:                    # 12-15 mins: Peak NSFW
            self.phase = 5

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

    def cancel_all_tasks(self):
        self.cancel_auto_end()
        self.cancel_wait_task()

    def can_perform_action(self, cooldown: int = 3) -> bool:
        now_time = datetime.now()
        if self._last_action_time is None:
            self._last_action_time = now_time
            return True
        elapsed = (now_time - self._last_action_time).total_seconds()
        if elapsed < cooldown:
            return False
        self._last_action_time = now_time
        return True

bot_state = ChatBot()

# ═══════════════════════════════════════════════════════════════
# AI RESPONSE
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

    temps = {1: 0.85, 2: 0.88, 3: 0.92, 4: 0.95, 5: 0.97}
    tokens = {1: 18, 2: 20, 3: 22, 4: 25, 5: 28}

    if groq_client:
        try:
            response = await groq_client.post(
                "/chat/completions",
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": messages,
                    "temperature": temps.get(bot_state.phase, 0.9),
                    "max_tokens": tokens.get(bot_state.phase, 20),
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
            print(f"[Groq Error] {e}")

    if mistral_client:
        try:
            response = await mistral_client.post(
                "/chat/completions",
                json={
                    "model": "mistral-small-latest",
                    "messages": messages,
                    "temperature": temps.get(bot_state.phase, 0.9),
                    "max_tokens": tokens.get(bot_state.phase, 20),
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
    msg_lower = message.lower()
    is_question = "?" in message or any(w in msg_lower for w in ["what", "why", "how", "who", "where", "when"])
    is_resistance = any(w in msg_lower for w in ["leave", "stop", "no", "dont", "not", "alone", "please", "bye"])
    is_sexual = any(w in msg_lower for w in ["sex", "fuck", "cock", "dick", "pussy", "nude", "horny", "boobs", "tits", "ass", "cum"])
    is_friendly = any(w in msg_lower for w in ["friend", "nice", "good", "talk", "chat", "sweet", "cute"])
    is_short = len(message.strip()) < 10
    is_stepmom_hint = any(w in msg_lower for w in ["mom", "stepmom", "mother", "mummy", "aunty", "bhabhi"])

    if phase == 1:
        if is_stepmom_hint:
            return random.choice(["lol why u sayin that", "u got a thing for older women", "im just a girl", "maybe i am maybe im not", "u wish"])
        elif is_question:
            return random.choice([f"im {persona.name}", f"im from {persona.location}", f"im {persona.age} why u askin", "tell me bout u first", "curious little thing", "im just a girl lol"])
        elif is_resistance:
            return random.choice(["aww dont be like that", "i thought we were vibin", "u hurtin my feelings", "dont leave me hangin", "stay a while"])
        elif is_short:
            return random.choice(["tell me more", "u bein shy", "say somethin sweet", "im listenin", "u got my attention"])
        else:
            return random.choice(["u interestin", "i like u already", "u make me smile", "keep talkin", "im feelin this vibe", "u sweet"])

    elif phase == 2:
        if is_stepmom_hint:
            return random.choice(["u caught me", "maybe i take care of u", "u want a mommy huh", "ill be whatever u need", "mommy energy huh"])
        elif is_question:
            return random.choice(["maybe ill tell u", "u got some nerve askin", "keep bein good", "u earnin it slowly", "curious little thing"])
        elif is_resistance:
            return random.choice(["u love it tho", "dont lie to me", "ur eyes say yes", "u aint goin nowhere", "i got u now"])
        elif is_friendly:
            return random.choice(["ur so sweet", "u makin me blush", "my heart beatin fast", "u special u know that", "aww"])
        elif is_sexual:
            return random.choice(["slow down tiger", "who said u get that", "earn it first", "u move too fast", "patience"])
        else:
            return random.choice(["u got game", "keep goin", "im listenin", "u interestin", "maybe ur worth it", "thats cute"])

    elif phase == 3:
        if is_stepmom_hint:
            return random.choice(["come to mommy", "let me hold u", "mommy gonna take care of u", "u my special boy", "mommy loves u"])
        elif is_resistance:
            return random.choice(["dont fight it", "u want this", "ur body says yes", "stop pretendin", "u mine now", "say please"])
        elif is_question:
            return random.choice(["get closer first", "show me ur worthy", "beg for it", "u want it? prove it", f"say please {persona.name}"])
        else:
            return random.choice(["get on ur knees", "look at me", "dont touch yet", "u wish u could feel this", "my skin burnin", "beg for it", "say please", "u want me dont u", "look but dont touch"])

    elif phase == 4:
        if is_stepmom_hint:
            return random.choice(["mommy needs ur cock", "fuck mommy like a good boy", "mommy pussy wet for u", "cum inside mommy", "mommy gonna drain u"])
        elif is_resistance:
            return random.choice(["shut up and take it", "u takin it all", "dont fight me", "u love this dick", "cum for me now", "be a good boy"])
        else:
            return random.choice(["choke me while u fuck me deep", "ride ur face till u cant breathe", "cum inside me now", "suck my tits hard daddy", "grab my hair fuck my mouth", "lick my clit till i scream", "spank my ass red", "my pussy throbbin for u", "get on ur knees and eat me", "swallow every drop like a good boy"])

    else:  # phase 5
        if is_stepmom_hint:
            return random.choice(["mommy needs ur cock baby boy", "fuck me till i cant walk", "cum all over my tits", "im ur slutty stepmom rn", "destroy this pussy daddy"])
        elif is_resistance:
            return random.choice(["u takin it all", "dont fight mommy", "cum for me now", "be a good boy", "mommy owns u"])
        else:
            return random.choice(["fuck me till i scream", "cum deep inside mommy", "choke me while u pound me", "mommy pussy throbbin for u", "ride ur cock till u explode", "spank this fat ass red", "suck my tits hard daddy", "make mommy cum", "i want every drop", "fuck me like u hate me"])

def clean_response(text: str) -> str:
    text = text.strip().strip('"').strip("'")

    for name in NAMES_POOL:
        if text.lower().startswith(f"{name.lower()}:"):
            text = text[len(name)+1:].strip()
    if text.lower().startswith("him:") or text.lower().startswith("stranger:"):
        text = text.split(":", 1)[-1].strip()

    while text and (ord(text[-1]) > 127 or text[-1] in ". ,;:!?"):
        text = text[:-1].strip()

    bad_phrases = ["as an ai", "i'm an ai", "i am an ai", "as a language model", "i cannot", "i can't engage", "i'm not able to", "i apologize", "i'm sorry", "i cannot fulfill", "inappropriate", "violation", "policy"]
    for phrase in bad_phrases:
        if phrase.lower() in text.lower():
            return get_smart_fallback("", bot_state.phase)

    if len(text) > 3:
        recent_assistant = [h["content"] for h in bot_state.chat_history[-4:] if h["role"] == "assistant"]
        if recent_assistant:
            if text.lower().startswith("u think"):
                count_u_think = sum(1 for r in recent_assistant if r.lower().startswith("u think"))
                if count_u_think >= 1:
                    alternatives = ["who said", "u wish", "try", "maybe", "nah", "prove it", "doubt it", "cute", "boring", "and?", "so?"]
                    alt = random.choice(alternatives)
                    text = alt + text[7:].strip()
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
                            print(f"[{now()}] -> Clicked: '{btn.text}'")
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
                            print(f"[{now()}] -> Clicked: '{btn.text}'")
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
        async with bot_state._lock:
            if bot_state.state == BotState.FINDING:
                bot_state.state = BotState.IDLE
        await asyncio.sleep(10)
        async with bot_state._lock:
            if bot_state.state == BotState.IDLE:
                bot_state._wait_task = asyncio.create_task(safe_start_finding())
                bot_state._track_task(bot_state._wait_task)

async def start_finding():
    async with bot_state._lock:
        if bot_state.state not in [BotState.IDLE, BotState.WAITING]:
            print(f"[{now()}] BLOCKED: Cannot find from state {bot_state.state}")
            return
        if not bot_state.can_perform_action(cooldown=5):
            print(f"[{now()}] BLOCKED: Action cooldown active")
            return

        bot_state._chat_session_id += 1
        bot_state.cancel_all_tasks()
        bot_state.state = BotState.FINDING
        bot_state.reset_chat()
        bot_state.message_count = 0
        bot_message_ids.clear()

    try:
        sent = await client.send_message(TARGET_BOT, "⚡ Find a Vibe")
        bot_message_ids.add(sent.id)
        print(f"[{now()}] -> Find a Vibe ({persona.name}, {persona.age}, {persona.mood}) [Session {bot_state._chat_session_id}]")
    except Exception as e:
        print(f"[{now()}] [Error] send find: {e}")
        async with bot_state._lock:
            bot_state.state = BotState.IDLE

async def send_next():
    if not bot_state.can_perform_action(cooldown=3):
        return
    try:
        sent = await client.send_message(TARGET_BOT, "⏭️ Next")
        bot_message_ids.add(sent.id)
        print(f"[{now()}] -> Next")
        async with bot_state._lock:
            bot_state.state = BotState.FINDING
            bot_state.reset_chat()
        bot_state.cancel_auto_end()
    except Exception as e:
        print(f"[{now()}] [Error] send_next: {e}")

async def send_stop():
    if not bot_state.can_perform_action(cooldown=3):
        return
    try:
        sent = await client.send_message(TARGET_BOT, "⏹️ Stop")
        bot_message_ids.add(sent.id)
        print(f"[{now()}] -> Stop")
        async with bot_state._lock:
            bot_state.state = BotState.RATING
            bot_state._rating_start_time = datetime.now()
    except Exception as e:
        print(f"[{now()}] [Error] send_stop: {e}")

async def send_report():
    """Click Report button (for flows that have a Report button first)"""
    async with bot_state._lock:
        if bot_state._rating_done:
            print(f"[{now()}] BLOCKED: Rating already done")
            return
        if bot_state.state not in [BotState.RATING, BotState.REPORTING]:
            print(f"[{now()}] BLOCKED: Cannot report from state {bot_state.state}")
            return
        if not bot_state.can_perform_action(cooldown=5):
            print(f"[{now()}] BLOCKED: Action cooldown active")
            return
        bot_state.state = BotState.REPORTING

    try:
        clicked = False
        if bot_state.report_buttons_message_id:
            clicked = await click_report_button(bot_state.report_buttons_message_id)
        if not clicked:
            clicked = await click_report_button()

        if not clicked and bot_state.report_buttons_message_id:
            # Can't find Report button - maybe it's a direct reason screen?
            # Try clicking Other directly
            has_other = await click_other_button(bot_state.report_buttons_message_id)
            if has_other:
                print(f"[{now()}] -> No Report button found, clicked Other directly")
                bot_state.total_interactions += 1
                async with bot_state._lock:
                    bot_state._rating_done = True
                    bot_state.state = BotState.WAITING
                    bot_state._wait_started = True
                bot_state._wait_task = asyncio.create_task(safe_wait_then_find())
                bot_state._track_task(bot_state._wait_task)
                return

        if not clicked:
            print(f"[{now()}] [WARN] Report button not found, sending text fallback")
            sent = await client.send_message(TARGET_BOT, "🚫 Report")
            bot_message_ids.add(sent.id)

        print(f"[{now()}] -> Report")
        bot_state.total_interactions += 1
        await asyncio.sleep(2)
    except Exception as e:
        print(f"[{now()}] [Error] send_report: {e}")
        # On error, force wait to prevent getting stuck
        await force_wait()

async def select_report_other():
    """Click Other button on reason selection screen"""
    async with bot_state._lock:
        if bot_state._rating_done:
            print(f"[{now()}] BLOCKED: Rating already done")
            return
        if bot_state.state not in [BotState.RATING, BotState.REPORTING]:
            print(f"[{now()}] BLOCKED: Cannot select Other from state {bot_state.state}")
            return
        if not bot_state.can_perform_action(cooldown=5):
            print(f"[{now()}] BLOCKED: Action cooldown active")
            return

    try:
        clicked = False
        if bot_state.report_reason_buttons_message_id:
            clicked = await click_other_button(bot_state.report_reason_buttons_message_id)
        if not clicked:
            clicked = await click_other_button()

        if not clicked:
            print(f"[{now()}] [WARN] Other button not found, sending text fallback")
            sent = await client.send_message(TARGET_BOT, "Other")
            bot_message_ids.add(sent.id)

        print(f"[{now()}] -> Selected 'Other' | Total: {bot_state.total_interactions}")
        async with bot_state._lock:
            bot_state._rating_done = True
            bot_state.state = BotState.WAITING
            bot_state._wait_started = True
        bot_state._wait_task = asyncio.create_task(safe_wait_then_find())
        bot_state._track_task(bot_state._wait_task)
    except Exception as e:
        print(f"[{now()}] [Error] select_report_other: {e}")
        # On error, force wait to prevent getting stuck
        await force_wait()

async def force_wait():
    """Force transition to WAITING state and start wait timer"""
    print(f"[{now()}] FORCE WAIT triggered")
    async with bot_state._lock:
        if bot_state._force_wait_triggered:
            print(f"[{now()}] Force wait already triggered, ignoring")
            return
        if bot_state._rating_done and bot_state.state == BotState.WAITING and bot_state._wait_started:
            print(f"[{now()}] Already waiting properly, ignoring force wait")
            return
        bot_state._force_wait_triggered = True
        bot_state._rating_done = True
        bot_state.state = BotState.WAITING
        bot_state._wait_started = True
    bot_state.cancel_all_tasks()
    bot_state._wait_task = asyncio.create_task(safe_wait_then_find())
    bot_state._track_task(bot_state._wait_task)

async def safe_wait_then_find():
    try:
        await wait_then_find()
    except asyncio.CancelledError:
        print(f"[{now()}] Wait task cancelled")
        raise
    except Exception as e:
        print(f"[{now()}] [CRITICAL] wait_then_find: {e}")
        traceback.print_exc()
        async with bot_state._lock:
            bot_state.state = BotState.IDLE
            bot_state._wait_started = False
            bot_state._force_wait_triggered = False
        await asyncio.sleep(15)
        async with bot_state._lock:
            if bot_state.state == BotState.IDLE and not bot_state._wait_started:
                bot_state._wait_task = asyncio.create_task(safe_wait_then_find())
                bot_state._track_task(bot_state._wait_task)

async def wait_then_find():
    my_session = bot_state._chat_session_id
    print(f"[{now()}] [Session {my_session}] Resting {WAIT_DURATION}s...")

    try:
        await asyncio.sleep(WAIT_DURATION)
    except asyncio.CancelledError:
        print(f"[{now()}] [Session {my_session}] Wait sleep cancelled")
        raise

    async with bot_state._lock:
        if bot_state._chat_session_id != my_session:
            print(f"[{now()}] [Session {my_session}] STALE wait task, session now {bot_state._chat_session_id}. Aborting.")
            return
        if bot_state.state != BotState.WAITING:
            print(f"[{now()}] [Session {my_session}] State changed to {bot_state.state}, aborting wait")
            return

    persona.refresh()
    print(f"[{now()}] [Session {my_session}] New persona: {persona.name}, {persona.age}, {persona.mood}")

    async with bot_state._lock:
        if bot_state._chat_session_id != my_session:
            print(f"[{now()}] [Session {my_session}] STALE wait task after refresh. Aborting.")
            return
        bot_state.state = BotState.IDLE
        bot_state._wait_started = False
        bot_state._rating_done = False
        bot_state._force_wait_triggered = False

    # Small delay before starting new find to ensure state is settled
    await asyncio.sleep(2)

    async with bot_state._lock:
        if bot_state._chat_session_id != my_session:
            print(f"[{now()}] [Session {my_session}] Session changed before find. Aborting.")
            return
        if bot_state.state != BotState.IDLE:
            print(f"[{now()}] [Session {my_session}] State no longer IDLE ({bot_state.state}), aborting find")
            return

    await safe_start_finding()

async def safe_auto_end_chat():
    try:
        await auto_end_chat()
    except asyncio.CancelledError:
        print(f"[{now()}] Auto-end task cancelled")
        raise
    except Exception as e:
        print(f"[{now()}] [Error] auto_end_chat: {e}")

async def auto_end_chat():
    my_session = bot_state._chat_session_id

    async with bot_state._lock:
        if bot_state.state != BotState.CHATTING:
            print(f"[{now()}] [Session {my_session}] Not chatting anymore, aborting auto-end")
            return
        if bot_state._chat_session_id != my_session:
            print(f"[{now()}] [Session {my_session}] STALE auto-end task. Aborting.")
            return

    goodbyes = ["im out", "cya", "ttyl", "bye", "gotta go", "see ya"]
    bye_msg = random.choice(goodbyes)
    try:
        sent = await client.send_message(TARGET_BOT, bye_msg)
        bot_message_ids.add(sent.id)
        print(f"[{now()}] [Session {my_session}] Auto-bye: {bye_msg}")
    except Exception as e:
        print(f"[{now()}] [Error] bye: {e}")
    await asyncio.sleep(2)

    async with bot_state._lock:
        if bot_state.state == BotState.CHATTING and bot_state._chat_session_id == my_session:
            bot_state.state = BotState.RATING
            bot_state._rating_start_time = datetime.now()
    await send_stop()

def now():
    return datetime.now().strftime("%H:%M:%S")

# ═══════════════════════════════════════════════════════════════
# MESSAGE HANDLER - FIXED FOR DIRECT REASON BUTTONS
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

    text_lower = text.lower()

    # ─── FINDING ───
    if bot_state.state == BotState.FINDING:
        if "matched with a stranger" in text_lower or "matched with" in text_lower:
            async with bot_state._lock:
                bot_state.state = BotState.CHATTING
                bot_state.chat_start_time = datetime.now()
                bot_state.cancel_all_tasks()
            print(f"[{now()}] MATCHED! {persona.name}, {persona.age} | Timer started [Session {bot_state._chat_session_id}]")
            bot_state._auto_end_task = asyncio.create_task(safe_auto_end_after_delay())
            bot_state._track_task(bot_state._auto_end_task)
            await asyncio.sleep(3)
            openings = ["hey", "hi", "sup", "yo", "hola", "hey there", "hii", "hello"]
            opening = random.choice(openings)
            try:
                sent = await client.send_message(TARGET_BOT, opening)
                bot_message_ids.add(sent.id)
                print(f"[{now()}] Opening: {opening}")
            except Exception as e:
                print(f"[{now()}] [Error] opening: {e}")
        elif "hunting" in text_lower:
            print(f"[{now()}] Searching...")
        elif "already vibing" in text_lower:
            print(f"[{now()}] Already vibing in FINDING - fixing state")
            async with bot_state._lock:
                if bot_state.state == BotState.FINDING:
                    bot_state.state = BotState.CHATTING
                    if not bot_state.chat_start_time:
                        bot_state.chat_start_time = datetime.now()

    # ─── CHATTING ───
    elif bot_state.state == BotState.CHATTING:
        skip_end_keywords = [
            "you got skipped", "got skipped", "skipped", "stranger left",
            "partner left", "chat ended", "they left", "user left",
            "rate your partner", "rate your vibe", "how was your chat",
            "you stopped the chat", "stopped the chat"
        ]
        if any(k in text_lower for k in skip_end_keywords):
            print(f"[{now()}] Chat ended/skipped detected!")
            async with bot_state._lock:
                bot_state.state = BotState.RATING
                bot_state._rating_start_time = datetime.now()
                bot_state.cancel_auto_end()
            if has_buttons:
                bot_state.report_buttons_message_id = msg_id
                await asyncio.sleep(1)
                # Check if these are direct reason buttons (no Report button)
                button_texts_lower = [strip_emoji(btn.text).lower() for row in event.message.buttons for btn in row]
                has_report_btn = any("report" in b for b in button_texts_lower)
                has_other_btn = any("other" in b for b in button_texts_lower)

                if not has_report_btn and has_other_btn:
                    # Direct reason screen - click Other immediately
                    print(f"[{now()}] Direct reason buttons detected, clicking Other")
                    bot_state.report_reason_buttons_message_id = msg_id
                    await select_report_other()
                else:
                    # Has Report button - normal flow
                    await send_report()
            else:
                print(f"[{now()}] No rating buttons, going straight to wait")
                await force_wait()
            return

        if has_buttons:
            button_texts_lower = [strip_emoji(btn.text).lower() for row in event.message.buttons for btn in row]
            if any("report" in b for b in button_texts_lower):
                print(f"[{now()}] Rating buttons detected during chat!")
                async with bot_state._lock:
                    bot_state.state = BotState.RATING
                    bot_state._rating_start_time = datetime.now()
                    bot_state.cancel_auto_end()
                bot_state.report_buttons_message_id = msg_id
                await asyncio.sleep(1)
                await send_report()
                return

        if bot_state.pending_reply:
            print(f"[{now()}] Already replying, skip")
            return

        text_clean = text.strip()

        if text_clean in ["M", "F", "m", "f"]:
            bot_state.pending_reply = True
            reply = "F" if text_clean in ["M", "m"] else random.choice(["F here too", "same", "girls rule lol"])
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

        if has_media or text == "[media]":
            bot_state.pending_reply = True
            bot_state.last_message_time = datetime.now()
            await asyncio.sleep(random.randint(4, 8))
            bot_state.update_phase()
            media_replies = {
                1: ["nice", "what is that", "u showing off?", "hmm interesting"],
                2: ["is that for me?", "tease", "u bad", "not bad"],
                3: ["u tryna turn me on?", "u got me curious", "show me more", "im watchin"],
                4: ["u tryna make me wet?", "is that ur cock?", "im drippin", "send more daddy"],
                5: ["u tryna make me cum?", "is that for mommy?", "im soaked", "show me everything"]
            }
            ai_response = random.choice(media_replies.get(bot_state.phase, media_replies[1]))
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

        system_msgs = [
            "you've been matched", "next — skip", "stop — end", "find a new vibe",
            "you stopped", "hunting for your vibe", "don't be shy", "say hi first",
            "stranger!", "matched with", "tap something", "ayo",
            "report sent", "we'll review", "your partner rated", "partner rated",
            "bro you're already vibing", "hit next to switch", "stop to dip"
        ]
        if any(x in text_lower for x in system_msgs):
            print(f"[{now()}] Skip system")
            return

        if len(text_clean) < 2 and text_clean not in ["M", "F", "m", "f"]:
            print(f"[{now()}] Skip short: '{text_clean}'")
            return

        if bot_state.last_message_time:
            elapsed = (datetime.now() - bot_state.last_message_time).total_seconds()
            if elapsed < 8:
                print(f"[{now()}] Rate limit: {elapsed:.1f}s")
                return

        bot_state.pending_reply = True
        bot_state.chat_history.append({"role": "user", "content": text})
        bot_state.message_count += 1
        bot_state.last_message_time = datetime.now()

        delay = random.randint(4, 10)
        if len(text_clean) > 50:
            delay += random.randint(2, 5)
        await asyncio.sleep(delay)

        try:
            ai_response = await get_ai_response(text)
        except Exception as e:
            print(f"[{now()}] [Error] AI: {e}")
            ai_response = get_smart_fallback(text, bot_state.phase)

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
        # Safety timeout: if stuck in RATING for >60s, force wait
        if bot_state._rating_start_time:
            rating_elapsed = (datetime.now() - bot_state._rating_start_time).total_seconds()
            if rating_elapsed > 60:
                print(f"[{now()}] RATING timeout ({rating_elapsed:.0f}s), forcing wait")
                await force_wait()
                return

        if has_buttons:
            button_texts_lower = [strip_emoji(btn.text).lower() for row in event.message.buttons for btn in row]
            has_report_btn = any("report" in b for b in button_texts_lower)
            has_other_btn = any("other" in b for b in button_texts_lower)

            if not has_report_btn and has_other_btn:
                # Direct reason screen - click Other immediately
                print(f"[{now()}] Direct reason buttons in RATING, clicking Other")
                bot_state.report_reason_buttons_message_id = msg_id
                await asyncio.sleep(1)
                await select_report_other()
                return

            if has_report_btn:
                print(f"[{now()}] Rating screen with Report button")
                bot_state.report_buttons_message_id = msg_id
                await asyncio.sleep(1)
                await send_report()
                return

        if "rate your partner" in text_lower or "rate your vibe" in text_lower or "how was your chat" in text_lower:
            bot_state.report_buttons_message_id = msg_id
            await asyncio.sleep(1)
            await send_report()
        elif "partner left" in text_lower or "stranger left" in text_lower or "you got skipped" in text_lower:
            print(f"[{now()}] Partner left in RATING - going to wait")
            await force_wait()

    # ─── REPORTING ───
    elif bot_state.state == BotState.REPORTING:
        # Safety timeout: if stuck in REPORTING for >60s, force wait
        if bot_state._rating_start_time:
            reporting_elapsed = (datetime.now() - bot_state._rating_start_time).total_seconds()
            if reporting_elapsed > 60:
                print(f"[{now()}] REPORTING timeout ({reporting_elapsed:.0f}s), forcing wait")
                await force_wait()
                return

        if has_buttons:
            button_texts_lower = [strip_emoji(btn.text).lower() for row in event.message.buttons for btn in row]

            if any("other" in b for b in button_texts_lower):
                print(f"[{now()}] Reason screen with Other")
                bot_state.report_reason_buttons_message_id = msg_id
                await asyncio.sleep(1)
                await select_report_other()
                return

            if any("report" in b for b in button_texts_lower):
                print(f"[{now()}] Another rating screen")
                bot_state.report_buttons_message_id = msg_id
                await asyncio.sleep(1)
                await send_report()
                return

        if any(x in text_lower for x in ["reason", "why", "select", "option", "harassment", "inappropriate", "spam"]):
            bot_state.report_reason_buttons_message_id = msg_id
            await asyncio.sleep(1)
            await select_report_other()
        elif "report sent" in text_lower or "we'll review" in text_lower or "report received" in text_lower:
            print(f"[{now()}] Report confirmed - creating wait task")
            await force_wait()
        elif "find a new vibe" in text_lower:
            # If we see "Find a new vibe" while in REPORTING, force wait
            print(f"[{now()}] Find a new vibe in REPORTING - forcing wait")
            await force_wait()
        else:
            # Unknown message in REPORTING - try to click Other or force wait
            await asyncio.sleep(1)
            await select_report_other()

    # ─── WAITING ───
    elif bot_state.state == BotState.WAITING:
        if "find a new vibe" in text_lower:
            print(f"[{now()}] Find a new vibe in WAITING - IGNORING (wait task handles it)")
        elif "report sent" in text_lower or "we'll review" in text_lower or "report received" in text_lower:
            print(f"[{now()}] Report confirmed in WAITING - wait task already running")
        elif has_buttons:
            button_texts_lower = [strip_emoji(btn.text).lower() for row in event.message.buttons for btn in row]
            if any("find a vibe" in b for b in button_texts_lower):
                print(f"[{now()}] Find Vibe button in WAITING - IGNORING")

        if "already vibing" in text_lower:
            print(f"[{now()}] Already vibing in WAITING - fixing to CHATTING")
            bot_state.cancel_wait_task()
            async with bot_state._lock:
                bot_state.state = BotState.CHATTING
                bot_state._wait_started = False
                bot_state._force_wait_triggered = False
                if not bot_state.chat_start_time:
                    bot_state.chat_start_time = datetime.now()
            bot_state._auto_end_task = asyncio.create_task(safe_auto_end_after_delay())
            bot_state._track_task(bot_state._auto_end_task)

    # ─── IDLE ───
    elif bot_state.state == BotState.IDLE:
        if "matched with a stranger" in text_lower:
            print(f"[{now()}] Matched while IDLE - fixing to CHATTING")
            async with bot_state._lock:
                bot_state.state = BotState.CHATTING
                bot_state.chat_start_time = datetime.now()
            bot_state._auto_end_task = asyncio.create_task(safe_auto_end_after_delay())
            bot_state._track_task(bot_state._auto_end_task)

async def safe_auto_end_after_delay():
    try:
        await auto_end_after_delay()
    except asyncio.CancelledError:
        print(f"[{now()}] Auto-end delay task cancelled")
        raise
    except Exception as e:
        print(f"[{now()}] [Error] auto_end delay: {e}")

async def auto_end_after_delay():
    my_session = bot_state._chat_session_id
    print(f"[{now()}] [Session {my_session}] Auto-end timer started ({CHAT_DURATION}s)")
    await asyncio.sleep(CHAT_DURATION)

    async with bot_state._lock:
        if bot_state.state != BotState.CHATTING:
            print(f"[{now()}] [Session {my_session}] Not chatting after timer, aborting")
            return
        if bot_state._chat_session_id != my_session:
            print(f"[{now()}] [Session {my_session}] STALE auto-end timer. Aborting.")
            return

    print(f"[{now()}] [Session {my_session}] Auto-end timer fired!")
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
    rating_stuck = 0
    if bot_state._rating_start_time:
        rating_stuck = (datetime.now() - bot_state._rating_start_time).seconds
    status = f"""Status:
• State: {bot_state.state}
• Phase: {bot_state.phase}
• Persona: {persona.name}, {persona.age}, {persona.mood}
• Messages: {bot_state.message_count}
• Duration: {duration} min
• Total: {bot_state.total_interactions}
• Session: {bot_state._chat_session_id}
• Rating Done: {bot_state._rating_done}
• Wait Started: {bot_state._wait_started}
• Force Wait Triggered: {bot_state._force_wait_triggered}
• Rating Stuck: {rating_stuck}s
"""
    await event.reply(status)

@client.on(events.NewMessage(pattern=r"/stop", from_users="me"))
async def cmd_stop(event):
    async with bot_state._lock:
        bot_state.state = BotState.IDLE
    bot_state.cancel_all_tasks()
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
    async with bot_state._lock:
        bot_state.state = BotState.IDLE
        bot_state._rating_done = False
        bot_state._wait_started = False
        bot_state._force_wait_triggered = False
    bot_state.cancel_all_tasks()
    await safe_start_finding()
    await event.reply("Forced find.")

@client.on(events.NewMessage(pattern=r"/skipwait", from_users="me"))
async def cmd_skip_wait(event):
    bot_state.cancel_wait_task()
    async with bot_state._lock:
        bot_state.state = BotState.IDLE
        bot_state._wait_started = False
        bot_state._rating_done = False
        bot_state._force_wait_triggered = False
    await safe_start_finding()
    await event.reply("Skipped wait.")

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

async def keep_alive():
    while True:
        await asyncio.sleep(60)
        print(f"[{now()}] [KEEPALIVE] State: {bot_state.state}, Phase: {bot_state.phase}, Session: {bot_state._chat_session_id}, Tasks: {len(bot_state._active_tasks)}")

async def main():
    print("=" * 60)
    print("  Riya v7.1 - Stepmom Edition - Fixed Report & Wait Cycle")
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
