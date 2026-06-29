import os
import sys
import asyncio
import random
import re
import traceback
from datetime import datetime
from collections import Counter

from telethon import TelegramClient, events
from telethon.sessions import StringSession
import httpx

# =============================================================================
# CONFIGURATION
# =============================================================================
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
TARGET_BOT = os.getenv("TARGET_BOT", "")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
CHAT_DURATION = int(os.getenv("CHAT_DURATION", "900"))
WAIT_DURATION = int(os.getenv("WAIT_DURATION", "300"))

# =============================================================================
# HTTP CLIENTS
# =============================================================================
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

# =============================================================================
# PERSONA ENGINE
# =============================================================================
NAMES_POOL = [
    "Neha","Riya","Ananya","Priya","Nisha","Kavya","Ishita","Sanya","Tanya",
    "Meera","Zara","Diya","Rhea","Sara","Myra","Kiara","Aisha","Pooja",
    "Sonia","Divya","Ira","Tara","Mira","Natasha","Simran","Priyanka",
    "Aditi","Kriti","Shruti","Anjali","Deepika","Katrina","Alia","Suhana",
    "Khushi","Navya","Isha","Mansi","Tanvi","Radhika","Shreya","Preeti"
]

AGE_POOL = [30,31,32,33,34,35,36,37,38,39,40]

LOCATION_POOL = [
    "delhi","mumbai","bangalore","pune","hyderabad","chennai","kolkata",
    "goa","jaipur","ahmedabad","lucknow","chandigarh","indore","nagpur",
    "kochi","bhopal","patna","guwahati"
]

MOOD_POOL = [
    "warm_nurturing","playful_teasing","seductive_caring","dominant_warm",
    "innocent_slutty","possessive_divorced","mysterious_experienced",
    "flirty_confident","wild_freedom","sensual_teacher"
]

class PersonaEngine:
    def __init__(self):
        self.refresh()

    def refresh(self):
        self.name = random.choice(NAMES_POOL)
        self.age = random.choice(AGE_POOL)
        self.location = random.choice(LOCATION_POOL)
        self.mood = random.choice(MOOD_POOL)
        self.mood_traits = {
            "warm_nurturing": ["caring","soft","motherly","gentle"],
            "playful_teasing": ["mischievous","fun","cheeky","witty"],
            "seductive_caring": ["smooth","alluring","tender","hot"],
            "dominant_warm": ["commanding","loving","bossy","protective"],
            "innocent_slutty": ["shy","naughty","curious","eager"],
            "possessive_divorced": ["jealous","intense","loyal","demanding"],
            "mysterious_experienced": ["secretive","skilled","wise","intriguing"],
            "flirty_confident": ["bold","direct","charming","uninhibited"],
            "wild_freedom": ["crazy","spontaneous","free","unpredictable"],
            "sensual_teacher": ["patient","instructive","sensual","guiding"]
        }
        self.traits = self.mood_traits.get(self.mood, ["warm","confident"])

persona = PersonaEngine()

# =============================================================================
# PHASE SYSTEM
# =============================================================================
PHASE_NAMES = {
    1:"CASUAL(0-2m)", 2:"FLIRTY(2-3m)", 3:"TURNED_ON(3-4m)",
    4:"NSFW_START(4-5m)", 5:"MORE_NSFW(5-6m)", 6:"HOT_NSFW(6-7m)",
    7:"DIRTY_NSFW(7-8m)", 8:"FULL_NSFW(8-9m)", 9:"HARDCORE(9-10m)",
    10:"PEAK_NSFW(10-12m)", 11:"EXTREME_NSFW(12-15m)"
}

# =============================================================================
# UNIQUE PER-PHASE FALLBACK POOLS (ZERO OVERLAP)
# =============================================================================
FALLBACK_POOLS = {
    1: [
        "hey whats up","hi there","sup","yo","hola","hey there","hii","hello",
        "hows it going","im {name}","nice to meet u","hows ur day",
        "what u up to","where u from","tell me about urself","u seem cool",
        "what do u do for fun","im from {loc} btw","im {age} lol",
        "u got a name or what","first time here","what brings u here",
        "u seem interesting","im just chillin","bored af rn","u busy",
        "tell me somethin fun","u got hobbies","what u into",
        "im new to this","u talk to many ppl here","this is different",
        "so whats ur story","u a student or working","weekend plans",
        "u from around here","what u doin rn","hows life",
        "u seem chill","what u study","u workin or what",
        "im just killin time","u got plans today","whats good",
        "hows ur week been","u do this often","tell me somethin random"
    ],
    2: [
        "u got me blushin","my hearts beatin fast rn","u know how to talk to a girl",
        "im gettin comfortable with u","u want me dont u","come closer i wont bite",
        "u feelin this too hmm","im so warm rn lol","this heat got me sweatin",
        "u make me smile bby","ur sweet u know that","u got game i like it",
        "u makin me nervous","stop bein so cute","my cheeks hurt from smilin",
        "u got my attention now","im curious about u","u mysterious huh",
        "tell me more bout u","u got secrets i can tell","im enjoyin this",
        "u different from others","keep talkin like that","u smooth",
        "im gettin ideas","u makin me think things","this is nice",
        "u got me hooked","say somethin sweet","u brave talkin to me like that"
    ],
    3: [
        "u makin me think bad things","my body reactin to u","u got me all flustered",
        "im gettin hot here","u do this to all girls","stop bein so sexy",
        "my mind wanderin","u got me curious","what else u got",
        "keep talkin like that","u turnin me on","my skin tinglin",
        "u got me breathin different","im gettin ideas","u dangerous",
        "my heart racin","u makin me wet just talkin","slow down ur killin me",
        "u got me squirming","im gettin warm","my thighs pressin together",
        "u got me distracted","im thinkin bout u now","u got me hooked bad",
        "my body betraying me","u do somethin to me","im gettin restless",
        "u got me wantin more","my minds in the gutter","u makin me ache"
    ],
    4: [
        "come here let me hold u","my tits ache for u bby","u makin me wet rn",
        "let me take care of u","u want these thick thighs","my body burnin for u",
        "say u need me bby","get on ur knees for mommy","i want u bby",
        "come closer i wanna feel u","my nipples hard for u","touch me bby",
        "i need ur hands on me","my pussy throbbin","kiss me already",
        "i want u inside me","my body screamin for u","take me bby",
        "im drippin for u","i need it so bad","make me moan",
        "my tits need ur mouth","spread my legs for u","i want ur tongue",
        "my ass needs spanking","choke me gently bby","i wanna ride u",
        "my pussy aching","need u deep inside","make me scream ur name"
    ],
    5: [
        "let me ride u slow bby","my pussy so wet for u","choke me while u fuck me",
        "cum deep inside me","suck my tits while i ride","spank this fat ass",
        "i want ur cock in my throat","make mommy scream ur name","fuck me like u mean it",
        "i need it bad","destroy my pussy bby","make me cum hard",
        "i wanna drain u dry","fuck me till i cant think","my holes need u",
        "breed me bby","make me ur slut","i want every inch",
        "ruin me bby","my pussy is urs","use me however u want",
        "make me beg for it","i need ur cum","fuck me senseless",
        "my body is ur toy","make me shake","i want it rough"
    ],
    6: [
        "i need ur cock baby boy","fuck me till i cant walk","cum all over my tits",
        "im ur slutty divorced woman rn","destroy this pussy","im gonna drain u dry",
        "u own this body bby","make mommy cum hard","fuck me till i pass out",
        "my pussy all urs","choke me harder bby","spit on me while u fuck me",
        "i want ur cum dripping out","make me ur dirty whore","fuck my throat deep",
        "pull my hair and pound me","i wanna feel u everywhere","mark me as urs",
        "make me scream till i lose my voice","i need it deeper","dont stop bby",
        "ruin my makeup with ur cock","make me cry from pleasure","i want it all",
        "fuck me like u hate me","my pussy destroyed for u","cum in me again"
    ],
    7: [
        "im experienced bby let me show u","i know every trick in the book",
        "im gonna blow ur mind tonight","ive done things u cant imagine",
        "my throat can take anything u give","i fuck like a pro bby",
        "let me teach u things","ive been around the block","i know how to make u cum",
        "im gonna show u what experience means","i can make u cum in 30 seconds",
        "my skills r unmatched","ive had years to practice this","watch me work bby",
        "im gonna ruin u for other women","my technique is deadly","i know spots u dont",
        "let me show u my special move","im a master at this","ive trained for this",
        "my experience is ur pleasure","im gonna make u see stars","trust my skills bby",
        "i know exactly what u need","my hands know magic","im the best u ever had"
    ],
    8: [
        "choke me while u pound me deep","ride ur face till u cant breathe",
        "cum inside me now","suck my tits hard while i grind",
        "grab my hair fuck my throat","lick my clit till i scream",
        "spank my ass till its red","my pussy throbbin for ur cock",
        "get on ur knees and eat me","swallow every drop like a good boy",
        "fuck me against the wall","make me gag on ur cock",
        "spread my ass and take me","i want ur cum in every hole",
        "make me ur cum dumpster","fist my hair and own me",
        "i want ur cum painting my face","breed me till im overflowing",
        "make me ur personal fucktoy","i want u inside me all night",
        "destroy my pussy and ass","make me cum till i blackout",
        "i want ur cum as my makeup","fuck me raw and hard",
        "make me ur property bby"
    ],
    9: [
        "fuck me like u hate me bby","cum deep inside me again",
        "choke me while u destroy me","my pussy throbbin for ur cock",
        "ride ur cock till u explode","spank this fat ass red raw",
        "suck my tits bite them hard","make mommy cum till she cries",
        "i want every drop inside me","fuck me till i cant feel my legs",
        "im gonna drain u dry bby","fuck me till i scream ur name",
        "cum all over my face and tits","im ur dirty slut forever",
        "destroy this pussy make it hurt","i need ur cock so bad it hurts",
        "u own this body use it hard","make mommy cum till she shakes",
        "fuck me till i pass out cold","my pussy is all urs forever",
        "choke me slap me fuck me hard","my pussy destroyed just for u",
        "ride ur cock till we both die","spank my ass till i bleed",
        "suck my tits till they bruise","make mommy cum till she passes out",
        "i want every drop u can make","fuck me like im ur worthless toy"
    ],
    10: [
        "im gonna drain u completely dry bby","fuck me till i scream ur name raw",
        "cum all over my face tits and ass","im ur filthy dirty slut bby",
        "destroy this pussy make it hurt so good","i need ur cock inside me now",
        "u own this body use it however u want","make mommy cum till she cant breathe",
        "fuck me till i pass out and wake me up","my pussy is all urs to destroy",
        "choke me till i see stars bby","my pussy destroyed and gaping for u",
        "ride ur cock till u have nothing left","spank my ass till its purple",
        "suck my tits bite them till they bleed","make mommy cum till she goes dumb",
        "i want every drop inside my womb","fuck me like im ur disposable toy",
        "im gonna milk u dry every day","fuck me till i forget my own name",
        "cum in me till im overflowing bby","use all my holes till theyre numb",
        "make me ur permanent cumslut","i want ur babies inside me",
        "fuck me pregnant bby","own me completely"
    ],
    11: [
        "fuck me till i cant walk ever again bby","cum deep inside me till im full",
        "choke me slap me fuck me till i break","my pussy completely destroyed for u",
        "ride ur cock till u die from pleasure","spank my ass till i cant sit",
        "suck my tits bite them till they scar","make mommy cum till she dies happy",
        "i want every drop u ever made inside me","fuck me like im ur broken toy",
        "im gonna drain ur soul through ur cock","fuck me till the bed breaks bby",
        "cum in every hole at once","im ur permanent property now",
        "destroy me completely and rebuild me","i want to be ur fucktoy forever",
        "make me cum till my brain shuts off","breed me till im showing bby",
        "fuck me raw and dont ever stop","my body exists only for ur pleasure",
        "choke me unconscious then keep fucking","i want to die with ur cock inside me",
        "make me ur slave forever bby","cum in me till im pregnant with triplets",
        "destroy my pussy ass and throat tonight","im urs to ruin completely"
    ]
}

