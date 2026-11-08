# Say It Naturally — Regional English Rewriter

A self-contained web app for rewriting text in Nigerian English, British English, International English, American English, or Nigerian Pidgin. It offers three selectable dictionary-assisted versions, tone controls, regional spelling and vocabulary, and an optional writing-style estimate.

## Built-in engine and its limits

All rewriting rules and synonym choices are bundled in `dictionary.json` and `app.py`. The app needs no API key, external model account, or remote inference. It creates three alternatives by changing a small number of phrase or word choices so the text remains readable. English word meanings depend on context, so review the alternatives and choose the one that preserves your intent. This curated offline dictionary is not a complete dictionary of every English word and is not equivalent to a generative AI model.

The AI text detector is a local style-pattern heuristic. Its red-yellow-green scale is only a rough indicator and cannot reliably identify AI authorship or prove who wrote a text. Short inputs under 25 words are not scored.

## Run locally

Requires Python 3.10 or newer and Node.js/npm if you want to use the npm shortcut.

```bash
npm start
```

`npm start` creates a local `.venv` and installs the Python server dependencies the first time, then starts the app at <http://localhost:10000>. Stop with Ctrl+C. Alternatively, start it manually:

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app:app --reload
```

The health endpoint is `/health`.

## Deploy on Render

1. Unzip the project and push the folder to a Git repository you control.
2. In Render, choose **New + → Blueprint**, then connect that repository. Render reads `render.yaml` and creates the web service.
3. Deploy. No API key or extra environment variable is needed. The health check uses `/health`.

Render uses the Python commands in `render.yaml`; `npm start` is a local convenience shortcut. To create a Render web service manually, use build command `pip install -r requirements.txt` and start command `uvicorn app:app --host 0.0.0.0 --port $PORT`.

## Features

- Three selectable rewrite options per request
- Bundled common-phrase and synonym dictionary
- Regional selector: auto-detect, Nigerian English, British English, International English, American English, and separate Nigerian Pidgin mode
- Tone options: keep my tone, conversational, professional, academic, and concise
- Live red-yellow-green style-pattern estimate, clearly marked as non-determinative
- Input limit: 5,000 characters
- No model API key, API account, or remote inference dependency

## Files

- `app.py` — FastAPI server, bundled rewrite/detection logic, and health endpoint
- `dictionary.json` — offline phrase and synonym choices
- `static/` — browser interface, stylesheet, and browser logic
- `package.json` — optional `npm start` shortcut
- `render.yaml` — Render Blueprint
- `Dockerfile` — portable container build
- `requirements.txt` — web-server dependencies only

## API

`POST /api/rewrite`

```json
{
  "text": "I think this is a good idea because it can help people.",
  "region": "en-GB",
  "tone": "professional"
}
```

Returns `options` (three labelled alternatives) and `rewritten_text` (the first choice for compatibility). `POST /api/detect` accepts `{"text":"..."}` and returns the style-indicator band, estimate and caveat. Regions: `auto`, `en-NG`, `en-GB`, `en-INT`, `en-US`, `pcm-NG`. Tones: `keep`, `casual`, `professional`, `academic`, `concise`.
