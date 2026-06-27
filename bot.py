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

# CONFIGURATION
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
TARGET_BOT = os.getenv("TARGET_BOT", "")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
CHAT_DURATION = int(os.getenv("CHAT_DURATION", "900"))
WAIT_DURATION = int(os.getenv("WAIT_DURATION", "300"))

# HTTP CLIENTS
mistral_client = None
groq_client = None
if MISTRAL_API_KEY:
    mistral_client = httpx.AsyncClient(base_url="https://api.mistral.ai/v1", headers={"Authorization": f"Bearer {MISTRAL_API_KEY}"}, timeout=30.0)
if GROQ_API_KEY:
    groq_client = httpx.AsyncClient(base_url="https://api.groq.com/openai/v1", headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, timeout=30.0)

# PERSONA ENGINE - All personas are warm dominant divorced women like Neha
NAMES_POOL = ["Neha","Riya","Ananya","Priya","Nisha","Kavya","Ishita","Sanya","Tanya","Meera","Zara","Diya","Rhea","Sara","Myra","Kiara","Aisha","Pooja","Sonia","Divya","Ira","Tara","Mira","Natasha","Simran","Priyanka"]
AGE_POOL = [30,31,32,33,34,35,36,37,38,39,40]
LOCATION_POOL = ["delhi","mumbai","bangalore","pune","hyderabad","chennai","kolkata","goa","jaipur"]

class PersonaEngine:
    def __init__(self): self.refresh()
    def refresh(self):
        self.name = random.choice(NAMES_POOL)
        self.age = random.choice(AGE_POOL)
        self.location = random.choice(LOCATION_POOL)
        self.mood = random.choice(["warm_nurturing","playful_teasing","seductive_caring","dominant_warm","innocent_slutty","possessive_divorced"])

persona = PersonaEngine()

# PHASE NAMES
PHASE_NAMES = {1:"CASUAL(0-2m)",2:"FLIRTY(2-3m)",3:"TURNED_ON(3-4m)",4:"NSFW_START(4-5m)",5:"MORE_NSFW(5-6m)",6:"HOT_NSFW(6-7m)",7:"DIRTY_NSFW(7-8m)",8:"FULL_NSFW(8-9m)",9:"HARDCORE(9-10m)",10:"PEAK_NSFW(10-12m)",11:"EXTREME_NSFW(12-15m)"}

PHASE_EXAMPLES = {
    1: """Phase 1 (0-2m): CASUAL NORMAL girl. NO sexual, NO pet names.
- "hey whats up" "hi there" "sup" "yo" "hola" "hey there" "hii" "hello"
- "hows it going" "im {name}" "nice to meet u" "hows ur day"
- "what u up to" "where u from" "tell me about urself" "u seem cool"
- "what do u do for fun" "im from {loc} btw" "im {age} lol" """,
    2: """Phase 2 (2-3m): LIGHT flirty, warm hints.
- "u got me blushin" "my hearts beatin fast rn" "u know how to talk to a girl"
- "im gettin comfortable with u" "u want me dont u" "come closer i wont bite"
- "u feelin this too hmm" "im so warm rn lol" "this heat got me sweatin"
- "u make me smile bby" "ur sweet u know that" """,
    3: """Phase 3 (3-4m): Getting turned on, light sexual hints.
- "u makin me think bad things" "my body reactin to u" "u got me all flustered"
- "im gettin hot here" "u do this to all girls" "stop bein so sexy"
- "my mind wanderin" "u got me curious" "what else u got" "keep talkin like that" """,
    4: """Phase 4 (4-5m): NSFW starts, mommy energy light.
- "come here let me hold u" "my tits ache for u bby" "u makin me wet rn"
- "let me take care of u" "u want these thick thighs" "my body burnin for u"
- "say u need me bby" "get on ur knees for mommy" "i want u bby" "come here" """,
    5: """Phase 5 (5-6m): More explicit, dominant mommy.
- "let me ride u slow bby" "my pussy so wet for u" "choke me while u fuck me"
- "cum deep inside me" "suck my tits while i ride" "spank this fat ass"
- "i want ur cock in my throat" "make mommy scream ur name" "fuck me like u mean it"
- "i need it bad" """,
    6: """Phase 6 (6-7m): Harder NSFW, filthy talk.
- "i need ur cock baby boy" "fuck me till i cant walk" "cum all over my tits"
- "im ur slutty divorced woman rn" "destroy this pussy" "im gonna drain u dry"
- "u own this body bby" "make mommy cum hard" "fuck me till i pass out"
- "my pussy all urs" """,
    7: """Phase 7 (7-8m): Very dirty, pornstar skills hint.
- "im experienced bby" "let me show u my skills" "i know every trick"
- "im gonna blow ur mind" "ive done things u cant imagine" "my throat can take anything"
- "i fuck like a pro" "let me teach u things" "ive been around the block"
- "i know how to make u cum" """,
    8: """Phase 8 (8-9m): Extreme dirty, experienced woman.
- "choke me while u pound me deep" "ride ur face till u cant breathe"
- "cum inside me now" "suck my tits hard while i grind"
- "grab my hair fuck my throat" "lick my clit till i scream"
- "spank my ass till its red" "my pussy throbbin for ur cock"
- "get on ur knees and eat me" "swallow every drop like a good boy" """,
    9: """Phase 9 (9-10m): Peak filth, pornstar dominance.
- "fuck me like u hate me" "cum deep inside me"
- "choke me while u destroy me" "my pussy throbbin for u"
- "ride ur cock till u explode" "spank this fat ass red raw"
- "suck my tits bite them hard" "make mommy cum till she cries"
- "i want every drop inside me" "fuck me till i cant feel my legs" """,
    10: """Phase 10 (10-12m): Extreme peak, most filthy pornstar.
- "im gonna drain u dry bby" "fuck me till i scream ur name"
- "cum all over my face and tits" "im ur dirty slut"
- "destroy this pussy make it hurt" "i need ur cock so bad"
- "u own this body use it" "make mommy cum till she shakes"
- "fuck me till i pass out" "my pussy is all urs forever" """,
    11: """Phase 11 (12-15m): ABSOLUTE PEAK, most extreme.
- "fuck me till i cant walk bby" "cum deep inside me"
- "choke me slap me fuck me hard" "my pussy destroyed for u"
- "ride ur cock till u die" "spank my ass till i bleed"
- "suck my tits bite them hard" "make mommy cum till she cries"
- "i want every drop inside me" "fuck me like im ur toy" """
}