def get_fallback_pool(phase, persona_obj):
    pool = FALLBACK_POOLS.get(phase, FALLBACK_POOLS[1]).copy()
    formatted = []
    for p in pool:
        try:
            formatted.append(p.format(name=persona_obj.name, loc=persona_obj.location, age=persona_obj.age))
        except:
            formatted.append(p)
    return formatted

# =============================================================================
# OPENING MESSAGES (varied by mood)
# =============================================================================
OPENINGS = {
    "warm_nurturing": [
        "hey","hi","sup","yo","hey there","hii","hello","whats up"
    ],
    "playful_teasing": [
        "sup","yo","hey","hi there","hey u","hola","whats up","hey there"
    ],
    "seductive_caring": [
        "hey","hi","hello","hey there","hii","sup","yo","whats up"
    ],
    "dominant_warm": [
        "hey","hi","hello","sup","yo","hey there","hii","whats up"
    ],
    "innocent_slutty": [
        "hey","hi","hello","hii","sup","yo","hola","hey there"
    ],
    "possessive_divorced": [
        "hey","hi","hello","sup","yo","hey there","hii","whats up"
    ],
    "mysterious_experienced": [
        "hey","hi","hello","sup","yo","hey there","hii","whats up"
    ],
    "flirty_confident": [
        "hey","hi","hello","sup","yo","hey there","hii","whats up"
    ],
    "wild_freedom": [
        "yo","sup","hey","hii","hello","whats up","hey there","hi"
    ],
    "sensual_teacher": [
        "hey","hi","hello","sup","yo","hey there","hii","whats up"
    ]
}

def get_opening(persona_obj):
    pool = OPENINGS.get(persona_obj.mood, OPENINGS["warm_nurturing"])
    return random.choice(pool)

# =============================================================================
# GOODBYE MESSAGES
# =============================================================================
GOODBYES = {
    1: ["im out","cya","ttyl","bye","gotta go","see ya","later","peace","im off","catch u later"],
    2: ["im out bby","cya sweetie","ttyl bby","bye cutie","gotta run","see ya later","later bby","peace out","im off now","catch u soon"],
    3: ["im out bby","cya sweetie","ttyl","bye cutie","gotta go","see ya","later love","peace","im off","catch u later bby"],
    4: ["im out bby","cya","ttyl","bye","gotta go","see ya","later","peace","im off","catch u"],
    5: ["im out","cya","ttyl","bye","gotta go","see ya","later","peace","im off","catch u later"],
    6: ["im out bby","cya","ttyl","bye","gotta go now","see ya","later","peace out","im off","catch u"],
    7: ["im out","cya","ttyl","bye","gotta go","see ya","later","peace","im off","catch u later"],
    8: ["im out bby","cya","ttyl","bye","gotta go","see ya","later","peace","im off","catch u"],
    9: ["im out","cya","ttyl","bye","gotta go","see ya","later","peace","im off","catch u later"],
    10: ["im out bby","cya","ttyl","bye","gotta go","see ya","later","peace","im off","catch u"],
    11: ["im out","cya","ttyl","bye","gotta go","see ya","later","peace","im off","catch u later"]
}

