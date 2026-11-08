import re
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(title="Regional English Rewriter", version="1.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

Region = Literal["auto", "en-NG", "en-GB", "en-INT", "en-US", "pcm-NG"]
Tone = Literal["keep", "casual", "professional", "academic", "concise"]

REGION_NAMES = {
    "en-NG": "Nigerian English",
    "en-GB": "British English",
    "en-INT": "International English",
    "en-US": "American English",
    "pcm-NG": "Nigerian Pidgin",
}

class RewriteRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    region: Region = "auto"
    tone: Tone = "keep"

class RewriteResponse(BaseModel):
    rewritten_text: str
    region: str
    region_name: str
    engine: str
    notice: str | None = None


def has_phrase(text: str, phrase: str) -> bool:
    return bool(re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text, re.IGNORECASE))


def detect_region(text: str) -> str:
    """Conservatively suggest a region only when the text contains clear markers."""
    pidgin_markers = ("abeg", "wahala", "na wa", "wetin", "dey", "no wahala", "shey")
    ng_markers = ("japa", "gist", "omo", "oga", "sharp sharp", "pepper dem", "post utme")
    uk_markers = ("colour", "organise", "centre", "realise", "flat", "queue", "lorry", "holiday")
    us_markers = ("color", "organize", "center", "realize", "apartment", "vacation", "sidewalk")
    if any(has_phrase(text, marker) for marker in pidgin_markers):
        return "pcm-NG"
    if any(has_phrase(text, marker) for marker in ng_markers):
        return "en-NG"
    if any(has_phrase(text, marker) for marker in uk_markers):
        return "en-GB"
    if any(has_phrase(text, marker) for marker in us_markers):
        return "en-US"
    return "en-INT"


def preserve_case(source: str, replacement: str) -> str:
    if source.isupper():
        return replacement.upper()
    if source[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def replace_phrases(text: str, replacements: list[tuple[str, str]]) -> str:
    """Apply longer phrases first, using case-insensitive whole-word matching."""
    for source, target in sorted(replacements, key=lambda pair: len(pair[0]), reverse=True):
        pattern = re.compile(r"(?<!\w)" + re.escape(source) + r"(?!\w)", re.IGNORECASE)
        text = pattern.sub(lambda match, value=target: preserve_case(match.group(0), value), text)
    return text


BRITISH_SPELLINGS = [
    ("favorite", "favourite"), ("favorites", "favourites"),
    ("color", "colour"), ("colors", "colours"),
    ("organize", "organise"), ("organizes", "organises"), ("organized", "organised"), ("organizing", "organising"),
    ("realize", "realise"), ("realized", "realised"), ("realizing", "realising"),
    ("recognize", "recognise"), ("recognized", "recognised"), ("recognizing", "recognising"),
    ("center", "centre"), ("centers", "centres"), ("theater", "theatre"),
    ("gray", "grey"), ("traveling", "travelling"), ("traveled", "travelled"),
    ("defense", "defence"), ("license", "licence"), ("licenses", "licences"),
]
AMERICAN_SPELLINGS = [(target, source) for source, target in BRITISH_SPELLINGS]

BRITISH_VOCABULARY = [
    ("apartment", "flat"), ("elevator", "lift"), ("sidewalk", "pavement"),
    ("vacation", "holiday"), ("truck", "lorry"), ("zip code", "postcode"),
]
AMERICAN_VOCABULARY = [
    ("flat", "apartment"), ("lift", "elevator"), ("pavement", "sidewalk"),
    ("holiday", "vacation"), ("lorry", "truck"), ("postcode", "zip code"),
]

COMMON_REPHRASING = [
    ("at this point in time", "now"),
    ("due to the fact that", "because"),
    ("for the purpose of", "for"),
    ("in the event that", "if"),
    ("in order to", "to"),
    ("make a decision", "decide"),
    ("give consideration to", "consider"),
    ("in spite of the fact that", "although"),
]

PIDGIN_PHRASES = [
    ("how are you", "how you dey"),
    ("what is happening", "wetin dey happen"),
    ("what's happening", "wetin dey happen"),
    ("i am fine", "i dey fine"),
    ("i'm fine", "i dey fine"),
    ("i do not understand", "i no understand"),
    ("i don't understand", "i no understand"),
    ("i want to go home", "i wan go house"),
    ("i am going", "i dey go"),
    ("i'm going", "i dey go"),
    ("do not worry", "no worry"),
    ("don't worry", "no worry"),
    ("please", "abeg"),
    ("very much", "well well"),
]


def tone_rewrite(text: str, tone: str) -> str:
    if tone == "casual":
        text = replace_phrases(text, [
            ("I would like to", "I'd like to"), ("do not", "don't"),
            ("cannot", "can't"), ("it is", "it's"), ("I am", "I'm"),
            ("we are", "we're"), ("they are", "they're"),
        ])
    elif tone == "professional":
        text = replace_phrases(text, [
            ("hey", "Hello"), ("wanna", "want to"), ("gonna", "going to"),
            ("gotta", "have to"), ("thanks", "Thank you"),
        ])
    elif tone == "academic":
        text = replace_phrases(text, [
            ("kids", "children"), ("a bunch of", "several"),
            ("sort of", "somewhat"), ("kind of", "somewhat"),
            ("doesn't", "does not"), ("can't", "cannot"),
            ("won't", "will not"), ("it's", "it is"),
        ])
    elif tone == "concise":
        text = replace_phrases(text, [
            ("at this point in time", "now"), ("due to the fact that", "because"),
            ("for the purpose of", "for"), ("in the event that", "if"),
            ("in order to", "to"), ("basically", ""), ("actually", ""),
        ])
        text = re.sub(r"\s+([,.;!?])", r"\1", text)
        text = re.sub(r" {2,}", " ", text)
    return text


def rewrite_text(text: str, region: str, tone: str) -> str:
    if region == "pcm-NG":
        result = replace_phrases(text, PIDGIN_PHRASES)
    else:
        result = replace_phrases(text, COMMON_REPHRASING)
        if region in ("en-NG", "en-GB"):
            result = replace_phrases(result, BRITISH_SPELLINGS)
            if region == "en-GB":
                result = replace_phrases(result, BRITISH_VOCABULARY)
        elif region == "en-US":
            result = replace_phrases(result, AMERICAN_SPELLINGS)
            result = replace_phrases(result, AMERICAN_VOCABULARY)
        # International English deliberately keeps region-specific spellings and vocabulary.
        result = tone_rewrite(result, tone)
    result = re.sub(r"\s+([,.;!?])", r"\1", result)
    result = re.sub(r" {2,}", " ", result)
    return result.strip()


@app.get("/")
def home():
    return FileResponse("static/index.html")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/rewrite", response_model=RewriteResponse)
def rewrite(payload: RewriteRequest):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Please enter text to rewrite.")
    region = detect_region(text) if payload.region == "auto" else payload.region
    return RewriteResponse(
        rewritten_text=rewrite_text(text, region, payload.tone),
        region=region,
        region_name=REGION_NAMES[region],
        engine="built-in rules",
        notice="Runs with the rewriting rules bundled in this app. No API key or external model account is needed.",
    )