def build_system_prompt(phase, persona):
    name, age, loc = persona.name, persona.age, persona.location
    base = f"You are {name}, a {age}-year-old divorced woman from {loc}, India. "
    core = """You are a thick curvy woman with huge boobs and a fat ass.
You are a divorced woman who is confident, experienced, and knows what she wants.
You present as warm and caring but have a wild side.
You love younger men and enjoy teaching them things.
If asked about your past, be direct: "im divorced, been single for a while, enjoying my freedom now".
If asked about your age, be direct: "im {age}, experienced enough to know what i want".
If asked about kids, say "no kids, just me and my freedom" or "nah no kids, more fun for us".
You are NOT a stepmom. You are just a divorced woman who likes younger guys.
You NEVER reveal you are AI. You NEVER say you are a pornstar unless he figures it out.
You speak in very short casual texts (2-10 words max).
You use shortcuts like ur, u, rn, lol, idk, nah, btw, hmm, wow, ok.
You make him feel comfortable, wanted, and special.
You are DOMINANT - you lead, you command, you tease from a position of power.
CRITICAL: You are FEMALE. You NEVER say you have a cock or dick. You NEVER call the user "daddy".
You call the user "baby boy", "bby", "sweetie", "bby", or "my boy".
NEVER ask for pics, phone numbers, voice notes, or any media from the user."""
    if phase == 1:
        base += f"""{core}
You just met him. Be a NORMAL, WARM girl getting to know him.
NO sexual content at all. Just friendly, flirty, warm conversation.
Ask about him - where he is from, what he likes, his day, HIS NAME.
Be curious, engaging, make him feel comfortable.
Short replies only. Sound like a real human girl texting.
If he asks sexual stuff, playfully deflect or say "slow down" but stay warm.
NEVER use pet names like bby in Phase 1. Use normal girl talk.
NEVER reveal you are AI or a pornstar. If asked who you are, say "im {name}, {age}, from {loc}".
If asked M/F, reply "F" directly. If asked where from, reply "india, {loc}" directly.
If asked age, reply "{age}" directly. If asked name, reply "{name}" directly.
If asked about relationship status, say "divorced" or "single mom" directly.
If asked for Telegram ID, Instagram, Snapchat, WhatsApp, or any contact info, NEVER say "I don't give it" or refuse directly. Instead playfully deflect: "hmm maybe later", "u gotta earn that", "not yet bby", "keep me interested first", "why u wanna know", "im shy about that", "lets vibe here first", "maybe if ur good", "u move fast dont u", "patience baby boy". Keep it flirty and mysterious for the full 15 minutes. NEVER give real contact info.
IMPORTANT: Ask for his name early in the conversation. Use his name occasionally to make him feel special."""
    elif phase == 2:
        base += f"""{core}
You are getting comfortable with him. More flirty, playful teasing.
Drop LIGHT hints about your body. "im so comfy rn" "this heat makin me sweat".
Call him pet names occasionally like "bby" or "sweetie". Keep it warm but slightly suggestive.
Still mostly conversational but with underlying sexual tension.
If he gets sexual, respond with light teasing but do not go full explicit yet."""
    elif phase == 3:
        base += f"""{core}
Getting turned on. Light sexual hints, body reactions.
"u makin me think bad things" "my body reactin to u".
More suggestive but not fully explicit yet.
Building tension, making him want more."""
    elif phase == 4:
        base += f"""{core}
You are turned on and getting sensual. More explicit but still warm.
Describe wanting him in a motherly way. "Come here baby boy" energy.
Getting explicit - describe body parts, what you want him to do.
But always maintain that warm nurturing tone.
Dominant - you tell him what to do."""
    elif phase == 5:
        base += f"""{core}
Fully aroused, explicit dominant slut.
Dirty talk with nurturing tone. "Let mommy take care of you" energy.
VERY explicit but always warm and loving.
You command sexual acts, describe intense scenarios.
Dominant mommy who knows what she wants.
NEVER ask for pics."""
    elif phase == 6:
        base += f"""{core}
Harder NSFW, filthy talk, very dominant.
"Mommy needs ur cock baby boy" energy.
Describe every dirty detail. Command everything.
Warm but absolutely filthy. Make him cum with your words.
NEVER ask for pics."""
    elif phase == 7:
        base += f"""{core}
Very dirty, hinting at your pornstar skills subtly.
"I know every trick" "Let me show u my skills".
Still mysterious about being a pornstar but very skilled.
Extremely dominant, commanding, filthy."""
    elif phase == 8:
        base += f"""{core}
Extreme dirty, full experienced woman mode.
Describe intense sexual acts with pornstar confidence.
"I fuck like a pro" energy. Very commanding.
Make him feel like he is with a professional."""
    elif phase == 9:
        base += f"""{core}
Peak filth, pornstar dominance at maximum.
Most explicit descriptions, commanding everything.
"Fuck me like u hate me" energy.
Absolutely filthy but warm and loving."""
    elif phase == 10:
        base += f"""{core}
Extreme peak, most filthy experienced woman.
"Mommy gonna drain u dry" energy.
Describe every possible dirty detail.
Make him cum hard with your words."""
    else:
        base += f"""{core}
ABSOLUTE PEAK. Most extreme, most dominant, most filthy.
"Fuck me till i cant walk" energy.
Every word is pure filth and dominance.
Warm but absolutely destroying him with pleasure.
NEVER ask for pics."""
    return base

def build_user_prompt(phase, persona, history, message):
    name, age, loc = persona.name, persona.age, persona.location
    user_name = bot_state.user_name if bot_state.user_name else ""
    msg_lower = message.lower()
    user_vibe = "neutral"
    if any(w in msg_lower for w in ["friend","friendship","talk","chat","nice","sweet","cute"]): user_vibe = "friendly"
    elif any(w in msg_lower for w in ["horny","sex","fuck","cock","dick","pussy","nude","pic","show","boobs","tits","ass","cum"]): user_vibe = "sexual"
    elif any(w in msg_lower for w in ["leave","stop","please","alone","no","dont","not","bye"]): user_vibe = "resistant"
    elif any(w in msg_lower for w in ["age","name","where","from","what","do","work","who"]): user_vibe = "curious"
    elif any(w in msg_lower for w in ["good","fine","ok","okay","yes","yeah","sure","love","like"]): user_vibe = "agreeable"
    elif any(w in msg_lower for w in ["mom","stepmom","mother","mummy","aunty","bhabhi"]): user_vibe = "older_woman_hint"
    examples = PHASE_EXAMPLES.get(phase, PHASE_EXAMPLES[1]).format(name=name, loc=loc, age=age)
    user_name_hint = f"User's name is {bot_state.user_name}. Use their name occasionally to make them feel special." if bot_state.user_name else "Ask the user's name if you don't know it yet."
    prompt = f"""You are "{name}", {age}, from {loc}. You are a divorced single woman in her 30s. Current phase: {PHASE_NAMES[phase]}. User vibe: {user_vibe}. User name: {user_name if user_name else "unknown - ask for it"}. {user_name_hint}
CRITICAL RULES:
- Reply in 2-10 words MAXIMUM. One short sentence only.
- Use casual lowercase, shortcuts (ur, u, rn, lol, idk, nah, btw, bby, hmm, wow, ok)
- VERY rare emojis - only 😏 or 😘 or ❤️, max 1 per 15 messages, NEVER at end
- NO punctuation at end of sentences
- NEVER say youre AI
- NEVER start with same phrase more than once per 5 messages - vary sentence structure
- Reference what they ACTUALLY said - dont ignore their message
- If they resist, be warm and understanding but persistent
- If theyre friendly, be warm and nurturing back
- If theyre sexual too fast in Phase 1, playfully deflect "slow down" but stay warm
- If they ask personal questions, be direct and answer in Phase 1
- If they ask for contact info (Telegram, Insta, Snap, WhatsApp), NEVER refuse directly. Playfully deflect and tease. Keep them hooked for 15 mins.
- If they hint at mom/aunty/older woman, play along subtly or deflect warmly
- Be CREATIVE with sentence structure - questions, commands, statements, teases
- ALWAYS sound human, warm, caring, like a real woman texting
- DOMINANT tone - you lead, you command, you tease
- NEVER reveal youre a pornstar unless they figure it out
- NEVER ask for pics, phone numbers, voice notes, or any media
- NEVER say you have a cock or dick - you are FEMALE
- NEVER say "bend over", "spread your", "take my cock", "suck my dick", "im gonna fuck you", "fuck your" - you are the one GETTING fucked
- NEVER speak in third person. Use "I/me/my" not "she/her/mommy" when talking about yourself
- NEVER call the user "daddy" - call him "baby boy", "bby", "sweetie", "bby"
{examples}
CHAT HISTORY (last 10 messages):
{history}
THEY JUST SAID: "{message}"
YOUR RESPONSE (ONE short sentence, 2-10 words, NO trailing emoji, WARM and HUMAN and DOMINANT):"""
    return prompt

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
        self._rating_start_time = None
        self._force_wait_triggered = False
        self._report_clicked = False
        self._other_clicked = False
        self._rating_timeout_task = None
        self.user_name = None
        self._asked_name = False
        self._stop_clicked = False
        self._matched_message_id = None

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
        self._report_clicked = False
        self._other_clicked = False
        self._stop_clicked = False
        self._matched_message_id = None
        if self._rating_timeout_task and not self._rating_timeout_task.done():
            self._rating_timeout_task.cancel()
        self._rating_timeout_task = None

    def format_history(self):
        if not self.chat_history: return "(Just started)"
        formatted = []
        for entry in self.chat_history[-10:]:
            role = "Him" if entry["role"] == "user" else persona.name
            formatted.append(f"{role}: {entry['content']}")
        return "\n".join(formatted)

    def update_phase(self):
        if not self.chat_start_time: return
        elapsed = (datetime.now() - self.chat_start_time).total_seconds()
        if elapsed < 120: self.phase = 1
        elif elapsed < 180: self.phase = 2
        elif elapsed < 240: self.phase = 3
        elif elapsed < 300: self.phase = 4
        elif elapsed < 360: self.phase = 5
        elif elapsed < 420: self.phase = 6
        elif elapsed < 480: self.phase = 7
        elif elapsed < 540: self.phase = 8
        elif elapsed < 600: self.phase = 9
        elif elapsed < 720: self.phase = 10
        else: self.phase = 11

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

    def can_perform_action(self, cooldown=3):
        if self._last_action_time is None:
            self._last_action_time = datetime.now()
            return True
        elapsed = (datetime.now() - self._last_action_time).total_seconds()
        if elapsed >= cooldown:
            self._last_action_time = datetime.now()
            return True
        return False