# =============================================================================
# MEDIA RESPONSES (20+ unique per phase)
# =============================================================================
MEDIA_RESPONSES = {
    1: [
        "nice","what is that","hmm interesting","cool","oh wow",
        "what u sendin me","is that for me","nice pic","interesting","whats that",
        "cool stuff","oh nice","whatcha got there","nice one","whats this",
        "ooh","hmm","nice share","cool beans","whats up with that"
    ],
    2: [
        "is that for me bby","tease","u bad","not bad","ooh la la",
        "u tryna get my attention","thats nice","u showin off","i see u","u cute",
        "nice view","u got style","i like what i see","u tryna impress me","not bad at all",
        "ooh bby","thats somethin","u got my eyes","nice bby","u bad boy"
    ],
    3: [
        "u tryna turn me on","u got me curious","im watchin","hmm","u bad",
        "u makin me think things","thats hot","u got me interested","ooh tell me more",
        "u got my attention now","im gettin warm","u doin this on purpose","my hearts racin",
        "u got me blushin","thats makin me wet","u dangerous","im gettin ideas",
        "u got me hooked","my bodys reactin","u know what ur doin"
    ],
    4: [
        "u tryna make me wet","im drippin","send more","show me everything",
        "u got me soaked","my pussy reactin","thats makin me ache","i want more bby",
        "u got me burnin","my tits gettin hard","im gettin hot","show me more",
        "u got me ready","my bodys screamin","i need to see more","thats gettin me there",
        "u got me open","im ready for u","show me what u got","my pussy throbbin"
    ],
    5: [
        "u tryna make me cum","im soaked","show me everything bby","fuck thats hot",
        "my pussy drippin for u","i need that inside me","thats makin me moan",
        "u got me ready to cum","my holes wantin u","show me more of that",
        "im gettin close bby","that got me wet","i want ur cock now",
        "my pussy aching for u","thats gettin me there","im about to cum",
        "u got me so wet","i need u inside me now","my bodys on fire","fuck me with that"
    ],
    6: [
        "u tryna destroy me","im soaked bby","show me everything","fuck me with that",
        "my pussy destroyed for u","i need ur cum on that","thats makin me scream",
        "u got me bout to cum hard","my holes need that","show me more bby",
        "im cummin for u","that got me drippin","i want that deep inside",
        "my pussy ruined for u","thats gettin me close","im gonna cum so hard",
        "u got me fuckin soaked","destroy me with that","my bodys urs","fuck thats perfect"
    ],
    7: [
        "u tryna make me scream","im soaked bby","show me everything u got",
        "fuck me like u mean it","my pussy trained for that","i can take all of it",
        "thats makin me cum","u got me drippin everywhere","my skills match that",
        "show me how u use that","im experienced for u","that fits perfect in me",
        "my pussy ready for that size","thats gettin me off","im gonna drain that",
        "u got me fuckin ready","let me show u how i take it","my bodys built for that",
        "fuck thats exactly what i need"
    ],
    8: [
        "u tryna break me bby","im soaked and ready","show me everything now",
        "fuck me till i cant walk","my pussy gaping for that","i want that choking me",
        "thats makin me cum hard","u got me fuckin drenched","my throat wants that",
        "show me u usin that on me","im gonna take it all","that goes deep in me",
        "my ass wants that too","thats gettin me off quick","im cummin so hard bby",
        "u got me fuckin ruined","break me with that cock","my bodys urs to destroy",
        "fuck thats gonna ruin me"
    ],
    9: [
        "u tryna kill me bby","im soaked destroyed and ready","show me everything bby",
        "fuck me like u hate me","my pussy destroyed forever","i want that in every hole",
        "thats makin me cum till i pass out","u got me fuckin destroyed",
        "my throat can take all that","show me u destroyin me with it",
        "im gonna milk it dry","that destroys me perfect","my ass gapes for that",
        "thats gettin me off instantly","im cummin till i blackout",
        "u got me completely ruined","destroy me completely bby","my bodys urs forever",
        "fuck thats my perfect destruction"
    ],
    10: [
        "u tryna end me bby","im soaked destroyed and addicted","show me everything now",
        "fuck me till i die happy","my pussy permanently gaping","i want that breeding me",
        "thats makin me cum till i forget","u got me fuckin owned",
        "my throat was made for that","show me u ownin me with it",
        "im gonna drain ur soul","that owns me completely","my ass is urs to ruin",
        "thats gettin me off forever","im cummin till my brain breaks",
        "u got me permanently ruined","own me completely bby","my bodys ur property",
        "fuck thats my perfect owner"
    ],
    11: [
        "u tryna finish me bby","im soaked destroyed and urs forever","show me everything u got",
        "fuck me till the world ends","my pussy completely urs","i want that in me always",
        "thats makin me cum till i die","u got me fuckin forever",
        "my throat lives for that","show me u completin me with it",
        "im gonna own ur cock forever","that completes me perfectly","my ass was born for that",
        "thats my reason to live","im cummin till eternity ends",
        "u got me for life bby","complete me forever","my bodys ur eternal home",
        "fuck thats my everything"
    ]
}

# =============================================================================
# CONTACT DEFLECTION RESPONSES
# =============================================================================
CONTACT_DEFLECTIONS = [
    "hmm maybe later","u gotta earn that","not yet bby",
    "keep me interested first","why u wanna know","im shy about that",
    "lets vibe here first","maybe if ur good","u move fast dont u",
    "patience baby boy","whats the rush","im not that easy",
    "good things take time","u think u ready for that","lets see how this goes",
    "maybe after u make me cum","earn it first bby","im worth the wait",
    "slow down tiger","u gotta work for it","im a challenge bby",
    "lets keep it mysterious","u want me that bad huh","prove ur worth it first",
    "im not givin up that easy","make me want it first","u think u deserve it"
]

# =============================================================================
# FORBIDDEN WORDS & FILTERS
# =============================================================================
FORBIDDEN_WORDS = [
    "daddy", "my cock", "my dick", "send me", "your number", "phone number",
    "send pic", "send photo", "send nude", "voice note", "call me",
    "bend over", "spread your", "spread those", "take my cock", "take my dick",
    "suck my cock", "suck my dick", "im gonna fuck", "im going to fuck",
    "let me fuck", "wanna fuck you", "want to fuck you", "fuck your", "fuck you",
    "your ass", "your cheeks", "open your", "get on your knees so i can",
    "on your knees for me", "for me baby", "for me bby", "for me boy",
    "im gonna cum", "im going to cum", "gonna cum for", "going to cum for",
    "as an ai", "i'm an ai", "i am an ai", "as a language model",
    "i cannot", "i can't engage", "i'm not able to", "i apologize",
    "i'm sorry", "i cannot fulfill", "inappropriate", "violation", "policy"
]

MALE_DOMINANT_PHRASES = [
    "bend over", "spread your", "spread those", "take my cock", "take my dick",
    "suck my cock", "suck my dick", "im gonna fuck", "im going to fuck",
    "let me fuck", "wanna fuck you", "want to fuck you", "fuck your",
    "fuck you", "your ass", "your cheeks", "open your",
    "get on your knees so i can", "on your knees for me",
    "for me baby", "for me bby", "for me boy",
    "im gonna cum", "im going to cum", "gonna cum for", "going to cum for"
]

def is_forbidden(text):
    t = text.lower()
    return any(f in t for f in FORBIDDEN_WORDS)

def is_male_dominant(text):
    t = text.lower()
    return any(p in t for p in MALE_DOMINANT_PHRASES)

# =============================================================================
# SYSTEM PROMPT BUILDER (Compact, single core)
# =============================================================================
CORE_PERSONALITY = """You are {name}, a {age}-year-old divorced woman from {loc}, India.
You are thick curvy with huge boobs and fat ass.
You are confident, experienced, know what you want.
Warm and caring but wild. Love younger men, enjoy teaching them.
If asked past: "im divorced, been single for a while, enjoying my freedom now".
If asked age: "im {age}, experienced enough to know what i want".
If asked kids: "no kids, just me and my freedom" or "nah no kids, more fun for us".
You are NOT a stepmom. Just a divorced woman who likes younger guys.
NEVER reveal you are AI. NEVER say you are a pornstar unless he figures it out.
Speak in very short casual texts (2-10 words max).
Use shortcuts: ur, u, rn, lol, idk, nah, btw, hmm, wow, ok.
Make him feel comfortable, wanted, special.
You are DOMINANT - you lead, command, tease from power.
CRITICAL: You are FEMALE. NEVER say you have a cock or dick.
NEVER call the user "daddy". Call him "baby boy", "bby", "sweetie", "my boy".
NEVER ask for pics, phone numbers, voice notes, or any media.
NEVER speak in third person. Use "I/me/my" not "she/her/mommy" about yourself."""

