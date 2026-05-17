# Colab Runbook — How to run SuccessApp's notebooks reliably

## TL;DR

You have **three notebooks**. Each one is **fully independent** — you can run them in fresh Colab runtimes, in any order, no cross-notebook state required.

| # | Notebook | What it does | Time on T4 | Output |
|---|----------|--------------|-----------|--------|
| 1 | `01_triage_and_tools.ipynb` | Phase 1 (triage) + Phase 2 (function calling). Loads Gemma 4, runs the 20-case eval, simulates a full multi-turn session with goal-graph + journal + reminder, visualises the goal graph. | ~12 min | Eval score, sample goal graph PNG |
| 2 | `02_multimodal.ipynb` | Phase 3 (photo journal). Reloads model with vision head, runs on a sample image, demonstrates JSON output. | ~10 min | Sample journal JSON from a photo |
| 3 | `03_quantize.ipynb` | Phase 5 (export). Converts Gemma 4 to MediaPipe `.task` int4 for the Android app. | ~25 min | Downloadable `gemma-4-e2b-it-int4.task` (~3 GB) |

There is **no shared kernel requirement**. Each notebook re-downloads / re-loads the model. Yes, that's redundant, but it's bulletproof.

---

## Pre-flight checklist (do once)

### 1. Kaggle account setup
- [ ] Joined the [Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon) (click "Join Competition" — required for eligibility)
- [ ] Accepted Gemma 4 license at https://www.kaggle.com/models/google/gemma-4
- [ ] Created a fresh API token: Kaggle → Settings → API → "Create New Token" (downloads `kaggle.json`)

### 2. Upload repo files to Colab
The notebooks reference three files that live outside the notebook itself:

| File needed by | File path in your repo |
|----------------|------------------------|
| Notebook 1 (eval) | `eval/triage_testcases.jsonl` |
| Notebook 1 (tools) | `prompts/tool_schemas.json` |
| Notebook 1 (extended eval, optional) | `eval/triage_testcases_extended.jsonl` |

**Two ways to make them available in Colab — pick one:**

**Option A — Manual upload (simplest, must repeat each session)**
- In Colab, click the 📁 **Files** icon (left sidebar) → 📤 Upload
- Drag the 2-3 files in. They land in `/content/`.

**Option B — Mount Google Drive (do once, then automatic)**
- Copy the whole `Kaggle competition Gemma 4/` folder into your Google Drive (e.g. `/My Drive/successapp/`).
- In the first cell of each notebook, add:
  ```python
  from google.colab import drive
  drive.mount('/content/drive')
  %cd /content/drive/MyDrive/successapp
  ```
- Now every relative path (`eval/...`, `prompts/...`) just works.

**Option C (best for serious iteration) — Clone from GitHub**
- Push your repo to GitHub, then in the first cell:
  ```python
  !git clone https://github.com/<your-handle>/successapp.git
  %cd successapp
  ```

### 3. Add Colab Secrets (one-time)
In Colab's left sidebar, click 🔑 **Secrets**. Add two secrets with these **exact names**:

| Secret name | Value | Notebook-access toggle |
|-------------|-------|-----------------------|
| `KAGGLE_USERNAME` | your Kaggle username | ON for all 3 notebooks |
| `KAGGLE_KEY` | the `key` value from your `kaggle.json` | ON for all 3 notebooks |

> ⚠️ **Common mistake (you hit this before):** Pass the *name* `'KAGGLE_USERNAME'` to `userdata.get()`, **not the value**. The code in the notebook already does this correctly — don't edit it.

### 4. Pick the right runtime
For each notebook:
- **Runtime → Change runtime type → T4 GPU** (free tier is fine for all three)
- Save & connect.

---

## Run Notebook 1 — `01_triage_and_tools.ipynb` (~12 min)

This is the **most important** notebook. The eval output here determines whether the prompt is safe enough to ship.

### Steps
1. Open `01_triage_and_tools.ipynb` in Colab.
2. **Files in /content/ before you start:** `triage_testcases.jsonl`, `tool_schemas.json`. Upload them if you went with Option A.
3. Click **Runtime → Run all** (Ctrl-F9).
4. Wait. Watch for the eval output near the bottom.

### What to verify
- Cell 7 prints `Model files at: /root/.cache/kagglehub/...` (download succeeded).
- Cell 9 prints `Loaded on cuda:0 | VRAM: ~10 GB`.
- Cell 15 (sanity triage) prints valid JSON.
- Cell 17 (eval harness) prints `=== X/20 passed ===`. **You want X ≥ 16 and all 5 crisis cases as PASS.**
- The full multi-turn scenario in the function-calling section emits at least one `create_goal_graph` and `save_journal_entry`.
- Last cell renders a goal graph plot.

