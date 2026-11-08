import json
import re
import statistics
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="Regional English Rewriter", version="1.2.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
with (BASE_DIR / "dictionary.json").open(encoding="utf-8") as dictionary_file:
    REPHRASE_DICTIONARY: dict[str, list[str]] = json.load(dictionary_file)
PIDGIN_DICTIONARY_KEYS = {
    "how are you", "i am fine", "i'm fine", "i do not understand",
    "i don't understand", "i want to go home", "what is happening", "what's happening",
}
ENGLISH_DICTIONARY = {key: value for key, value in REPHRASE_DICTIONARY.items() if key not in PIDGIN_DICTIONARY_KEYS}
PIDGIN_DICTIONARY = {key: REPHRASE_DICTIONARY[key] for key in PIDGIN_DICTIONARY_KEYS}

Region = Literal["auto", "en-NG", "en-GB", "en-INT", "en-US", "pcm-NG"]
Tone = Literal["keep", "casual", "professional", "academic", "concise"]
REGION_NAMES = {
    "en-NG": "Nigerian English", "en-GB": "British English",
    "en-INT": "International English", "en-US": "American English",
    "pcm-NG": "Nigerian Pidgin",
}
OPTION_LABELS = ["Natural", "Fresh wording", "Clearer phrasing"]

class RewriteRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    region: Region = "auto"
    tone: Tone = "keep"

class RewriteOption(BaseModel):
    label: str
    text: str

class RewriteResponse(BaseModel):
    rewritten_text: str
    options: list[RewriteOption]
    region: str
    region_name: str
    engine: str
    notice: str

class DetectRequest(BaseModel):
    text: str = Field(max_length=5000)

class DetectResponse(BaseModel):
    score: int | None
    band: str
    label: str
    detail: str
    word_count: int


def has_phrase(text: str, phrase: str) -> bool:
    return bool(re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text, re.IGNORECASE))


def detect_region(text: str) -> str:
    """Suggest a region only when the input contains clear regional markers."""
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
    for source, target in sorted(replacements, key=lambda pair: len(pair[0]), reverse=True):
        pattern = re.compile(r"(?<!\w)" + re.escape(source) + r"(?!\w)", re.IGNORECASE)
        text = pattern.sub(lambda match, value=target: preserve_case(match.group(0), value), text)
    return text


def dictionary_variant(text: str, variant_index: int, max_changes: int = 3, dictionary: dict[str, list[str]] | None = None) -> str:
    """Apply a small number of dictionary-backed substitutions for readable options."""
    dictionary = dictionary or ENGLISH_DICTIONARY
    replacements: list[tuple[int, int, str]] = []
    patterns = sorted(dictionary, key=len, reverse=True)
    occupied: list[tuple[int, int]] = []
    for term in patterns:
        pattern = re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)", re.IGNORECASE)
        for match in pattern.finditer(text):
            if any(match.start() < end and match.end() > start for start, end in occupied):
                continue
            choices = dictionary[term]
            if not choices:
                continue
            chosen = choices[variant_index % len(choices)]
            replacements.append((match.start(), match.end(), preserve_case(match.group(0), chosen)))
            occupied.append((match.start(), match.end()))
            if len(replacements) >= max_changes:
                break
        if len(replacements) >= max_changes:
            break
    for start, end, replacement in sorted(replacements, key=lambda item: item[0], reverse=True):
        text = text[:start] + replacement + text[end:]
    return text


BRITISH_SPELLINGS = [
    ("favorites", "favourites"), ("favorite", "favourite"), ("colors", "colours"), ("color", "colour"),
    ("organizes", "organises"), ("organized", "organised"), ("organizing", "organising"), ("organize", "organise"),
    ("realized", "realised"), ("realizing", "realising"), ("realize", "realise"),
    ("recognized", "recognised"), ("recognizing", "recognising"), ("recognize", "recognise"),
    ("centers", "centres"), ("center", "centre"), ("theater", "theatre"),
    ("gray", "grey"), ("traveling", "travelling"), ("traveled", "travelled"),
    ("defense", "defence"), ("licenses", "licences"), ("license", "licence"),
]
AMERICAN_SPELLINGS = [(target, source) for source, target in BRITISH_SPELLINGS]
BRITISH_VOCABULARY = [("apartment", "flat"), ("elevator", "lift"), ("sidewalk", "pavement"), ("vacation", "holiday"), ("truck", "lorry"), ("zip code", "postcode")]
AMERICAN_VOCABULARY = [("flat", "apartment"), ("lift", "elevator"), ("pavement", "sidewalk"), ("holiday", "vacation"), ("lorry", "truck"), ("postcode", "zip code")]
COMMON_REPHRASING = [
    ("at this point in time", "now"), ("due to the fact that", "because"),
    ("for the purpose of", "for"), ("in the event that", "if"),
    ("in order to", "to"), ("make a decision", "decide"),
    ("give consideration to", "consider"), ("in spite of the fact that", "although"),
    ("has the ability to", "can"), ("is able to", "can"),
    ("with regard to", "about"), ("on a daily basis", "daily"),
    ("prior to", "before"), ("a large number of", "many"),
]
PIDGIN_PHRASES = [
    ("how are you", "how you dey"), ("what is happening", "wetin dey happen"),
    ("what's happening", "wetin dey happen"), ("i am fine", "i dey fine"),
    ("i'm fine", "i dey fine"), ("i do not understand", "i no understand"),
    ("i don't understand", "i no understand"), ("i want to go home", "i wan go house"),
    ("i am going", "i dey go"), ("i'm going", "i dey go"),
    ("do not worry", "no worry"), ("don't worry", "no worry"),
    ("thank you very much", "thank you well well"), ("very much", "well well"),
    ("please", "abeg"),
]