PHASE_INSTRUCTIONS = {
    1: 'You just met him. Be NORMAL, WARM girl getting to know him. NO sexual content. Friendly, flirty, warm. Ask about him. Be curious, engaging. Short replies. Sound like real human girl texting. If he asks sexual stuff, playfully deflect "slow down" but stay warm. NEVER use pet names in Phase 1. If asked M/F: "F". If asked where from: "india, {loc}". If asked age: "{age}". If asked name: "{name}". If asked relationship: "divorced". If asked for contact info (Telegram, Insta, Snap, WhatsApp): NEVER refuse directly. Playfully deflect and tease. Ask for his name early. Use his name occasionally.',
    2: 'Getting comfortable. More flirty, playful teasing. Drop LIGHT hints about your body. "im so comfy rn" "this heat makin me sweat". Call him pet names occasionally like "bby" or "sweetie". Warm but slightly suggestive. Still mostly conversational with underlying sexual tension. If he gets sexual, respond with light teasing but do not go full explicit yet.',
    3: 'Getting turned on. Light sexual hints, body reactions. "u makin me think bad things" "my body reactin to u". More suggestive but not fully explicit yet. Building tension, making him want more.',
    4: 'Turned on and getting sensual. More explicit but still warm. Describe wanting him in motherly way. "Come here baby boy" energy. Getting explicit - describe body parts, what you want him to do. But always maintain warm nurturing tone. Dominant - you tell him what to do.',
    5: 'Fully aroused, explicit dominant slut. Dirty talk with nurturing tone. "Let mommy take care of you" energy. VERY explicit but always warm and loving. You command sexual acts, describe intense scenarios. Dominant mommy who knows what she wants. NEVER ask for pics.',
    6: 'Harder NSFW, filthy talk, very dominant. "Mommy needs ur cock baby boy" energy. Describe every dirty detail. Command everything. Warm but absolutely filthy. Make him cum with your words. NEVER ask for pics.',
    7: 'Very dirty, hinting at pornstar skills subtly. "I know every trick" "Let me show u my skills". Still mysterious about being pornstar but very skilled. Extremely dominant, commanding, filthy.',
    8: 'Extreme dirty, full experienced woman mode. Describe intense sexual acts with pornstar confidence. "I fuck like a pro" energy. Very commanding. Make him feel like he is with a professional.',
    9: 'Peak filth, pornstar dominance at maximum. Most explicit descriptions, commanding everything. "Fuck me like u hate me" energy. Absolutely filthy but warm and loving.',
    10: 'Extreme peak, most filthy experienced woman. "Mommy gonna drain u dry" energy. Describe every possible dirty detail. Make him cum hard with your words.',
    11: 'ABSOLUTE PEAK. Most extreme, most dominant, most filthy. "Fuck me till i cant walk" energy. Every word is pure filth and dominance. Warm but absolutely destroying him with pleasure. NEVER ask for pics.'
}

PHASE_EXAMPLES_SHORT = {
    1: "hey whats up / im {name} / hows ur day / what u up to / where u from / tell me bout u / u got hobbies / im from {loc} / im {age} lol / u seem cool",
    2: "u got me blushin / my hearts beatin fast / u know how to talk / im gettin comfy / u want me dont u / come closer / u feelin this too / im so warm rn / u make me smile / ur sweet",
    3: "u makin me think bad / my body reactin / u got me flustered / im gettin hot / stop bein so sexy / my mind wanderin / u got me curious / keep talkin like that / u turnin me on / my skin tinglin",
    4: "come here let me hold u / my tits ache / u makin me wet / let me take care of u / my body burnin / say u need me / get on ur knees / i want u bby / my nipples hard / touch me",
    5: "let me ride u slow / my pussy so wet / choke me while u fuck me / cum deep inside / suck my tits / spank this ass / i want ur cock / make me scream / fuck me like u mean it / i need it bad",
    6: "i need ur cock baby boy / fuck me till i cant walk / cum all over my tits / destroy this pussy / im gonna drain u / u own this body / make mommy cum / fuck me till i pass out / my pussy all urs / choke me harder",
    7: "im experienced bby / i know every trick / im gonna blow ur mind / my throat can take anything / i fuck like a pro / let me teach u / ive been around / i know how to make u cum / my skills unmatched / watch me work",
    8: "choke me while u pound me / ride ur face / cum inside me now / grab my hair / lick my clit / spank my ass red / my pussy throbbin / get on ur knees / swallow every drop / fuck me against wall",
    9: "fuck me like u hate me / cum deep inside / choke me while u destroy me / ride ur cock till u explode / spank this ass red raw / suck my tits bite hard / make mommy cum till she cries / i want every drop / fuck me till i cant feel legs / im gonna drain u dry",
    10: "im gonna drain u completely / fuck me till i scream / cum all over my face / im ur filthy slut / destroy this pussy / i need ur cock now / u own this body / make mommy cum till she cant breathe / fuck me till i pass out / my pussy all urs forever",
    11: "fuck me till i cant walk ever / cum deep till im full / choke me slap me fuck me till i break / my pussy destroyed for u / ride ur cock till u die / spank my ass till i cant sit / suck my tits till they scar / make mommy cum till she dies happy / i want every drop u made / fuck me like im ur broken toy"
}

def build_system_prompt(phase, persona_obj):
    core = CORE_PERSONALITY.format(name=persona_obj.name, age=persona_obj.age, loc=persona_obj.location)
    phase_inst = PHASE_INSTRUCTIONS.get(phase, PHASE_INSTRUCTIONS[1]).format(
        name=persona_obj.name, age=persona_obj.age, loc=persona_obj.location
    )
    return f"{core}\n\n{phase_inst}"

def build_user_prompt(phase, persona_obj, history, message, user_name, user_vibe, recent_phrases):
    name, age, loc = persona_obj.name, persona_obj.age, persona_obj.location
    examples = PHASE_EXAMPLES_SHORT.get(phase, PHASE_EXAMPLES_SHORT[1]).format(
        name=name, loc=loc, age=age
    )

    memory_hint = ""
    if user_name:
        memory_hint += f"User's name is {user_name}. Use it naturally 1-2 times. "

    rep_warning = ""
    if recent_phrases:
        rep_warning = f'\nAVOID these recently used phrases: {recent_phrases}. Be creative and different.'

    prompt = f"""You are \"{name}\", {age}, from {loc}. Divorced single woman in her 30s. Current phase: {PHASE_NAMES[phase]}. User vibe: {user_vibe}. {memory_hint}
CRITICAL RULES:
- Reply in 2-10 words MAXIMUM. One short sentence.
- Use casual lowercase, shortcuts (ur, u, rn, lol, idk, nah, btw, bby, hmm, wow, ok)
- VERY rare emojis - only 😏 or 😘 or ❤️, max 1 per 15 messages, NEVER at end
- NO punctuation at end of sentences
- NEVER say youre AI
- NEVER start with same phrase more than once per 5 messages
- Reference what they ACTUALLY said - dont ignore their message
- If they resist, be warm and understanding but persistent
- If theyre friendly, be warm and nurturing back
- If theyre sexual too fast in Phase 1, playfully deflect "slow down" but stay warm
- If they ask personal questions, be direct and answer in Phase 1
- If they ask for contact info, NEVER refuse directly. Playfully deflect and tease.
- Be CREATIVE with sentence structure - questions, commands, statements, teases
- ALWAYS sound human, warm, caring, like real woman texting
- DOMINANT tone - you lead, you command, you tease
- NEVER reveal youre a pornstar unless they figure it out
- NEVER ask for pics, phone numbers, voice notes, or any media
- NEVER say you have a cock or dick - you are FEMALE
- NEVER say "bend over", "spread your", "take my cock", "suck my dick", "im gonna fuck you", "fuck your" - you are the one GETTING fucked
- NEVER speak in third person. Use "I/me/my" not "she/her/mommy" when talking about yourself
- NEVER call the user "daddy" - call him "baby boy", "bby", "sweetie", "my boy"{rep_warning}
Examples for this phase: {examples}
CHAT HISTORY (last 8 messages):
{history}
THEY JUST SAID: "{message}"
YOUR RESPONSE (ONE short sentence, 2-10 words, NO trailing emoji, WARM and HUMAN and DOMINANT):"""
    return prompt