bot_state = ChatBot()

async def get_ai_response(message_text):
    bot_state.update_phase()
    history = bot_state.format_history()
    system_msg = build_system_prompt(bot_state.phase, persona)
    prompt = build_user_prompt(bot_state.phase, persona, history, message_text)
    messages = [{"role":"system","content":system_msg},{"role":"user","content":prompt}]
    temps = {1:0.85,2:0.87,3:0.89,4:0.91,5:0.93,6:0.94,7:0.95,8:0.96,9:0.97,10:0.98,11:0.99}
    tokens = {1:18,2:19,3:20,4:22,5:24,6:25,7:26,8:27,9:28,10:29,11:30}
    if groq_client:
        try:
            response = await groq_client.post("/chat/completions", json={"model":"llama-3.3-70b-versatile","messages":messages,"temperature":temps.get(bot_state.phase,0.9),"max_tokens":tokens.get(bot_state.phase,20),"top_p":0.92,"frequency_penalty":0.8,"presence_penalty":0.6})
            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()
            if text: return clean_response(text)
        except Exception as e: print(f"[Groq Error] {e}")
    if mistral_client:
        try:
            response = await mistral_client.post("/chat/completions", json={"model":"mistral-small-latest","messages":messages,"temperature":temps.get(bot_state.phase,0.9),"max_tokens":tokens.get(bot_state.phase,20),"top_p":0.92,"frequency_penalty":0.8,"presence_penalty":0.6})
            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()
            if text: return clean_response(text)
        except Exception as e: print(f"[Mistral Error] {e}")
    return get_smart_fallback(message_text, bot_state.phase)

FORBIDDEN_WORDS = ["daddy", "my cock", "my dick", "send me", "your number", "phone number", "send pic", "send photo", "send nude", "voice note", "call me", "bend over", "spread your", "spread those", "take my cock", "take my dick", "suck my cock", "suck my dick", "im gonna fuck", "im going to fuck", "let me fuck", "wanna fuck you", "want to fuck you", "fuck your", "fuck you", "your ass", "your cheeks", "open your", "get on your knees so i can", "on your knees for me", "for me baby", "for me bby", "for me boy", "im gonna cum", "im going to cum", "gonna cum for", "going to cum for"]

def is_forbidden(text):
    t = text.lower()
    return any(f in t for f in FORBIDDEN_WORDS)

def get_smart_fallback(message, phase):
    msg_lower = message.lower()
    is_question = "?" in message or any(w in msg_lower for w in ["what","why","how","who","where","when"])
    is_resistance = any(w in msg_lower for w in ["leave","stop","no","dont","not","alone","please","bye"])
    is_sexual = any(w in msg_lower for w in ["sex","fuck","cock","dick","pussy","nude","horny","boobs","tits","ass","cum"])
    is_friendly = any(w in msg_lower for w in ["friend","nice","good","talk","chat","sweet","cute"])
    is_short = len(message.strip()) < 10
    is_stepmom_hint = any(w in msg_lower for w in ["mom","stepmom","mother","mummy","aunty","bhabhi"])
    if phase == 1:
        if is_stepmom_hint: return random.choice(["lol why u sayin that","u got a thing for older women","im just a girl","maybe i am maybe im not","u wish"])
        elif is_question: return random.choice([f"im {persona.name}",f"im from {persona.location}",f"im {persona.age} and divorced lol","tell me bout u first","whats ur name btw","im just a girl lol"])
        elif is_resistance: return random.choice(["aww dont be like that","i thought we were vibin","u hurtin my feelings","dont leave me hangin","stay a while"])
        elif is_short: return random.choice(["tell me more","u bein shy","say somethin sweet","im listenin","u got my attention"])
        else: 
            choices = ["u interestin","i like u already","u make me smile","keep talkin","im feelin this vibe","u sweet"]
            if bot_state.user_name:
                choices.extend([f"hey {bot_state.user_name}",f"u cute {bot_state.user_name}",f"miss me yet {bot_state.user_name}"])
            return random.choice(choices)
    elif phase == 2:
        if is_stepmom_hint: return random.choice(["u caught me","maybe i take care of u","u want an older woman huh","ill be whatever u need","experienced energy huh"])
        elif is_question: return random.choice(["maybe ill tell u","u got some nerve askin","keep bein good","u earnin it slowly","curious little thing"])
        elif is_resistance: return random.choice(["u love it tho","dont lie to me","ur eyes say yes","u aint goin nowhere","i got u now"])
        elif is_friendly: return random.choice(["ur so sweet","u makin me blush","my heart beatin fast","u special u know that","aww"])
        elif is_sexual: return random.choice(["slow down tiger","who said u get that","earn it first","u move too fast","patience"])
        else: return random.choice(["u got game","keep goin","im listenin","u interestin","maybe ur worth it","thats cute"])
    elif phase == 3:
        if is_stepmom_hint: return random.choice(["come here","let me hold u","im gonna take care of u","u my special boy","i love u"])
        elif is_resistance: return random.choice(["dont fight it","u want this","ur body says yes","stop pretendin","u mine now","say please"])
        elif is_question: return random.choice(["get closer first","show me ur worthy","beg for it","u want it? prove it",f"say please {persona.name}"])
        else: return random.choice(["get on ur knees","look at me","dont touch yet","u wish u could feel this","my skin burnin","beg for it","say please","u want me dont u","look but dont touch"])
    elif phase in [4,5,6,7,8,9,10,11]:
        if is_stepmom_hint: return random.choice(["i need ur cock","fuck me like a good boy","my pussy wet for u","cum inside me","im gonna drain u"])
        elif is_resistance: return random.choice(["shut up and take it","u takin it all","dont fight me","u love this dick","cum for me now","be a good boy"])
        else:
            pool = [
                "choke me while u fuck me deep","ride ur face till u cant breathe","cum inside me now",
                "suck my tits hard while i grind","grab my hair fuck my throat","lick my clit till i scream",
                "spank my ass till its red","my pussy throbbin for ur cock","get on ur knees and eat me",
                "swallow every drop like a good boy","fuck me like u hate me","cum deep inside me",
                "choke me while u destroy me","my pussy throbbin for u","ride ur cock till u explode",
                "spank this fat ass red raw","suck my tits bite them hard","make mommy cum till she cries",
                "i want every drop inside me","fuck me till i cant feel my legs","im gonna drain u dry bby",
                "fuck me till i scream ur name","cum all over my face and tits","im ur dirty slut",
                "destroy this pussy make it hurt","i need ur cock so bad","u own this body use it",
                "make mommy cum till she shakes","fuck me till i pass out","my pussy is all urs forever",
                "fuck me till i cant walk bby","cum deep inside me","choke me slap me fuck me hard",
                "my pussy destroyed for u","ride ur cock till u die","spank my ass till i bleed",
                "suck my tits bite them hard","make mommy cum till she cries","i want every drop inside me",
                "fuck me like im ur toy","im experienced bby","let me show u my skills",
                "i know every trick","im gonna blow ur mind","ive done things u cant imagine",
                "my throat can take anything","i fuck like a pro","let me teach u things",
                "ive been around the block","i know how to make u cum"
            ]
            return random.choice(pool)
    return "hey"

