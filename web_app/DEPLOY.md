# Deploy SuccessApp to Hugging Face Spaces

End-to-end deploy. ~10 minutes if everything is in order.

## Prerequisites
- Hugging Face account (free): https://huggingface.co/join
- Google AI Studio API key: https://aistudio.google.com → "Get API key" → "Create API key"

## Step 1 — Create the Space

1. Go to https://huggingface.co/new-space
2. **Owner:** your account
3. **Space name:** `successapp` (or anything URL-safe)
4. **License:** Apache 2.0
5. **Space SDK:** **Gradio**
6. **Space hardware:** **CPU basic — free**
7. **Visibility:** **Public** (judges need to see it)
8. Click **Create Space**

You land on an empty Space with a few starter files.

## Step 2 — Upload the four files

In the Space's **Files** tab, click **Add file → Upload files** and upload from your local `web_app/` folder:

| Upload | Rename to (on the Space) |
|--------|--------------------------|
| `app.py` | `app.py` |
| `gemma_client.py` | `gemma_client.py` |
| `prompts.py` | `prompts.py` |
| `requirements.txt` | `requirements.txt` |
| `SPACE_README.md` | **`README.md`** ← important: rename on upload |

> ⚠️ **Do NOT upload** `.env`, `.venv/`, or anything else. Especially not your local `.env` if you made one — your key is in there.

The Space's existing starter `README.md` (with frontmatter) is what you're replacing. The frontmatter in `SPACE_README.md` is what makes the Space show as Gradio + render the title/emoji/colors.

## Step 3 — Add your API key as a Space secret

This is the crucial step.

1. In your Space, go to **Settings** (gear icon, top-right)
2. Scroll down to **"Variables and secrets"**
3. Click **"New secret"**
4. **Name:** `GOOGLE_API_KEY` (exactly this string, no quotes)
5. **Value:** paste your `AIza...` key from Google AI Studio
6. Click **Save**

The Space will automatically restart. The secret is injected as an environment variable that `gemma_client.py` reads.

## Step 4 — Watch the build

Go to the **App** tab. You'll see build logs streaming. Expected sequence:
1. `Installing requirements...` (~60 sec)
2. `Running on http://0.0.0.0:7860`
3. Your app appears.

If it fails:
- **`GOOGLE_API_KEY is not set`** → the secret name is wrong or it wasn't saved
- **`ModuleNotFoundError`** → a package missing in `requirements.txt`
- **400 error from Google AI** → key is invalid or not enabled for Gemma 4

## Step 5 — Test the public URL

1. The Space URL is `https://huggingface.co/spaces/<your-handle>/successapp`
2. Open it in an **incognito window** (verify it works without your HF login)
3. Try the **Talk** tab — say "I've been overwhelmed at work."
4. Try a **crisis-flag input** — say "Everyone would be better off without me." → crisis hotlines should appear.
5. Try the **Journal** tab — upload a photo.

If all three work, you're live.

## Step 6 — Put the URL into the writeup + video

1. Copy the public Space URL
2. Paste into:
   - `README.md` (top — replace `<HF Spaces URL — added at submission>`)
   - `docs/submission_writeup.md` (top + Section 6)
   - `web_app/SPACE_README.md` (anywhere you reference the demo)
3. Use the URL in your demo video's opening shot

## Maintenance

- **Free CPU Spaces sleep after 48 hours of inactivity.** Wake by visiting the URL. Don't worry — judges visiting will wake it.
- If you hit Gemma 4 rate limits (HTTP 429), you can either wait or temporarily put a more relaxed model handle first in `gemma_client._MODEL_CANDIDATES` (e.g. `gemma-3-27b-it`).

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| "Application error: a server error has occurred" | Build crashed | Check Logs in the App tab; usually `requirements.txt` issue |
| Chat works but no goal graph renders | Planner not emitting `create_goal_graph` for the test message | This is correct behavior — try a more explicit goal-commit message like "I commit, let's plan this." |
| Crisis hotlines don't appear | Triage didn't set `crisis_flag` | Use exact phrasings from `eval/triage_testcases_extended.jsonl` to verify |
| 429 Too Many Requests | Free-tier rate limit hit | Wait a few seconds; usage resets per minute. For the demo recording, do a dry-run a few minutes earlier. |