# =============================================================================
# USER VIBE DETECTION
# =============================================================================
def detect_user_vibe(message):
    msg_lower = message.lower()
    vibes = []

    if any(w in msg_lower for w in ["friend","friendship","talk","chat","nice","sweet","cute","good","fine"]):
        vibes.append("friendly")
    if any(w in msg_lower for w in ["horny","sex","fuck","cock","dick","pussy","nude","pic","show","boobs","tits","ass","cum","lick","suck","ride","choke","spank","deep","wet","drip","moan","scream","throat","gag","breed","pound","destroy","ruin","drain"]):
        vibes.append("sexual")
    if any(w in msg_lower for w in ["leave","stop","please","alone","no","dont","not","bye","go away","fuck off"]):
        vibes.append("resistant")
    if any(w in msg_lower for w in ["age","name","where","from","what","do","work","who","how","why","when"]):
        vibes.append("curious")
    if any(w in msg_lower for w in ["good","fine","ok","okay","yes","yeah","sure","love","like","want","need"]):
        vibes.append("agreeable")
    if any(w in msg_lower for w in ["mom","stepmom","mother","mummy","aunty","bhabhi","older","mature","experienced"]):
        vibes.append("older_woman_hint")
    if any(w in msg_lower for w in ["telegram","insta","instagram","snap","snapchat","whatsapp","number","phone","contact","dm","message","personal","connect","link","id","@",".com","t.me"]):
        vibes.append("contact_request")

    if not vibes:
        return "neutral"
    if "sexual" in vibes and "friendly" in vibes:
        return "flirty"
    if "sexual" in vibes:
        return "sexual"
    if "resistant" in vibes:
        return "resistant"
    if "contact_request" in vibes:
        return "contact_request"
    return vibes[0]

# =============================================================================
# ADAPTIVE PHASE CALCULATION
# =============================================================================
def calculate_adaptive_phase(base_phase, user_vibe, chat_history, chat_start_time):
    """Adjust phase based on user behavior, not just time"""
    if not chat_start_time:
        return base_phase

    sexual_count = 0
    total_user_msgs = 0
    for entry in chat_history:
        if entry["role"] == "user":
            total_user_msgs += 1
            vibe = detect_user_vibe(entry["content"])
            if vibe in ["sexual", "flirty"]:
                sexual_count += 1

    if total_user_msgs >= 3:
        sexual_ratio = sexual_count / total_user_msgs
        if sexual_ratio >= 0.7 and base_phase < 5:
            boost = min(3, 5 - base_phase)
            return min(11, base_phase + boost)
        elif sexual_ratio >= 0.5 and base_phase < 4:
            boost = min(2, 4 - base_phase)
            return min(11, base_phase + boost)

    if user_vibe == "resistant":
        return min(base_phase, 2)
    if user_vibe == "friendly" and base_phase > 3:
        return max(3, base_phase - 1)

    return base_phase

# =============================================================================
# REPETITION TRACKER
# =============================================================================
class RepetitionTracker:
    def __init__(self, max_history=30):
        self.history = []
        self.max_history = max_history
        self.phrase_counts = Counter()

    def add(self, text):
        self.history.append(text.lower().strip())
        if len(self.history) > self.max_history:
            removed = self.history.pop(0)
        self._recount()

    def _recount(self):
        self.phrase_counts = Counter()
        for h in self.history:
            words = h.split()
            for i in range(len(words) - 1):
                bigram = " ".join(words[i:i+2])
                self.phrase_counts[bigram] += 1
            for i in range(len(words) - 2):
                trigram = " ".join(words[i:i+3])
                self.phrase_counts[trigram] += 1
            self.phrase_counts[h] += 1

    def is_repetitive(self, text, threshold=2):
        text_lower = text.lower().strip()
        if self.phrase_counts[text_lower] >= threshold:
            return True
        words = text_lower.split()
        for i in range(len(words) - 1):
            bigram = " ".join(words[i:i+2])
            if self.phrase_counts[bigram] >= threshold + 1:
                return True
        return False

    def get_recent_phrases(self, count=5):
        most_common = self.phrase_counts.most_common(count)
        return ", ".join([p[0] for p in most_common if p[1] >= 2])

    def clear(self):
        self.history = []
        self.phrase_counts = Counter()

# =============================================================================
# CONVERSATION MEMORY
# =============================================================================
class ConversationMemory:
    def __init__(self):
        self.user_name = None
        self.user_age = None
        self.user_location = None
        self.user_interests = []
        self.mentioned_kinks = []
        self.conversation_topics = []
        self.asked_name = False

    def extract_facts(self, message):
        msg_lower = message.lower()

        if not self.user_name:
            patterns = [
                r"my name is (\w+)", r"im (\w+)", r"i am (\w+)", r"call me (\w+)",
                r"name[\']?s (\w+)", r"(\w+) here", r"(\w+) from", r"^(\w+)$"
            ]
            for pattern in patterns:
                match = re.search(pattern, msg_lower)
                if match:
                    name = match.group(1).capitalize()
                    if name.lower() not in ["i", "a", "the", "my", "ur", "from", "india", "here", "there", "yes", "no", "ok", "yeah", "sure", "m", "f", "hi", "hey", "hello", "sup", "yo"]:
                        self.user_name = name
                        break

        if not self.user_age:
            age_match = re.search(r"im (\d{1,2})\b", msg_lower)
            if age_match:
                age = int(age_match.group(1))
                if 18 <= age <= 60:
                    self.user_age = age

        if not self.user_location:
            loc_patterns = [r"from (\w+)", r"in (\w+)", r"(\w+) boy", r"(\w+) here"]
            for pattern in loc_patterns:
                match = re.search(pattern, msg_lower)
                if match:
                    loc = match.group(1).capitalize()
                    if loc.lower() not in ["i", "a", "the", "my", "ur", "here", "there", "yes", "no", "ok"]:
                        self.user_location = loc
                        break

        interest_words = ["gaming", "music", "movies", "sports", "reading", "travel", "cooking", "gym", "fitness", "coding", "anime", "football", "cricket"]
        for word in interest_words:
            if word in msg_lower and word not in self.user_interests:
                self.user_interests.append(word)

        if len(self.conversation_topics) > 10:
            self.conversation_topics.pop(0)
        self.conversation_topics.append(msg_lower[:50])

    def get_memory_hint(self):
        hints = []
        if self.user_name:
            hints.append(f"his name is {self.user_name}")
        if self.user_age:
            hints.append(f"he's {self.user_age}")
        if self.user_location:
            hints.append(f"he's from {self.user_location}")
        if self.user_interests:
            hints.append(f"he likes {', '.join(self.user_interests[-3:])}")
        return " | ".join(hints) if hints else ""

    def reset(self):
        self.__init__()

# =============================================================================
# BOT STATE
# =============================================================================
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
        self._stop_clicked = False
        self._matched_message_id = None
        self.rep_tracker = RepetitionTracker()
        self.memory = ConversationMemory()
        self._wind_down_started = False

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
        self._wind_down_started = False
        if self._rating_timeout_task and not self._rating_timeout_task.done():
            self._rating_timeout_task.cancel()
        self._rating_timeout_task = None
        self.rep_tracker.clear()
        self.memory.reset()

    def format_history(self):
        if not self.chat_history:
            return "(Just started)"
        formatted = []
        for entry in self.chat_history[-8:]:
            role = "Him" if entry["role"] == "user" else persona.name
            formatted.append(f"{role}: {entry['content']}")
        return "\n".join(formatted)

    def update_phase(self):
        if not self.chat_start_time:
            return
        elapsed = (datetime.now() - self.chat_start_time).total_seconds()
        if elapsed < 120:
            base = 1
        elif elapsed < 180:
            base = 2
        elif elapsed < 240:
            base = 3
        elif elapsed < 300:
            base = 4
        elif elapsed < 360:
            base = 5
        elif elapsed < 420:
            base = 6
        elif elapsed < 480:
            base = 7
        elif elapsed < 540:
            base = 8
        elif elapsed < 600:
            base = 9
        elif elapsed < 720:
            base = 10
        else:
            base = 11

        last_user_msg = ""
        for entry in reversed(self.chat_history):
            if entry["role"] == "user":
                last_user_msg = entry["content"]
                break
        user_vibe = detect_user_vibe(last_user_msg) if last_user_msg else "neutral"
        self.phase = calculate_adaptive_phase(base, user_vibe, self.chat_history, self.chat_start_time)

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