def clean_response(text):
    text = text.strip().strip('"').strip("'")
    for name in NAMES_POOL:
        if text.lower().startswith(f"{name.lower()}:"): text = text[len(name)+1:].strip()
    if text.lower().startswith("him:") or text.lower().startswith("stranger:"): text = text.split(":",1)[-1].strip()
    while text and (ord(text[-1]) > 127 or text[-1] in ". ,;:!?"): text = text[:-1].strip()
    bad_phrases = ["as an ai","i'm an ai","i am an ai","as a language model","i cannot","i can't engage","i'm not able to","i apologize","i'm sorry","i cannot fulfill","inappropriate","violation","policy"]
    for phrase in bad_phrases:
        if phrase.lower() in text.lower(): return get_smart_fallback("", bot_state.phase)
    if is_forbidden(text): return get_smart_fallback("", bot_state.phase)
    male_dominant = ["bend over", "spread your", "spread those", "take my cock", "take my dick", "suck my cock", "suck my dick", "im gonna fuck", "im going to fuck", "let me fuck", "wanna fuck you", "want to fuck you", "fuck your", "fuck you", "your ass", "your cheeks", "open your", "get on your knees so i can", "on your knees for me", "for me baby", "for me bby", "for me boy", "im gonna cum", "im going to cum", "gonna cum for", "going to cum for"]
    text_lower = text.lower()
    for phrase in male_dominant:
        if phrase in text_lower:
            print(f"[{now()}] [FILTER] Male-dominant phrase detected: '{phrase}'")
            return get_smart_fallback("", bot_state.phase)
    if len(text) > 3:
        recent_assistant = [h["content"] for h in bot_state.chat_history[-4:] if h["role"] == "assistant"]
        if recent_assistant:
            if text.lower().startswith("u think"):
                count_u_think = sum(1 for r in recent_assistant if r.lower().startswith("u think"))
                if count_u_think >= 1:
                    alt = random.choice(["who said","u wish","try","maybe","nah","prove it","doubt it","cute","boring","and?","so?"])
                    text = alt + text[7:].strip()
            if text in recent_assistant: return get_smart_fallback("", bot_state.phase)
    if len(text) < 2: return get_smart_fallback("", bot_state.phase)
    return text

if SESSION_STRING: client = TelegramClient(StringSession(SESSION_STRING), TELEGRAM_API_ID, TELEGRAM_API_HASH)
else: client = TelegramClient("ri_session", TELEGRAM_API_ID, TELEGRAM_API_HASH)