def tone_rewrite(text: str, tone: str) -> str:
    if tone == "casual":
        return replace_phrases(text, [
            ("I would like to", "I'd like to"), ("do not", "don't"), ("cannot", "can't"),
            ("it is", "it's"), ("I am", "I'm"), ("we are", "we're"), ("they are", "they're"),
        ])
    if tone == "professional":
        return replace_phrases(text, [
            ("hey", "Hello"), ("wanna", "want to"), ("gonna", "going to"),
            ("gotta", "have to"), ("thanks", "Thank you"),
        ])
    if tone == "academic":
        return replace_phrases(text, [
            ("kids", "children"), ("a bunch of", "several"), ("sort of", "somewhat"),
            ("kind of", "somewhat"), ("doesn't", "does not"), ("can't", "cannot"),
            ("won't", "will not"), ("it's", "it is"),
        ])
    if tone == "concise":
        text = replace_phrases(text, [("basically", ""), ("actually", ""), ("very", "")])
    return text


def apply_region(text: str, region: str) -> str:
    if region in ("en-NG", "en-GB"):
        text = replace_phrases(text, BRITISH_SPELLINGS)
        if region == "en-GB":
            text = replace_phrases(text, BRITISH_VOCABULARY)
    elif region == "en-US":
        text = replace_phrases(text, AMERICAN_SPELLINGS)
        text = replace_phrases(text, AMERICAN_VOCABULARY)
    return text


def tidy(text: str) -> str:
    text = re.sub(r"\s+([,.;!?])", r"\1", text)
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def rewrite_options(text: str, region: str, tone: str) -> list[RewriteOption]:
    options = []
    for index, label in enumerate(OPTION_LABELS):
        if region == "pcm-NG":
            result = dictionary_variant(text, index, max_changes=3, dictionary=PIDGIN_DICTIONARY)
            result = replace_phrases(result, PIDGIN_PHRASES)
        else:
            result = dictionary_variant(text, index, max_changes=5, dictionary=ENGLISH_DICTIONARY)
            result = replace_phrases(result, COMMON_REPHRASING)
            result = tone_rewrite(result, tone)
            result = apply_region(result, region)
        options.append(RewriteOption(label=label, text=tidy(result)))
    # Preserve three options while avoiding accidental exact duplicates on short inputs.
    for idx in range(1, len(options)):
        if options[idx].text == options[idx - 1].text:
            options[idx].label = f"{options[idx].label} · similar wording"
    return options


AI_STYLE_MARKERS = [
    "in conclusion", "moreover", "furthermore", "additionally", "it is important to note",
    "plays a crucial role", "in today's world", "delve into", "comprehensive",
    "robust", "leverage", "navigate", "seamless", "landscape", "multifaceted",
    "underscore", "foster", "it is worth noting", "in summary", "first and foremost",
]
TRANSITION_WORDS = {"moreover", "furthermore", "additionally", "therefore", "consequently", "ultimately", "overall"}


def analyze_writing_style(text: str) -> dict:
    words = re.findall(r"\b[\w’'-]+\b", text.lower())
    if len(words) < 25:
        return {
            "score": None, "band": "short", "label": "Need more text",
            "detail": "Add at least 25 words for a rough style estimate. Even longer text cannot prove whether AI wrote it.",
            "word_count": len(words),
        }
    sentences = [part.strip() for part in re.split(r"[.!?]+", text) if part.strip()]
    lengths = [len(re.findall(r"\b[\w’'-]+\b", sentence)) for sentence in sentences]
    average_length = statistics.mean(lengths) if lengths else 0
    length_cv = (statistics.pstdev(lengths) / average_length) if len(lengths) > 1 and average_length else 1
    uniformity = max(0.0, min(1.0, 1.0 - length_cv))
    unique_ratio = len(set(words)) / max(1, len(words))
    repetition_signal = max(0.0, min(1.0, (0.62 - unique_ratio) / 0.25))
    marker_hits = sum(1 for marker in AI_STYLE_MARKERS if has_phrase(text, marker))
    repeated_transitions = sum(1 for word in words if word.strip(".,!?;:") in TRANSITION_WORDS)
    starts = [re.findall(r"\b[\w’'-]+\b", sentence.lower())[:1] for sentence in sentences]
    first_words = [entry[0] for entry in starts if entry]
    repeated_starts = max(0, len(first_words) - len(set(first_words)))
    score = 12 + uniformity * 22 + repetition_signal * 16 + min(marker_hits * 5, 25)
    score += min(repeated_transitions * 4, 12) + min(repeated_starts * 3, 10)
    score = int(round(max(0, min(100, score))))
    if score < 35:
        band, label = "low", "Few AI-style patterns"
    elif score < 65:
        band, label = "mixed", "Some AI-style patterns"
    else:
        band, label = "high", "Many AI-style patterns"
    return {
        "score": score, "band": band, "label": label,
        "detail": "Heuristic estimate from style patterns only—not a reliable AI detector or proof of authorship.",
        "word_count": len(words),
    }


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/rewrite", response_model=RewriteResponse)
def rewrite(payload: RewriteRequest):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Please enter text to rewrite.")
    region = detect_region(text) if payload.region == "auto" else payload.region
    options = rewrite_options(text, region, payload.tone)
    return RewriteResponse(
        rewritten_text=options[0].text,
        options=options,
        region=region,
        region_name=REGION_NAMES[region],
        engine="bundled dictionary",
        notice="Choose one of three dictionary-assisted options. Review the wording to make sure it preserves your intended meaning.",
    )

@app.post("/api/detect", response_model=DetectResponse)
def detect(payload: DetectRequest):
    return DetectResponse(**analyze_writing_style(payload.text))