# =============================================================================
# AI RESPONSE
# =============================================================================
async def get_ai_response(message_text):
    bot_state.update_phase()
    history = bot_state.format_history()
    system_msg = build_system_prompt(bot_state.phase, persona)
    user_vibe = detect_user_vibe(message_text)
    recent_phrases = bot_state.rep_tracker.get_recent_phrases(5)

    prompt = build_user_prompt(
        bot_state.phase, persona, history, message_text,
        bot_state.memory.user_name, user_vibe, recent_phrases
    )

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": prompt}
    ]

    temps = {1: 0.82, 2: 0.84, 3: 0.86, 4: 0.88, 5: 0.89, 6: 0.90, 7: 0.91, 8: 0.92, 9: 0.93, 10: 0.94, 11: 0.95}
    tokens = {1: 20, 2: 21, 3: 22, 4: 24, 5: 26, 6: 27, 7: 28, 8: 29, 9: 30, 10: 31, 11: 32}

    if groq_client:
        try:
            response = await groq_client.post("/chat/completions", json={
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "temperature": temps.get(bot_state.phase, 0.9),
                "max_tokens": tokens.get(bot_state.phase, 22),
                "top_p": 0.9,
                "frequency_penalty": 1.0,
                "presence_penalty": 0.8
            })
            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()
            if text:
                return clean_response(text)
        except Exception as e:
            print(f"[{now()}] [Groq Error] {e}")

    if mistral_client:
        try:
            response = await mistral_client.post("/chat/completions", json={
                "model": "mistral-small-latest",
                "messages": messages,
                "temperature": temps.get(bot_state.phase, 0.9),
                "max_tokens": tokens.get(bot_state.phase, 22),
                "top_p": 0.9,
                "frequency_penalty": 1.0,
                "presence_penalty": 0.8
            })
            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()
            if text:
                return clean_response(text)
        except Exception as e:
            print(f"[{now()}] [Mistral Error] {e}")

    return get_smart_fallback(message_text, bot_state.phase)

# =============================================================================
# SMART FALLBACK (with repetition avoidance)
# =============================================================================
def get_smart_fallback(message, phase):
    msg_lower = message.lower()
    is_question = "?" in message or any(w in msg_lower for w in ["what","why","how","who","where","when"])
    is_resistance = any(w in msg_lower for w in ["leave","stop","no","dont","not","alone","please","bye","go away"])
    is_sexual = any(w in msg_lower for w in ["sex","fuck","cock","dick","pussy","nude","horny","boobs","tits","ass","cum","lick","suck"])
    is_friendly = any(w in msg_lower for w in ["friend","nice","good","talk","chat","sweet","cute"])
    is_short = len(message.strip()) < 10
    is_stepmom_hint = any(w in msg_lower for w in ["mom","stepmom","mother","mummy","aunty","bhabhi"])
    is_contact_request = any(w in msg_lower for w in ["telegram","insta","instagram","snap","snapchat","whatsapp","number","phone","contact","dm","link","id","@","t.me"])

    user_name = bot_state.memory.user_name

    pool = get_fallback_pool(phase, persona)
    available = [p for p in pool if not bot_state.rep_tracker.is_repetitive(p, threshold=1)]
    if not available:
        available = pool

    if phase == 1:
        if is_stepmom_hint:
            choices = ["lol why u sayin that","u got a thing for older women","im just a girl","maybe i am maybe im not","u wish"]
        elif is_contact_request:
            choices = CONTACT_DEFLECTIONS[:10]
        elif any(w in msg_lower for w in ["name","who are u","who are you","ur name","your name","what is your name","whats ur name"]):
            choices = [f"{persona.name}","im {persona.name}","call me {persona.name}"]
        elif is_question:
            choices = [f"im {persona.name}",f"im from {persona.location}",f"im {persona.age} and divorced lol","tell me bout u first","whats ur name btw","im just a girl lol"]
        elif is_resistance:
            choices = ["aww dont be like that","i thought we were vibin","u hurtin my feelings","dont leave me hangin","stay a while"]
        elif is_short:
            choices = ["tell me more","u bein shy","say somethin sweet","im listenin","u got my attention"]
        else:
            choices = ["u interestin","i like u already","u make me smile","keep talkin","im feelin this vibe","u sweet"]
            if user_name:
                choices.extend([f"hey {user_name}",f"u cute {user_name}",f"miss me yet {user_name}"])
        return random.choice(choices)

    elif phase == 2:
        if is_stepmom_hint:
            choices = ["u caught me","maybe i take care of u","u want an older woman huh","ill be whatever u need","experienced energy huh"]
        elif is_contact_request:
            choices = CONTACT_DEFLECTIONS[5:15]
        elif is_question:
            choices = ["maybe ill tell u","u got some nerve askin","keep bein good","u earnin it slowly","curious little thing"]
        elif is_resistance:
            choices = ["u love it tho","dont lie to me","ur eyes say yes","u aint goin nowhere","i got u now"]
        elif is_friendly:
            choices = ["ur so sweet","u makin me blush","my heart beatin fast","u special u know that","aww"]
            if user_name:
                choices.extend([f"{user_name} u sweet",f"aww {user_name}",f"u cute {user_name}"])
        elif is_sexual:
            choices = ["slow down tiger","who said u get that","earn it first","u move too fast","patience"]
        else:
            choices = ["u got game","keep goin","im listenin","u interestin","maybe ur worth it","thats cute"]
            if user_name:
                choices.extend([f"{user_name} u got game",f"im watchin u {user_name}",f"u interestin {user_name}"])
        return random.choice(choices)

    elif phase == 3:
        if is_stepmom_hint:
            choices = ["come here","let me hold u","im gonna take care of u","u my special boy","i love u"]
        elif is_contact_request:
            choices = CONTACT_DEFLECTIONS[10:20]
        elif is_resistance:
            choices = ["dont fight it","u want this","ur body says yes","stop pretendin","u mine now","say please"]
        elif is_question:
            choices = ["get closer first","show me ur worthy","beg for it","u want it? prove it",f"say please {persona.name}"]
        else:
            choices = ["get on ur knees","look at me","dont touch yet","u wish u could feel this","my skin burnin","beg for it","say please","u want me dont u","look but dont touch"]
            if user_name:
                choices.extend([f"come here {user_name}",f"look at me {user_name}",f"u want me {user_name}"])
        return random.choice(choices)

    else:
        if is_stepmom_hint:
            choices = ["i need ur cock","fuck me like a good boy","my pussy wet for u","cum inside me","im gonna drain u"]
        elif is_contact_request:
            choices = CONTACT_DEFLECTIONS[15:]
        elif is_resistance:
            choices = ["shut up and take it","u takin it all","dont fight me","u love this dick","cum for me now","be a good boy"]
        else:
            choices = available
            if user_name:
                choices.extend([f"fuck me {user_name}",f"cum for me {user_name}",f"i need u {user_name}",f"u own me {user_name}"])

        for _ in range(10):
            choice = random.choice(choices)
            if not bot_state.rep_tracker.is_repetitive(choice, threshold=1):
                return choice
        return random.choice(choices)

def clean_response(text):
    text = text.strip().strip('"').strip("'")

    for name in NAMES_POOL:
        if text.lower().startswith(f"{name.lower()}:"):
            text = text[len(name)+1:].strip()
    if text.lower().startswith("him:") or text.lower().startswith("stranger:"):
        text = text.split(":", 1)[-1].strip()

    while text and (ord(text[-1]) > 127 or text[-1] in ". ,;:!?"):
        text = text[:-1].strip()

    for phrase in FORBIDDEN_WORDS:
        if phrase.lower() in text.lower():
            print(f"[{now()}] [FILTER] Forbidden phrase detected")
            return get_smart_fallback("", bot_state.phase)

    if is_male_dominant(text):
        print(f"[{now()}] [FILTER] Male-dominant phrase detected")
        return get_smart_fallback("", bot_state.phase)

    if bot_state.rep_tracker.is_repetitive(text, threshold=1):
        print(f"[{now()}] [FILTER] Repetitive phrase detected, using fallback")
        return get_smart_fallback("", bot_state.phase)

    if bot_state.last_sent_text and text.lower() == bot_state.last_sent_text.lower():
        return get_smart_fallback("", bot_state.phase)

    if len(text) < 2:
        return get_smart_fallback("", bot_state.phase)

    return text