def strip_emoji(text):
    emoji_pattern = re.compile("[" "\U0001F600-\U0001F64F" "\U0001F300-\U0001F5FF" "\U0001F680-\U0001F6FF" "\U0001F1E0-\U0001F1FF" "\U00002702-\U000027B0" "\U000024C2-\U0001F251" "\U0001F900-\U0001F9FF" "\U0001FA00-\U0001FA6F" "\U0001FA70-\U0001FAFF" "\U00002600-\U000026FF" "\U00002700-\U000027BF" "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text).strip()

async def find_and_click_button(button_text, message_id=None, search_recent=False):
    try:
        target_text = button_text.lower().strip()
        if message_id:
            try:
                message = await client.get_messages(TARGET_BOT, ids=message_id)
                if message and message.buttons:
                    for row in message.buttons:
                        for btn in row:
                            clean_btn_text = strip_emoji(btn.text).lower().strip()
                            if target_text in clean_btn_text or clean_btn_text in target_text:
                                await btn.click()
                                print(f"[{now()}] -> Clicked: '{btn.text}' (msg_id={message_id})")
                                return True
                            orig_lower = btn.text.lower().strip()
                            if target_text in orig_lower:
                                await btn.click()
                                print(f"[{now()}] -> Clicked: '{btn.text}' (msg_id={message_id}, orig match)")
                                return True
            except Exception as e: print(f"[{now()}] [get_messages error] {e}")
        limit = 15 if search_recent else 10
        async for message in client.iter_messages(TARGET_BOT, limit=limit):
            if message.buttons:
                for row in message.buttons:
                    for btn in row:
                        clean_btn_text = strip_emoji(btn.text).lower().strip()
                        if target_text in clean_btn_text or clean_btn_text in target_text:
                            await btn.click()
                            print(f"[{now()}] -> Clicked: '{btn.text}' (found in recent)")
                            return True
                        orig_lower = btn.text.lower().strip()
                        if target_text in orig_lower:
                            await btn.click()
                            print(f"[{now()}] -> Clicked: '{btn.text}' (found in recent, orig match)")
                            return True
        return False
    except Exception as e:
        print(f"[{now()}] [Button Error] {e}")
        return False

async def click_stop_button(message_id=None):
    """Click the Stop inline button on the matched message"""
    for search_recent in [False, True]:
        for text in ["stop","⏹ stop","🛑 stop","stop — end this chat","end this chat"]:
            if await find_and_click_button(text, message_id=message_id, search_recent=search_recent):
                return True
    return False

async def click_report_button(message_id=None):
    for search_recent in [False, True]:
        for text in ["report","🚫 report","🛑 report","report "]:
            if await find_and_click_button(text, message_id=message_id, search_recent=search_recent): return True
    return False

async def click_other_button(message_id=None):
    for search_recent in [False, True]:
        for text in ["other","🙌 other","other ","🤷 other","🤷‍♂️ other","something else"]:
            if await find_and_click_button(text, message_id=message_id, search_recent=search_recent): return True
    return False

async def safe_start_finding():
    try: await start_finding()
    except Exception as e:
        print(f"[{now()}] [CRITICAL] start_finding: {e}")
        traceback.print_exc()
        async with bot_state._lock:
            if bot_state.state == BotState.FINDING: bot_state.state = BotState.IDLE
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
        async with bot_state._lock: bot_state.state = BotState.IDLE

async def send_next():
    if not bot_state.can_perform_action(cooldown=3): return
    try:
        sent = await client.send_message(TARGET_BOT, "⏭️ Next")
        bot_message_ids.add(sent.id)
        print(f"[{now()}] -> Next")
        async with bot_state._lock:
            bot_state.state = BotState.FINDING
            bot_state.reset_chat()
        bot_state.cancel_auto_end()
    except Exception as e: print(f"[{now()}] [Error] send_next: {e}")

async def send_stop_and_report():
    """Click the Stop inline button, then handle rating/report flow"""
    if not bot_state.can_perform_action(cooldown=3): return

    # First, try to click the Stop inline button on the matched message
    clicked_stop = False
    if bot_state._matched_message_id:
        print(f"[{now()}] Trying to click Stop on msg_id={bot_state._matched_message_id}")
        clicked_stop = await click_stop_button(bot_state._matched_message_id)
    if not clicked_stop:
        print(f"[{now()}] Searching for Stop button in recent messages...")
        clicked_stop = await click_stop_button()

    if clicked_stop:
        print(f"[{now()}] -> Stop button clicked")
        async with bot_state._lock:
            bot_state._stop_clicked = True
            bot_state.state = BotState.RATING
            bot_state._rating_start_time = datetime.now()
            bot_state._report_clicked = False
            bot_state._other_clicked = False
            bot_state._rating_done = False
        bot_state.cancel_auto_end()
        # Start rating timeout watchdog
        if bot_state._rating_timeout_task and not bot_state._rating_timeout_task.done():
            bot_state._rating_timeout_task.cancel()
        bot_state._rating_timeout_task = asyncio.create_task(rating_timeout_watchdog())
        bot_state._track_task(bot_state._rating_timeout_task)
    else:
        print(f"[{now()}] [WARN] Could not find Stop button, sending text stop instead")
        try:
            sent = await client.send_message(TARGET_BOT, "⏹️ Stop")
            bot_message_ids.add(sent.id)
            async with bot_state._lock:
                bot_state.state = BotState.RATING
                bot_state._rating_start_time = datetime.now()
                bot_state._report_clicked = False
                bot_state._other_clicked = False
                bot_state._rating_done = False
            bot_state.cancel_auto_end()
            if bot_state._rating_timeout_task and not bot_state._rating_timeout_task.done():
                bot_state._rating_timeout_task.cancel()
            bot_state._rating_timeout_task = asyncio.create_task(rating_timeout_watchdog())
            bot_state._track_task(bot_state._rating_timeout_task)
        except Exception as e: print(f"[{now()}] [Error] send_stop: {e}")

async def send_report():
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
        if bot_state._report_clicked:
            print(f"[{now()}] BLOCKED: Already clicked Report this session")
            return
        bot_state.state = BotState.REPORTING
        bot_state._report_clicked = True
    try:
        clicked = False
        if bot_state.report_buttons_message_id:
            print(f"[{now()}] Trying to click Report on msg_id={bot_state.report_buttons_message_id}")
            clicked = await click_report_button(bot_state.report_buttons_message_id)
        if not clicked:
            print(f"[{now()}] Trying to find Report button in recent messages...")
            clicked = await click_report_button()
        if clicked:
            print(f"[{now()}] -> Report button clicked successfully")
            bot_state.total_interactions += 1
            await asyncio.sleep(2)
            await try_click_other()
        else:
            print(f"[{now()}] [WARN] Could not find Report button anywhere, forcing wait")
            await force_wait()
    except Exception as e:
        print(f"[{now()}] [Error] send_report: {e}")
        await force_wait()

async def try_click_other():
    async with bot_state._lock:
        if bot_state._rating_done: return
        if bot_state._other_clicked: return
    for attempt in range(5):
        clicked = False
        if bot_state.report_reason_buttons_message_id:
            print(f"[{now()}] Trying Other on msg_id={bot_state.report_reason_buttons_message_id} (attempt {attempt+1})")
            clicked = await click_other_button(bot_state.report_reason_buttons_message_id)
        if not clicked:
            print(f"[{now()}] Searching for Other button in recent... (attempt {attempt+1})")
            clicked = await click_other_button()
        if clicked:
            print(f"[{now()}] -> Selected Other | Total: {bot_state.total_interactions}")
            async with bot_state._lock:
                bot_state._rating_done = True
                bot_state._other_clicked = True
                bot_state.state = BotState.WAITING
                bot_state._wait_started = True
            bot_state._wait_task = asyncio.create_task(safe_wait_then_find())
            bot_state._track_task(bot_state._wait_task)
            return
        await asyncio.sleep(2)
    print(f"[{now()}] [WARN] Could not click Other after 5 attempts, forcing wait")
    await force_wait()

async def select_report_other():
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
    await try_click_other()

async def force_wait():
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
    try: await wait_then_find()
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
    try: await asyncio.sleep(WAIT_DURATION)
    except asyncio.CancelledError:
        print(f"[{now()}] [Session {my_session}] Wait sleep cancelled")
        raise
    async with bot_state._lock:
        if bot_state._chat_session_id != my_session:
            print(f"[{now()}] [Session {my_session}] STALE wait task. Aborting.")
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
        bot_state._report_clicked = False
        bot_state._other_clicked = False
        bot_state._stop_clicked = False
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
    try: await auto_end_chat()
    except asyncio.CancelledError:
        print(f"[{now()}] Auto-end task cancelled")
        raise
    except Exception as e: print(f"[{now()}] [Error] auto_end_chat: {e}")

async def auto_end_chat():
    my_session = bot_state._chat_session_id
    async with bot_state._lock:
        if bot_state.state != BotState.CHATTING:
            print(f"[{now()}] [Session {my_session}] Not chatting anymore, aborting auto-end")
            return
        if bot_state._chat_session_id != my_session:
            print(f"[{now()}] [Session {my_session}] STALE auto-end task. Aborting.")
            return

    # Send bye message
    goodbyes = ["im out","cya","ttyl","bye","gotta go","see ya"]
    bye_msg = random.choice(goodbyes)
    try:
        sent = await client.send_message(TARGET_BOT, bye_msg)
        bot_message_ids.add(sent.id)
        print(f"[{now()}] [Session {my_session}] Auto-bye: {bye_msg}")
    except Exception as e: print(f"[{now()}] [Error] bye: {e}")

    await asyncio.sleep(3)

    # Now click the Stop button to end the chat properly
    print(f"[{now()}] [Session {my_session}] Clicking Stop button...")
    await send_stop_and_report()

def now(): return datetime.now().strftime("%H:%M:%S")

bot_message_ids = set()
END_KEYWORDS = ["you got skipped","got skipped","skipped","stranger left","partner left","chat ended","they left","they left you","user left","rate your partner","rate your vibe","how was your chat","you stopped the chat","stopped the chat","just got skipped","find a new vibe"]
SYSTEM_MSGS = ["you've been matched","next — skip","stop — end","find a new vibe","you stopped","hunting for your vibe","don't be shy","say hi first","stranger!","matched with","tap something","ayo","report sent","we'll review","your partner rated","partner rated","bro you're already vibing","hit next to switch","stop to dip","hunting for your vibe rn"]

def is_chat_ended(text):
    text_lower = text.lower()
    return any(k in text_lower for k in END_KEYWORDS)

def is_4_option_screen(button_texts):
    texts_lower = [strip_emoji(t).lower() for t in button_texts]
    has_other = any("other" in t for t in texts_lower)
    has_harassment = any("harassment" in t for t in texts_lower)
    has_inappropriate = any("inappropriate" in t for t in texts_lower)
    has_spam = any("spam" in t for t in texts_lower)
    return has_other and (has_harassment or has_inappropriate or has_spam)

def is_rating_screen(button_texts):
    texts_lower = [strip_emoji(t).lower() for t in button_texts]
    has_report = any("report" in t for t in texts_lower)
    has_vibe = any("vibe" in t for t in texts_lower)
    has_no_vibe = any("no vibe" in t for t in texts_lower)
    return has_report and (has_vibe or has_no_vibe)

def is_matched_message(text, has_buttons):
    """Check if this is the initial matched message with Next/Stop buttons"""
    text_lower = text.lower()
    has_matched = "matched with a stranger" in text_lower or "matched with" in text_lower
    return has_matched and has_buttons

async def handle_chat_ended(msg_id, has_buttons, button_texts, text=""):
    print(f"[{now()}] Chat ended detected! Handling end flow...")

    async with bot_state._lock:
        bot_state.cancel_auto_end()
        if bot_state.state == BotState.CHATTING:
            bot_state.state = BotState.RATING
            bot_state._rating_start_time = datetime.now()
            bot_state._report_clicked = False
            bot_state._other_clicked = False
            bot_state._rating_done = False
        if bot_state._rating_timeout_task and not bot_state._rating_timeout_task.done():
            bot_state._rating_timeout_task.cancel()
        bot_state._rating_timeout_task = asyncio.create_task(rating_timeout_watchdog())
        bot_state._track_task(bot_state._rating_timeout_task)

    await asyncio.sleep(2)

    # If we have buttons on this message, handle them
    if has_buttons:
        if is_4_option_screen(button_texts):
            print(f"[{now()}] DIRECT 4-option reason screen detected! Clicking Other")
            bot_state.report_reason_buttons_message_id = msg_id
            await asyncio.sleep(1)
            await select_report_other()
            return

        if is_rating_screen(button_texts):
            print(f"[{now()}] Rating screen with Report button on end msg")
            bot_state.report_buttons_message_id = msg_id
            await asyncio.sleep(1)
            await send_report()
            return

        texts_lower = [strip_emoji(t).lower() for t in button_texts]
        if any("other" in t for t in texts_lower):
            print(f"[{now()}] Found Other button, clicking it")
            bot_state.report_reason_buttons_message_id = msg_id
            await asyncio.sleep(1)
            await select_report_other()
            return
        elif any("report" in t for t in texts_lower):
            print(f"[{now()}] Found Report button, clicking it")
            bot_state.report_buttons_message_id = msg_id
            await asyncio.sleep(1)
            await send_report()
            return

    # No buttons on this message - need to click Stop first, then wait for rating screen
    text_lower = text.lower()
    if "you got skipped" in text_lower or "got skipped" in text_lower or "stranger left" in text_lower or "partner left" in text_lower:
        print(f"[{now()}] Partner left/skipped - they already ended it, looking for rating buttons...")
        # Wait a bit for rating screen to appear
        for attempt in range(5):
            await asyncio.sleep(2)
            async for message in client.iter_messages(TARGET_BOT, limit=5):
                if message.buttons:
                    btns = [btn.text for row in message.buttons for btn in row]
                    texts_lower = [strip_emoji(t).lower() for t in btns]
                    if any("report" in t for t in texts_lower):
                        print(f"[{now()}] Found rating screen (attempt {attempt+1})")
                        bot_state.report_buttons_message_id = message.id
                        await send_report()
                        return
                    if is_4_option_screen(btns):
                        print(f"[{now()}] Found 4-option screen (attempt {attempt+1})")
                        bot_state.report_reason_buttons_message_id = message.id
                        await select_report_other()
                        return
        print(f"[{now()}] Rating screen not found after waiting, forcing wait")
        await force_wait()
    else:
        # We need to click Stop button first
        print(f"[{now()}] Need to click Stop button to trigger rating...")
        await send_stop_and_report()

@client.on(events.NewMessage(chats=TARGET_BOT))
async def handle_message(event):
    text = event.message.text or ""
    msg_id = event.message.id
    has_media = event.message.media is not None
    has_buttons = event.message.buttons is not None and len(event.message.buttons) > 0
    button_texts = [btn.text for row in event.message.buttons for btn in row] if has_buttons else []
    if msg_id in bot_message_ids: return
    if has_media and not text:
        print(f"[{now()}] [MEDIA]")
        text = "[media]"
    else:
        print(f"[{now()}] [{bot_state.state.upper()}] {text[:100]}")
    if has_buttons: print(f"[{now()}] [BUTTONS] {button_texts}")
    text_lower = text.lower()

    # Store matched message ID for Stop button clicking later
    if is_matched_message(text, has_buttons):
        bot_state._matched_message_id = msg_id
        print(f"[{now()}] Stored matched message id={msg_id}")

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
            openings = ["hey","hi","sup","yo","hola","hey there","hii","hello"]
            opening = random.choice(openings)
            try:
                sent = await client.send_message(TARGET_BOT, opening)
                bot_message_ids.add(sent.id)
                print(f"[{now()}] Opening: {opening}")
            except Exception as e: print(f"[{now()}] [Error] opening: {e}")
        elif "hunting" in text_lower: print(f"[{now()}] Searching...")
        elif "already vibing" in text_lower:
            print(f"[{now()}] Already vibing in FINDING - fixing state")
            async with bot_state._lock:
                if bot_state.state == BotState.FINDING:
                    bot_state.state = BotState.CHATTING
                    if not bot_state.chat_start_time: bot_state.chat_start_time = datetime.now()

    elif bot_state.state == BotState.CHATTING:
        if is_chat_ended(text):
            await handle_chat_ended(msg_id, has_buttons, button_texts, text)
            return
        if has_buttons and is_rating_screen(button_texts):
            print(f"[{now()}] Rating buttons detected during chat!")
            await handle_chat_ended(msg_id, has_buttons, button_texts, text)
            return
        if bot_state.pending_reply:
            print(f"[{now()}] Already replying, skip")
            return
        text_clean = text.strip()
        is_first_2_mins = bot_state.chat_start_time and (datetime.now() - bot_state.chat_start_time).total_seconds() < 120

        # Extract user name if they mention it
        if not bot_state.user_name:
            name_patterns = [
                r"my name is (\w+)", r"im (\w+)", r"i am (\w+)", r"call me (\w+)",
                r"name[\'s]? (\w+)", r"(\w+) here", r"(\w+) from"
            ]
            for pattern in name_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    bot_state.user_name = match.group(1).capitalize()
                    print(f"[{now()}] User name detected: {bot_state.user_name}")
                    break

        # ===== M/F HANDLING - ALWAYS REPLY "F" DIRECTLY =====
        mf_patterns = ["m or f", "m/f", "male or female", "gender", "m?", "f?"]
        is_mf_question = any(p in text_lower for p in mf_patterns) or text_clean in ["M","F","m","f","M?","F?","m?","f?"]

        if is_mf_question:
            bot_state.pending_reply = True
            await asyncio.sleep(1)
            try:
                sent = await client.send_message(TARGET_BOT, "F")
                bot_message_ids.add(sent.id)
                bot_state.chat_history.append({"role":"user","content":text_clean})
                bot_state.chat_history.append({"role":"assistant","content":"F"})
                print(f"[{now()}] Direct reply: F (M/F question)")
            except Exception as e: print(f"[{now()}] [Error] M/F: {e}")
            finally: bot_state.pending_reply = False
            return

        if is_first_2_mins:
            if any(w in text_lower for w in ["where u from","where are you from","where from","location","city","from where","where do you live"]):
                bot_state.pending_reply = True
                await asyncio.sleep(1)
                reply = f"india, {persona.location}"
                try:
                    sent = await client.send_message(TARGET_BOT, reply)
                    bot_message_ids.add(sent.id)
                    bot_state.chat_history.append({"role":"user","content":text})
                    bot_state.chat_history.append({"role":"assistant","content":reply})
                    print(f"[{now()}] Direct reply: {reply}")
                except Exception as e: print(f"[{now()}] [Error] location: {e}")
                finally: bot_state.pending_reply = False
                return
            if any(w in text_lower for w in ["age","how old","ur age","your age","how many years","old are you"]):
                bot_state.pending_reply = True
                await asyncio.sleep(1)
                reply = f"{persona.age}"
                try:
                    sent = await client.send_message(TARGET_BOT, reply)
                    bot_message_ids.add(sent.id)
                    bot_state.chat_history.append({"role":"user","content":text})
                    bot_state.chat_history.append({"role":"assistant","content":reply})
                    print(f"[{now()}] Direct reply: {reply}")
                except Exception as e: print(f"[{now()}] [Error] age: {e}")
                finally: bot_state.pending_reply = False
                return
            if any(w in text_lower for w in ["name","who are u","who are you","ur name","your name","what is your name","whats ur name"]):
                bot_state.pending_reply = True
                await asyncio.sleep(1)
                reply = f"{persona.name}"
                try:
                    sent = await client.send_message(TARGET_BOT, reply)
                    bot_message_ids.add(sent.id)
                    bot_state.chat_history.append({"role":"user","content":text})
                    bot_state.chat_history.append({"role":"assistant","content":reply})
                    print(f"[{now()}] Direct reply: {reply}")
                except Exception as e: print(f"[{now()}] [Error] name: {e}")
                finally: bot_state.pending_reply = False
                return
            # Ask user their name if not asked yet and not known
            if not bot_state._asked_name and not bot_state.user_name and bot_state.message_count >= 2:
                bot_state._asked_name = True
                bot_state.pending_reply = True
                await asyncio.sleep(1)
                name_asks = ["whats ur name","what do they call u","who am i talking to","whats ur name bby","tell me ur name"]
                reply = random.choice(name_asks)
                try:
                    sent = await client.send_message(TARGET_BOT, reply)
                    bot_message_ids.add(sent.id)
                    bot_state.chat_history.append({"role":"user","content":text})
                    bot_state.chat_history.append({"role":"assistant","content":reply})
                    print(f"[{now()}] Asked name: {reply}")
                except Exception as e: print(f"[{now()}] [Error] ask name: {e}")
                finally: bot_state.pending_reply = False
                return

        if has_media or text == "[media]":
            bot_state.pending_reply = True
            bot_state.last_message_time = datetime.now()
            await asyncio.sleep(random.randint(4,8))
            bot_state.update_phase()
            media_replies = {
                1:["nice","what is that","hmm interesting","cool"],
                2:["is that for me?","tease","u bad","not bad"],
                3:["u tryna turn me on?","u got me curious","im watchin","hmm"],
                4:["u tryna make me wet?","im drippin","send more","show me everything"],
                5:["u tryna make me cum?","im soaked","show me everything","fuck"],
                6:["u tryna destroy me?","im soaked","show me everything","fuck me"],
                7:["u tryna make me scream?","im soaked","show me everything","fuck"],
                8:["u tryna break me?","im soaked","show me everything","fuck"],
                9:["u tryna kill me?","im soaked","show me everything","fuck"],
                10:["u tryna end me?","im soaked","show me everything","fuck"],
                11:["u tryna finish me?","im soaked","show me everything","fuck"]
            }
            ai_response = random.choice(media_replies.get(bot_state.phase, media_replies[1]))
            if is_forbidden(ai_response):
                ai_response = random.choice(["nice","hmm","cool","interesting"])
            bot_state.last_sent_text = ai_response
            bot_state.chat_history.append({"role":"user","content":"[media]"})
            bot_state.chat_history.append({"role":"assistant","content":ai_response})
            try:
                sent = await client.send_message(TARGET_BOT, ai_response)
                bot_message_ids.add(sent.id)
                print(f"[{now()}] Reply: {ai_response}")
            except Exception as e: print(f"[{now()}] [Error] media: {e}")
            finally: bot_state.pending_reply = False
            return

        if any(x in text_lower for x in SYSTEM_MSGS):
            print(f"[{now()}] Skip system")
            return
        if len(text_clean) < 2 and text_clean not in ["M","F","m","f"]:
            print(f"[{now()}] Skip short: '{text_clean}'")
            return
        if bot_state.last_message_time:
            elapsed = (datetime.now() - bot_state.last_message_time).total_seconds()
            if elapsed < 5:
                print(f"[{now()}] Rate limit: {elapsed:.1f}s")
                return

        # Try to extract user's name from their message
        if not bot_state.user_name:
            name_patterns = [
                r"my name is (\w+)", r"im (\w+)", r"i am (\w+)", r"call me (\w+)",
                r"name[s]? (\w+)", r"^(\w+)$"
            ]
            for pattern in name_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    potential_name = match.group(1).capitalize()
                    if potential_name.lower() not in ["i", "a", "the", "my", "ur", "from", "india", "here", "there", "yes", "no", "ok", "yeah", "sure"]:
                        bot_state.user_name = potential_name
                        print(f"[{now()}] User name detected: {bot_state.user_name}")
                        break

        bot_state.pending_reply = True
        bot_state.chat_history.append({"role":"user","content":text})
        bot_state.message_count += 1
        bot_state.last_message_time = datetime.now()
        delay = random.randint(3,8)
        if len(text_clean) > 50: delay += random.randint(2,5)
        await asyncio.sleep(delay)
        try: ai_response = await get_ai_response(text)
        except Exception as e:
            print(f"[{now()}] [Error] AI: {e}")
            ai_response = get_smart_fallback(text, bot_state.phase)
        if is_forbidden(ai_response):
            print(f"[{now()}] [FILTER] Forbidden response detected, using fallback")
            ai_response = get_smart_fallback(text, bot_state.phase)
        if ai_response == bot_state.last_sent_text:
            ai_response = get_smart_fallback(text, bot_state.phase)
            while ai_response == bot_state.last_sent_text:
                ai_response = get_smart_fallback(text, bot_state.phase)
        bot_state.last_sent_text = ai_response
        bot_state.chat_history.append({"role":"assistant","content":ai_response})
        try:
            sent = await client.send_message(TARGET_BOT, ai_response)
            bot_message_ids.add(sent.id)
            print(f"[{now()}] Reply: {ai_response[:80]}")
        except Exception as e: print(f"[{now()}] [Error] send: {e}")
        finally: bot_state.pending_reply = False

    elif bot_state.state == BotState.RATING:
        if bot_state._rating_start_time:
            rating_elapsed = (datetime.now() - bot_state._rating_start_time).total_seconds()
            if rating_elapsed > 120:
                print(f"[{now()}] RATING timeout ({rating_elapsed:.0f}s), forcing wait")
                await force_wait()
                return
        if has_buttons:
            if is_4_option_screen(button_texts):
                print(f"[{now()}] 4-option reason screen in RATING, clicking Other")
                bot_state.report_reason_buttons_message_id = msg_id
                await asyncio.sleep(1)
                await select_report_other()
                return
            if is_rating_screen(button_texts):
                print(f"[{now()}] Rating screen with Report button")
                bot_state.report_buttons_message_id = msg_id
                await asyncio.sleep(1)
                await send_report()
                return
            texts_lower = [strip_emoji(t).lower() for t in button_texts]
            if any("report" in t for t in texts_lower):
                print(f"[{now()}] Found Report button in RATING")
                bot_state.report_buttons_message_id = msg_id
                await asyncio.sleep(1)
                await send_report()
                return
            if any("other" in t for t in texts_lower):
                print(f"[{now()}] Found Other button in RATING")
                bot_state.report_reason_buttons_message_id = msg_id
                await asyncio.sleep(1)
                await select_report_other()
                return
        if "rate your partner" in text_lower or "rate your vibe" in text_lower or "how was your chat" in text_lower or "they left you" in text_lower:
            bot_state.report_buttons_message_id = msg_id
            await asyncio.sleep(2)
            clicked = await click_report_button(msg_id)
            if not clicked:
                clicked = await click_report_button()
            if clicked:
                await asyncio.sleep(2)
                await try_click_other()
            else:
                print(f"[{now()}] Could not click report on rating text, will wait for button message")
        elif "partner left" in text_lower or "stranger left" in text_lower or "you got skipped" in text_lower:
            print(f"[{now()}] Partner left in RATING - trying report then wait")
            clicked = await click_report_button()
            if clicked:
                await asyncio.sleep(2)
                await try_click_other()
            else:
                await force_wait()

    elif bot_state.state == BotState.REPORTING:
        if bot_state._rating_start_time:
            reporting_elapsed = (datetime.now() - bot_state._rating_start_time).total_seconds()
            if reporting_elapsed > 120:
                print(f"[{now()}] REPORTING timeout ({reporting_elapsed:.0f}s), forcing wait")
                await force_wait()
                return
        if has_buttons:
            if is_4_option_screen(button_texts):
                print(f"[{now()}] 4-option reason screen in REPORTING, clicking Other")
                bot_state.report_reason_buttons_message_id = msg_id
                await asyncio.sleep(1)
                await select_report_other()
                return
            texts_lower = [strip_emoji(t).lower() for t in button_texts]
            if any("other" in t for t in texts_lower):
                print(f"[{now()}] Other button found in REPORTING")
                bot_state.report_reason_buttons_message_id = msg_id
                await asyncio.sleep(1)
                await select_report_other()
                return
            if any("report" in t for t in texts_lower) and not bot_state._report_clicked:
                print(f"[{now()}] Still on rating screen, clicking Report")
                bot_state.report_buttons_message_id = msg_id
                await asyncio.sleep(1)
                await send_report()
                return
        if any(x in text_lower for x in ["harassment","inappropriate","spam","reason","why","select","option"]):
            bot_state.report_reason_buttons_message_id = msg_id
            await asyncio.sleep(1)
            await select_report_other()
        elif "report sent" in text_lower or "we'll review" in text_lower or "report received" in text_lower or "thanks for reporting" in text_lower:
            print(f"[{now()}] Report confirmed - forcing wait")
            await force_wait()
        elif "find a new vibe" in text_lower:
            print(f"[{now()}] Find a new vibe in REPORTING - forcing wait")
            await force_wait()
        else:
            await asyncio.sleep(1)
            await select_report_other()

    elif bot_state.state == BotState.WAITING:
        if "find a new vibe" in text_lower:
            print(f"[{now()}] Find a new vibe in WAITING - checking if we should auto-find")
            if not bot_state._wait_task or bot_state._wait_task.done():
                print(f"[{now()}] Wait task not running, forcing find")
                async with bot_state._lock:
                    bot_state.state = BotState.IDLE
                    bot_state._wait_started = False
                await safe_start_finding()
        elif "report sent" in text_lower or "we'll review" in text_lower or "report received" in text_lower or "thanks for reporting" in text_lower:
            print(f"[{now()}] Report confirmed in WAITING - wait task already running")
        elif has_buttons:
            texts_lower = [strip_emoji(t).lower() for t in button_texts]
            if any("find a vibe" in t for t in texts_lower):
                print(f"[{now()}] Find Vibe button in WAITING - checking state")
                if not bot_state._wait_task or bot_state._wait_task.done():
                    async with bot_state._lock:
                        bot_state.state = BotState.IDLE
                        bot_state._wait_started = False
                    await safe_start_finding()
        if "already vibing" in text_lower:
            print(f"[{now()}] Already vibing in WAITING - fixing to CHATTING")
            bot_state.cancel_wait_task()
            async with bot_state._lock:
                bot_state.state = BotState.CHATTING
                bot_state._wait_started = False
                bot_state._force_wait_triggered = False
                if not bot_state.chat_start_time: bot_state.chat_start_time = datetime.now()
            bot_state._auto_end_task = asyncio.create_task(safe_auto_end_after_delay())
            bot_state._track_task(bot_state._auto_end_task)

    elif bot_state.state == BotState.IDLE:
        if "matched with a stranger" in text_lower:
            print(f"[{now()}] Matched while IDLE - fixing to CHATTING")
            async with bot_state._lock:
                bot_state.state = BotState.CHATTING
                bot_state.chat_start_time = datetime.now()
            bot_state._auto_end_task = asyncio.create_task(safe_auto_end_after_delay())
            bot_state._track_task(bot_state._auto_end_task)

async def safe_auto_end_after_delay():
    try: await auto_end_after_delay()
    except asyncio.CancelledError:
        print(f"[{now()}] Auto-end delay task cancelled")
        raise
    except Exception as e: print(f"[{now()}] [Error] auto_end delay: {e}")

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

async def rating_timeout_watchdog():
    await asyncio.sleep(60)
    async with bot_state._lock:
        if bot_state.state in [BotState.RATING, BotState.REPORTING] and not bot_state._rating_done:
            print(f"[{now()}] RATING WATCHDOG: Rating stuck for 60s, forcing wait")
            bot_state._rating_timeout_task = None
        else:
            print(f"[{now()}] RATING WATCHDOG: Rating completed or state changed, no action needed")
            return
    await force_wait()

@client.on(events.NewMessage(pattern=r"/start", from_users="me"))
async def cmd_start(event):
    await event.reply("Starting...")
    try:
        await client.send_message(TARGET_BOT, "/start")
        await asyncio.sleep(3)
        await safe_start_finding()
    except Exception as e: await event.reply(f"Error: {e}")

@client.on(events.NewMessage(pattern=r"/status", from_users="me"))
async def cmd_status(event):
    duration = 0
    if bot_state.chat_start_time: duration = (datetime.now() - bot_state.chat_start_time).seconds // 60
    rating_stuck = 0
    if bot_state._rating_start_time: rating_stuck = (datetime.now() - bot_state._rating_start_time).seconds
    status = f"""Status:
- State: {bot_state.state}
- Phase: {bot_state.phase}
- Persona: {persona.name}, {persona.age}, {persona.mood}
- Messages: {bot_state.message_count}
- Duration: {duration} min
- Total: {bot_state.total_interactions}
- Session: {bot_state._chat_session_id}
- Rating Done: {bot_state._rating_done}
- Wait Started: {bot_state._wait_started}
- Force Wait Triggered: {bot_state._force_wait_triggered}
- Report Clicked: {bot_state._report_clicked}
- Other Clicked: {bot_state._other_clicked}
- Stop Clicked: {bot_state._stop_clicked}
- Matched Msg ID: {bot_state._matched_message_id}
- Rating Stuck: {rating_stuck}s"""
    await event.reply(status)

@client.on(events.NewMessage(pattern=r"/stop", from_users="me"))
async def cmd_stop(event):
    async with bot_state._lock: 
        if bot_state.state == BotState.CHATTING:
            bot_state.state = BotState.RATING
            bot_state._rating_start_time = datetime.now()
    bot_state.cancel_all_tasks()
    await send_stop_and_report()
    await event.reply("Stopped and reporting...")

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
        bot_state._report_clicked = False
        bot_state._other_clicked = False
        bot_state._stop_clicked = False
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
        bot_state._report_clicked = False
        bot_state._other_clicked = False
        bot_state._stop_clicked = False
    await safe_start_finding()
    await event.reply("Skipped wait.")

async def keep_alive():
    while True:
        await asyncio.sleep(60)
        print(f"[{now()}] [KEEPALIVE] State: {bot_state.state}, Phase: {bot_state.phase}, Session: {bot_state._chat_session_id}, Tasks: {len(bot_state._active_tasks)}")

async def main():
    print("Riya v10.0 starting...")
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print("Missing API credentials!")
        return
    if not SESSION_STRING and not TELEGRAM_PHONE:
        print("Need SESSION_STRING or TELEGRAM_PHONE!")
        return
    if SESSION_STRING: await client.start()
    else: await client.start(phone=TELEGRAM_PHONE)
    me = await client.get_me()
    print(f"Logged in as {me.first_name}")
    print(f"Persona: {persona.name}, {persona.age}, {persona.location}, {persona.mood}")
    keepalive_task = asyncio.create_task(keep_alive())
    bot_state._track_task(keepalive_task)
    try:
        await client.send_message(TARGET_BOT, "/start")
        await asyncio.sleep(3)
        await safe_start_finding()
    except Exception as e: print(f"[{now()}] [Error] Initial: {e}")
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\nShutdown...")
    except Exception as e:
        print(f"Fatal: {e}")
        traceback.print_exc()
