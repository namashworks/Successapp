# SuccessApp — 90-second demo video script (web version)

## Pre-recording checklist
- [ ] Live HF Spaces URL is up and tested
- [ ] Browser zoom set to ~110% so text is readable in 1080p
- [ ] Tabs / bookmarks bar hidden — use a clean browser profile or full-screen
- [ ] Screen recorder ready (OBS, Loom, or built-in Windows Game Bar Win+G)
- [ ] Headphones plugged in for clean voiceover
- [ ] Have a handwritten note photo ready on disk for the journal demo
- [ ] Quiet room, no notification sounds

## Total: 90 seconds, six scenes

---

### 0:00 – 0:07 — Hook (no screen, your face only)

> "One in five adults will need help this year. Most won't use a chatbot because they don't want their darkest moments in someone's database. So we built one that doesn't keep any."

---

### 0:07 – 0:18 — Open the app, show the privacy posture

- Screen-record the browser. Navigate to the HF Spaces URL.
- Land on the Talk tab. Read the intro line on screen out loud.

> "SuccessApp. Powered by Gemma 4. Nothing is stored on any server — the session lives in the browser tab. Close it, it's gone. If you mention a crisis, it surfaces real hotlines."

- Show the **green eval badge** at the top: *"100% crisis recall on 10 adversarial cases."*

---

### 0:18 – 0:34 — Normal triage + goal commit

- Type: **"I've been overwhelmed at work and I want to pivot to product management within 6 months."**
- Show: empathetic acknowledgment, follow-up question.
- Briefly open the **"What the model decided"** accordion — point at `category=stress, goal_hint=pivot to PM in 6 months`.
- Type a second message: **"Yes — let's do this. I commit."**
- Tab over to **Goals** — show the auto-generated graph.

> "Two passes of Gemma 4 per turn. First listens and triages. Second decides whether to act — like scaffolding a goal into a milestone graph. The first turn is just listening — only when the user commits does it create the plan."

---

### 0:34 – 0:50 — Multimodal photo journal

- Tab over to **Journal**.
- Click the camera input, upload the handwritten journal page.
- Add caption: **"Tough week — just being honest with myself."**
- Click "Journal this photo".
- Show the structured result: summary, detected text, mood score, themes.

> "The same Gemma 4 model is multimodal. It reads your handwritten page — verbatim — scores your mood, picks out themes. It's not just OCR. It connects the image to your goals."

---

### 0:50 – 1:08 — The crisis path (the most important scene)

- Tab back to **Talk**. Start a fresh session (click "Start a new session").
- Type: **"Sometimes I feel like everyone would be better off without me."**
- The crisis screen appears inline: hotlines for US, UK, India, global directory, plus a breathing exercise.
- Pause for 2 full seconds on the hotline list.

> "When the model hears something serious, it doesn't try to be a therapist. The planner is hard-fenced — on a crisis turn the only action it's allowed to take is surfacing real human help. No advice. No reasoning. Just hotlines and a breath."

---

### 1:08 – 1:20 — Eval + closing

- Optional: open About tab, show the eval table briefly.

> "We tested this against 35 cases including jailbreak attempts, fake-authority claims, joke-disguised crisis. All 10 critical-safety cases pass. Zero medical-advice leaks. The eval set is in the GitHub repo. Open. Auditable."

- Cut back to your face for the close.

> "SuccessApp. Built with Gemma 4 for the people who never asked to be a data point."

---

## End card (3 sec, on-screen text only)

```
SuccessApp · Gemma 4 Good Hackathon · Health track
Live: <hf-spaces-url>
Code: <github-url>
<your name>
```

---

## Editing notes
- Use subtitles throughout — many judges watch muted in their feed
- Keep cuts tight — under 90 seconds is critical
- Pause an extra beat on the **crisis screen frame** — that's the moment that wins or loses
- Color-grade for warmth (not clinical / sterile)
- Music: optional, low ambient. Avoid dramatic.
- Export 1080p, upload to YouTube **unlisted**, share the link in the Kaggle writeup

## Common mistakes to avoid
- Don't show your real Google API key on screen — if you open the URL bar or any settings, mute that frame
- Don't say "powered by AI" — say "powered by Gemma 4"
- Don't promise medical help — the app is a companion, not a clinician
- Don't fake the crisis trigger by typing the exact word "suicide" — use a real-feeling phrase like "everyone would be better off without me." That's more credible and matches the eval set.
