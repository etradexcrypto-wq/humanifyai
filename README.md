# Say It Naturally — Regional English Rewriter

A self-contained regional English rewriting web app. It supports Nigerian English, British English, International English, American English, and a separate Nigerian Pidgin mode, with a tone selector and conservative regional auto-detection.

## No API key required

The rewrite engine is bundled in `app.py`. It runs without an API key, external model account, or runtime call to an AI provider. It uses regional spelling and vocabulary maps, safe phrase-level rewording, and tone-specific rules. This deterministic approach is lightweight and portable, but it is not a full generative language model; it will not intelligently paraphrase every arbitrary sentence. You can add to the bundled phrase rules in `app.py` if you want more specialised rewrites.

## Run locally

Requires Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open <http://127.0.0.1:8000>. The health check is at `/health`.

## Deploy on Render

1. Unzip this folder and push it to a Git repository you control.
2. In Render, choose **New + → Blueprint**, then connect that repository. Render reads `render.yaml` and creates the web service.
3. Deploy. No secret, model selection, or extra environment variable is needed. Render checks `/health` to confirm the service is running.

You can also create a Render web service manually with build command `pip install -r requirements.txt` and start command `uvicorn app:app --host 0.0.0.0 --port $PORT`.

## Features

- Regional selector: automatic suggestion, Nigerian English, British English, International English, American English, and Nigerian Pidgin
- Tone options: keep my tone, conversational, professional, academic, and concise
- Built-in spelling and vocabulary conversions, plus common phrase simplifications
- Pidgin is an explicit separate mode; Nigerian English is not automatically converted to Pidgin
- Inputs are limited to 5,000 characters
- No model API key, API account, or remote inference dependency

## Files

- `app.py` — FastAPI server, bundled rewrite rules, region detection, and health endpoint
- `static/` — browser interface, styles, and client-side logic
- `render.yaml` — key-free Render Blueprint configuration
- `Dockerfile` — portable container build
- `requirements.txt` — web-server dependencies only

## API

`POST /api/rewrite`

```json
{
  "text": "Please rewrite this message.",
  "region": "en-GB",
  "tone": "professional"
}
```

Regions: `auto`, `en-NG`, `en-GB`, `en-INT`, `en-US`, `pcm-NG`. Tones: `keep`, `casual`, `professional`, `academic`, `concise`.