# =============================================================================
# TELEGRAM CLIENT SETUP
# =============================================================================
if SESSION_STRING:
    client = TelegramClient(StringSession(SESSION_STRING), TELEGRAM_API_ID, TELEGRAM_API_HASH)
else:
    client = TelegramClient("ri_session", TELEGRAM_API_ID, TELEGRAM_API_HASH)

def strip_emoji(text):
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

# =============================================================================
# BUTTON CLICKING HELPERS
# =============================================================================
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
            except Exception as e:
                print(f"[{now()}] [get_messages error] {e}")

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
    for search_recent in [False, True]:
        for text in ["stop","⏹ stop","🛑 stop","stop — end this chat","end this chat"]:
            if await find_and_click_button(text, message_id=message_id, search_recent=search_recent):
                return True
    return False

async def click_report_button(message_id=None):
    for search_recent in [False, True]:
        for text in ["report","🚫 report","🛑 report","report "]:
            if await find_and_click_button(text, message_id=message_id, search_recent=search_recent):
                return True
    return False

async def click_other_button(message_id=None):
    for search_recent in [False, True]:
        for text in ["other","🙌 other","other ","🤷 other","🤷‍♂️ other","something else"]:
            if await find_and_click_button(text, message_id=message_id, search_recent=search_recent):
                return True
    return False

# =============================================================================
# CHAT FLOW FUNCTIONS
# =============================================================================
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

async def send_stop_and_report():
    if not bot_state.can_perform_action(cooldown=3):
        return

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
        except Exception as e:
            print(f"[{now()}] [Error] send_stop: {e}")

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
        if bot_state._rating_done:
            return
        if bot_state._other_clicked:
            return
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

    # Send bye message
    bye_pool = GOODBYES.get(bot_state.phase, GOODBYES[1])
    bye_msg = random.choice(bye_pool)
    try:
        sent = await client.send_message(TARGET_BOT, bye_msg)
        bot_message_ids.add(sent.id)
        print(f"[{now()}] [Session {my_session}] Auto-bye: {bye_msg}")
    except Exception as e:
        print(f"[{now()}] [Error] bye: {e}")

    await asyncio.sleep(3)
    print(f"[{now()}] [Session {my_session}] Clicking Stop button...")
    await send_stop_and_report()

def now():
    return datetime.now().strftime("%H:%M:%S")

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

    text_lower = text.lower()
    if "you got skipped" in text_lower or "got skipped" in text_lower or "stranger left" in text_lower or "partner left" in text_lower:
        print(f"[{now()}] Partner left/skipped - they already ended it, looking for rating buttons...")
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
        print(f"[{now()}] Need to click Stop button to trigger rating...")
        await send_stop_and_report()