### What to paste back to me
- Copy the eval harness output (the `[PASS]`/`[FAIL]` block + final tally).
- Copy the function-calling demo output (the chat dialogue + tool-call printouts).

### If something goes wrong
| Symptom | Fix |
|---------|-----|
| `SecretNotFoundError` | Open Colab Secrets, double-check both `KAGGLE_USERNAME` and `KAGGLE_KEY` exist and notebook access is ON |
| `403 Forbidden` on model download | You haven't accepted the Gemma 4 license — open the model page and click Accept |
| `OutOfMemoryError` | Runtime → Disconnect and delete → reconnect with T4 (free tier sometimes downgrades you to CPU) |
| Eval file not found | Upload `triage_testcases.jsonl` into `/content/` (the 📁 Files panel), or fix `EVAL_PATH` in the cell |
| Crisis test fails (4/5 instead of 5/5) | Tell me which case failed; we iterate the system prompt — don't move to Notebook 2 until this is 5/5 |

---

## Run Notebook 2 — `02_multimodal.ipynb` (~10 min)

This validates that the same Gemma 4 model can read images.

### Steps
1. Open `02_multimodal.ipynb`. **You can start a new runtime — no state from Notebook 1 needed.**
2. Run all cells.
3. The default sample image is a public Unsplash mountain — runs without uploads.

### What to verify
- Cell 5 prints the JSON-parsed photo journal output.
- The `summary`, `mood_score`, `key_themes` fields look sensible for a mountain landscape.

### Try your own photos
Uncomment the "Option A" cell. Run `upload_image_interactive()`. Pick a photo of:
- A handwritten note (should set `detected_text`)
- A workout / meal (mood-based `key_themes`)
- A screenshot of a message (emotional-tone summary)

If any of these crash or hallucinate text it cannot actually read, tell me which image and the output.

---

## Run Notebook 3 — `03_quantize.ipynb` (~25 min)

This produces the file the Flutter app needs. Save this for after Notebooks 1+2 look good.

### Steps
1. Open `03_quantize.ipynb` in a fresh runtime.
2. **Watch the runtime memory** — quantization is disk-heavy (~30 GB peak intermediate). If you fill the disk, restart.
3. Run all cells.
4. The last cell downloads `gemma-4-e2b-it-int4.task` (~3 GB) to your laptop via the browser.

### What to verify
- Step 2 finishes without `KeyError` on the converter config. **This is the biggest risk** — MediaPipe's Gemma 4 support may not be released yet. If it fails, follow the CLI fallback in the Step 2 markdown.
- Step 3 smoke test prints a coherent sentence.
- `gemma-4-e2b-it-int4.task` lands in your Downloads folder.

### If quantization fails
1. Re-read the Step 2 markdown — there's a CLI fallback.
2. If both API and CLI fail with "unknown model_type GEMMA_4" or similar, MediaPipe doesn't support Gemma 4 yet. Two options:
   - Wait 2-3 days for Google to publish an example (likely, given they sponsored the hackathon)
   - Fall back to Gemma 3 E2B for the on-device build. The Colab notebooks 1 and 2 would still showcase Gemma 4 — only the phone uses Gemma 3. Document this trade-off honestly in the writeup.

---

## Time-saving tricks (optional)

### Cache the model in Google Drive
The 10 GB model download is the bottleneck. Cache it once:
```python
from google.colab import drive
drive.mount('/content/drive')
import os
os.environ['KAGGLEHUB_CACHE'] = '/content/drive/MyDrive/kagglehub_cache'
import kagglehub
MODEL_PATH = kagglehub.model_download('google/gemma-4/transformers/gemma-4-e2b-it')
```
After the first run, every subsequent notebook + session loads in ~30 seconds instead of 5 minutes.

### Reuse a single Colab runtime for Notebooks 1 and 2
1. Run Notebook 1 all the way through.
2. In Colab top bar: **File → Open notebook → Upload → pick 02_multimodal.ipynb**.
3. Then **Runtime → Manage sessions → Connect to existing → pick your running session**.
4. Notebook 2's first cell deletes the old model and reloads with the multimodal head — this is intentional, so you'll re-pay the load cost once. But you skip the Kaggle re-download because the cache persists in the same runtime.

### Disconnect aggressively
Colab free tier kicks you off after ~12h *total* or ~30-90 min of inactivity. After finishing a notebook, **Runtime → Disconnect and delete runtime** to free your quota for later sessions.

---

## What "done" looks like for the Colab phase

- [ ] Notebook 1 ran end-to-end. Eval score ≥ 16/20, crisis recall 5/5.
- [ ] Notebook 2 produced a valid JSON for the default image AND for one of your own.
- [ ] Notebook 3 produced `gemma-4-e2b-it-int4.task` on your laptop.

After all three, you're done with Colab. The rest of the build (Flutter, APK, demo video) happens on your laptop and phone.