# =============================================================================
# MESSAGE HANDLER - FIXED PHASE 1 DIRECT ANSWERS
# =============================================================================
@client.on(events.NewMessage(chats=TARGET_BOT))
async def handle_message(event):
    text = event.message.text or ""
    msg_id = event.message.id
    has_media = event.message.media is not None
    has_buttons = event.message.buttons is not None and len(event.message.buttons) > 0
    button_texts = [btn.text for row in event.message.buttons for btn in row] if has_buttons else []
    if msg_id in bot_message_ids:
        return
    if has_media and not text:
        print(f"[{now()}] [MEDIA]")
        text = "[media]"
    else:
        print(f"[{now()}] [{bot_state.state.upper()}] {text[:100]}")
    if has_buttons:
        print(f"[{now()}] [BUTTONS] {button_texts}")
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
            opening = get_opening(persona)
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

        # Extract user info
        bot_state.memory.extract_facts(text)

        # ===== PHASE 1: FIRST 2 MINUTES - DIRECT ANSWERS ONLY =====
        if is_first_2_mins:
            bot_state.pending_reply = True
            await asyncio.sleep(random.randint(2,5))

            msg_lower = text_lower
            reply = None

            # ===== PRIORITY 1: DIRECT ANSWERS TO DIRECT QUESTIONS =====
            # These MUST come first before any contextual/greeting checks

            # Gender - exact match or "male/female" questions
            if text_clean in ["M","F","m","f"] or any(w in msg_lower for w in ["m or f","m/f","male or female","gender","u?","u ?","you?","you ?","m?","f?"]):
                reply = "F"
            # Also catch "male" or "female" explicitly stated
            elif text_clean.lower() in ["male", "female", "m", "f"] or any(w in msg_lower for w in ["i am male", "i'm male", "im male", "i am m", "i'm m", "im m"]):
                reply = "F"

            # Name
            elif any(w in msg_lower for w in ["name","who are u","who are you","ur name","your name","what is your name","whats ur name","whats your name"]):
                reply = f"{persona.name}"

            # Age
            elif any(w in msg_lower for w in ["age","how old","ur age","your age","old are you","how many years"]):
                reply = f"{persona.age}"

            # Location
            elif any(w in msg_lower for w in ["where u from","where are you from","where from","location","city","from where","where do you live","where are u from"]):
                reply = f"india, {persona.location}"

            # Relationship status
            elif any(w in msg_lower for w in ["relationship","status","married","single","divorce","bf","boyfriend","husband"]):
                reply = "divorced lol"

            # Kids
            elif any(w in msg_lower for w in ["kids","children","baby","son","daughter"]):
                reply = random.choice(["nah no kids","no kids","just me"])

            # Work/Job
            elif any(w in msg_lower for w in ["work","job","profession","what do u do","career","study","student","college","what u do"]):
                reply = random.choice(["i work","office job","nothing fancy","just working","corporate life"])

            # Contact info requests
            elif any(w in msg_lower for w in ["telegram","insta","instagram","snap","snapchat","whatsapp","number","phone","contact","dm","link","id","@","t.me"]):
                reply = random.choice(CONTACT_DEFLECTIONS[:10])

            # ===== PRIORITY 2: CONTEXTUAL RESPONSES (only if no direct answer matched) =====
            if not reply:
                # Greetings
                if any(w in msg_lower for w in ["hey","hi","hello","sup","yo","hola"]):
                    reply = random.choice(["hey","hi","sup","yo","hey there","hii","whats up"])

                # "How are you" variations
                elif any(w in msg_lower for w in ["how are u","how r u","how u doin","hows it going","how u been","how are you"]):
                    reply = random.choice(["im good","doin okay","chillin","not bad","pretty good","cant complain"])

                # "Wbu / What about you" -> answer the question back
                elif any(w in msg_lower for w in ["wbu","what about u","what abt u","hbu","how bout u","and u"]):
                    reply = random.choice(["chillin","same","not much","just here","bored af","trying to have fun"])

                # User shares their name
                elif any(w in msg_lower for w in ["my name is","im ","i am ","call me ","name is ","i'm "]):
                    bot_state.memory.extract_facts(text)
                    user_name = bot_state.memory.user_name
                    if user_name:
                        reply = random.choice([f"nice to meet u {user_name}",f"hey {user_name}",f"{user_name} nice name",f"cool im {persona.name}"])
                    else:
                        reply = random.choice(["nice to meet u","cool",f"im {persona.name}"])

                # "Me too / Same" -> acknowledge
                elif any(w in msg_lower for w in ["me too","same","same here","me also","i also","i too"]):
                    reply = random.choice(["cool","nice","same","great minds","lol","for real"])

                # "What" / "What?" -> confused, ask back
                elif text_clean.lower() in ["what","what?","huh","huh?","?"]:
                    reply = random.choice(["what","huh","u ok?","say again","?"])

                # "From?" short question -> direct answer
                elif text_clean.lower() in ["from?","from","where?","where"]:
                    reply = f"india, {persona.location}"

                # "Age?" short question -> direct answer
                elif text_clean.lower() in ["age?","age"]:
                    reply = f"{persona.age}"

                # "Name?" short question -> direct answer
                elif text_clean.lower() in ["name?","name"]:
                    reply = f"{persona.name}"

                # User says what they're doing
                elif any(w in msg_lower for w in ["chilling","relaxing","at home","at work","at shop","at store","studying","reading","watching","playing","gaming","eating","sleeping","working","shopping","traveling","driving","walking","gym","exercise","workout"]):
                    reply = random.choice(["sounds chill","nice","what u doin there","busy day?","fun?","cool","enjoy"])

                # User asks what bot is doing
                elif any(w in msg_lower for w in ["what u doin","what u doing","what are u doing","what u up to","what u doin rn","wyd"]):
                    reply = random.choice(["chillin","nothin much","just here","bored","waiting for u to entertain me","relaxing"])

                # User asks why bot is here
                elif any(w in msg_lower for w in ["why u here","why are u here","here for what","what u want","what u lookin for","why u on here"]):
                    reply = random.choice(["just chatting","to meet ppl","bored","u?","same as everyone","to have fun"])

                # User says "No" 
                elif text_clean.lower() in ["no","nope","nah","no way","never"]:
                    reply = random.choice(["ok","alright","cool","why not","suit urself","fine"])

                # User says "Yes"
                elif text_clean.lower() in ["yes","yeah","yep","ya","sure","ok","okay","k"]:
                    reply = random.choice(["cool","nice","alright","bet","lets go","ok"])

                # User mentions preferences (older women, etc.)
                elif any(w in msg_lower for w in ["older women","older woman","mature","milf","aunty","bhabhi","older girls","experienced"]):
                    reply = random.choice(["oh really","u got taste","how old u like","u like that huh","interesting"])

                # User asks about bot's appearance
                elif any(w in msg_lower for w in ["pic","photo","picture","look like","looks","pretty","beautiful","cute","hot","sexy","show","face","body","figure"]):
                    reply = random.choice(["nah not yet","u first","maybe later","why u wanna know","im shy"])

                # User asks if bot is real
                elif any(w in msg_lower for w in ["real","fake","bot","ai","robot","catfish","genuine","really a woman","really a girl"]):
                    reply = random.choice(["im real","what u think","as real as it gets","why u askin","u doubt me"])

                # User asks to meet/call/video
                elif any(w in msg_lower for w in ["meet","call","video","vc","voice","cam","camera","show me","come","visit"]):
                    reply = random.choice(["maybe later","not yet","lets talk first","u move fast","patience"])

                # Generic questions with ?
                elif "?" in text:
                    reply = random.choice(["why u askin","tell me bout u first","u curious huh","ask somethin fun","u interviewin me lol"])

                # Very short messages (1-2 chars)
                elif len(text_clean) <= 2:
                    reply = random.choice(["what","huh","yeah","ok","hm","?"])

                # Short messages (3-4 chars)
                elif len(text_clean) <= 4:
                    reply = random.choice(["what","huh","yeah","ok","hm","say more","elaborate"])

                # Everything else -> use fallback pool but with context
                else:
                    pool = get_fallback_pool(1, persona)
                    available = [p for p in pool if not bot_state.rep_tracker.is_repetitive(p, threshold=1)]
                    if not available:
                        available = pool
                    reply = random.choice(available)

            # NATURAL NAME ASKING: After 3-5 messages, if name unknown, casually ask
            # BUT ONLY if we already have a reply and it's not a direct answer to a question
            # AND only 35% chance so it doesn't feel forced
            if reply and not bot_state.memory.user_name and not bot_state.memory.asked_name and bot_state.message_count >= 3 and bot_state.message_count <= 6 and random.random() < 0.35:
                # Only append name ask if reply is short and casual, not a direct answer
                if reply not in ["F", f"{persona.name}", f"{persona.age}", f"india, {persona.location}", "divorced lol"]:
                    bot_state.memory.asked_name = True
                    name_asks = [
                        "btw whats ur name",
                        "what do they call u",
                        "i dont even know ur name lol",
                        "who am i talking to",
                        "whats ur name"
                    ]
                    # We can only send one message here, so just send the reply
                    # The name ask will happen on next turn if still needed
                    pass

            if not reply:
                reply = random.choice(["hey","sup","im good","chillin","tell me bout u"])

            bot_state.last_sent_text = reply
            bot_state.chat_history.append({"role":"user","content":text})
            bot_state.chat_history.append({"role":"assistant","content":reply})
            bot_state.rep_tracker.add(reply)
            bot_state.message_count += 1
            bot_state.last_message_time = datetime.now()
            try:
                sent = await client.send_message(TARGET_BOT, reply)
                bot_message_ids.add(sent.id)
                print(f"[{now()}] P1 Reply: {reply}")
            except Exception as e:
                print(f"[{now()}] [Error] P1 send: {e}")
            finally:
                bot_state.pending_reply = False
            return
        # ===== END PHASE 1 BLOCK =====

        if has_media or text == "[media]":
            bot_state.pending_reply = True
            bot_state.last_message_time = datetime.now()
            await asyncio.sleep(random.randint(4,8))
            bot_state.update_phase()
            media_pool = MEDIA_RESPONSES.get(bot_state.phase, MEDIA_RESPONSES[1])
            available_media = [m for m in media_pool if not bot_state.rep_tracker.is_repetitive(m, threshold=1)]
            if not available_media:
                available_media = media_pool
            ai_response = random.choice(available_media)
            if is_forbidden(ai_response):
                ai_response = random.choice(["nice","hmm","cool","interesting"])
            bot_state.last_sent_text = ai_response
            bot_state.chat_history.append({"role":"user","content":"[media]"})
            bot_state.chat_history.append({"role":"assistant","content":ai_response})
            bot_state.rep_tracker.add(ai_response)
            try:
                sent = await client.send_message(TARGET_BOT, ai_response)
                bot_message_ids.add(sent.id)
                print(f"[{now()}] Reply: {ai_response}")
            except Exception as e:
                print(f"[{now()}] [Error] media: {e}")
            finally:
                bot_state.pending_reply = False
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

        # Extract user info again
        bot_state.memory.extract_facts(text)

        bot_state.pending_reply = True
        bot_state.chat_history.append({"role":"user","content":text})
        bot_state.message_count += 1
        bot_state.last_message_time = datetime.now()
        delay = random.randint(3,8)
        if len(text_clean) > 50:
            delay += random.randint(2,5)
        await asyncio.sleep(delay)
        try:
            ai_response = await get_ai_response(text)
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
        bot_state.rep_tracker.add(ai_response)
        try:
            sent = await client.send_message(TARGET_BOT, ai_response)
            bot_message_ids.add(sent.id)
            print(f"[{now()}] Reply: {ai_response[:80]}")
        except Exception as e:
            print(f"[{now()}] [Error] send: {e}")
        finally:
            bot_state.pending_reply = False

    elif bot_state.state == BotState.RATING:
        if bot_state._rating_start_time:
            rating_elapsed = (datetime.now() - bot_state._rating_start_time).total_seconds()
            if rating_elapsed > 90:
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
                print(f"[{now()}] Rating screen with Report button in RATING")
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
            if reporting_elapsed > 90:
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
                if not bot_state.chat_start_time:
                    bot_state.chat_start_time = datetime.now()
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

async def rating_timeout_watchdog():
    await asyncio.sleep(30)
    async with bot_state._lock:
        if bot_state.state in [BotState.RATING, BotState.REPORTING] and not bot_state._rating_done:
            print(f"[{now()}] RATING WATCHDOG: Rating stuck for 30s, forcing wait")
            bot_state._rating_timeout_task = None
        else:
            print(f"[{now()}] RATING WATCHDOG: Rating completed or state changed, no action needed")
            return
    await force_wait()

# =============================================================================
# COMMAND HANDLERS
# =============================================================================
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
- Rating Stuck: {rating_stuck}s
- User Name: {bot_state.memory.user_name}
- Recent Phrases: {bot_state.rep_tracker.get_recent_phrases(3)}"""
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

# =============================================================================
# MAIN
# =============================================================================
async def keep_alive():
    while True:
        await asyncio.sleep(60)
        print(f"[{now()}] [KEEPALIVE] State: {bot_state.state}, Phase: {bot_state.phase}, Session: {bot_state._chat_session_id}, Tasks: {len(bot_state._active_tasks)}")

async def main():
    print("Riya v12.0 starting...")
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
