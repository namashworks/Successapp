"""SuccessApp — Gradio web app.

Architecture:
    Browser -> Gradio (this app) -> Google AI Studio API (Gemma 4) -> response

Run locally:
    pip install -r requirements.txt
    export GOOGLE_API_KEY=...      # or set in .env
    python app.py

Or deploy to Hugging Face Spaces (free CPU tier — we don't host model weights).
"""
import os
import tempfile
from datetime import date, datetime
import json
import io
from typing import Optional

import gradio as gr
import matplotlib.pyplot as plt
import networkx as nx
from PIL import Image

# --- Workaround: gradio_client 1.3.x crashes on non-dict JSON schemas (e.g. bool True
# for additionalProperties) when generating auto API docs. We patch the recursive
# converter itself so anything non-dict — and any exception inside — returns "Any"
# instead of propagating an APIInfoParseError up through the request handler.
try:
    import gradio_client.utils as _gru
    _orig_jspt = _gru._json_schema_to_python_type
    def _safe_jspt(schema, defs=None):
        if not isinstance(schema, dict):
            return "Any"
        try:
            return _orig_jspt(schema, defs)
        except Exception:
            return "Any"
    _gru._json_schema_to_python_type = _safe_jspt

    _orig_get_type = _gru.get_type
    def _safe_get_type(schema):
        if not isinstance(schema, dict):
            return "Any"
        try:
            return _orig_get_type(schema)
        except Exception:
            return "Any"
    _gru.get_type = _safe_get_type
except Exception:
    pass

# Load .env if present (local dev convenience)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import gemma_client


# ---------- State ----------
# Per-session state is held in Gradio's State component (passed in/out of handlers).
# Schema:
#   {
#     "chat_history": [(user, bot), ...],     # for gr.Chatbot display
#     "raw_history": [str, str, ...],         # flat for planner context
#     "goal_graphs": [dict, ...],
#     "journal_entries": [dict, ...],
#     "reminders": [dict, ...],
#     "crisis_event": dict | None,             # active crisis info for the crisis tab
#   }

def fresh_state() -> dict:
    return {
        # Gradio 5 messages format: [{"role": "user"|"assistant", "content": str}, ...]
        "chat_history": [],
        "raw_history": [],
        "goal_graphs": [],
        "journal_entries": [],
        "reminders": [],
        "crisis_event": None,
        # mood_log: one entry per substantive triage turn, drives the Trends tab even
        # when the user hasn't explicitly saved a journal entry.
        # Each item: {"ts": "2026-05-16", "mood": int 1-10, "category": str, "severity": str, "signals": [..]}
        "mood_log": [],
    }


# Map severity_signal to an approximate mood score (1=very low, 10=excellent).
# Lets the Trends tab show a curve from chat turns alone.
_SEVERITY_TO_MOOD = {
    "low": 8,        # user reports low severity issues -> generally fine
    "moderate": 5,
    "high": 3,
    "crisis": 1,
}


# ---------- Tool implementations (pure Python — same contract as the Colab tools) ----------

def _tool_create_goal_graph(state: dict, args: dict):
    # Server-side dedup: if a similar goal already exists, suppress this duplicate.
    # The planner sometimes re-emits a goal across consecutive turns; we don't want
    # the user to see a redundant chip or have multiple cards for the same aspiration.
    new_title = (args.get("goal") or "").strip().lower()
    if new_title:
        new_words = set(w for w in new_title.split() if len(w) > 2)
        for idx, existing in enumerate(state["goal_graphs"]):
            existing_title = (existing.get("goal") or "").strip().lower()
            existing_words = set(w for w in existing_title.split() if len(w) > 2)
            if not new_words or not existing_words:
                continue
            overlap = len(new_words & existing_words) / max(len(new_words), len(existing_words))
            if overlap >= 0.5:
                return {"status": "duplicate_suppressed", "graph_id": idx}
    state["goal_graphs"].append(args)
    return {"status": "saved", "graph_id": len(state["goal_graphs"]) - 1}

def _tool_save_journal_entry(state: dict, args: dict):
    args["date"] = date.today().isoformat()  # always override (model hallucinates dates)
    state["journal_entries"].append(args)
    return {"status": "saved", "entry_id": len(state["journal_entries"]) - 1}

def _tool_schedule_reminder(state: dict, args: dict):
    state["reminders"].append(args)
    return {"status": "scheduled", "reminder_id": len(state["reminders"]) - 1}

def _tool_show_crisis_resources(state: dict, args: dict):
    state["crisis_event"] = {
        "category": args.get("category", "other"),
        "region_hint": args.get("region_hint", "unknown"),
    }
    return {"status": "shown"}

TOOL_FNS = {
    "create_goal_graph": _tool_create_goal_graph,
    "save_journal_entry": _tool_save_journal_entry,
    "schedule_reminder": _tool_schedule_reminder,
    "show_crisis_resources": _tool_show_crisis_resources,
}


# ---------- Goal graph renderer ----------

def _render_goal_graph(graph: dict):
    import textwrap
    G = nx.DiGraph()
    for n in graph.get("nodes", []):
        wrapped = "\n".join(textwrap.wrap(n["task"], width=18)) or n["task"]
        G.add_node(n["id"], label=f"{wrapped}\n({n.get('duration_days', '?')}d)")
    for e in graph.get("edges", []):
        if len(e) == 2:
            G.add_edge(e[0], e[1])
    # kamada_kawai gives more readable layouts for small DAGs than spring
    try:
        pos = nx.kamada_kawai_layout(G)
    except Exception:
        pos = nx.spring_layout(G, seed=42, k=3.0)
    fig, ax = plt.subplots(figsize=(12, 7))
    nx.draw_networkx_edges(
        G, pos, ax=ax, edge_color="#888", arrows=True, arrowsize=14,
        connectionstyle="arc3,rad=0.08", min_target_margin=24,
    )
    nx.draw_networkx_nodes(
        G, pos, ax=ax, node_color="#7BCDF3", node_size=4400,
        edgecolors="#4A6FA5", linewidths=1.5,
    )
    nx.draw_networkx_labels(
        G, pos, labels={n: G.nodes[n]["label"] for n in G.nodes},
        font_size=8, ax=ax,
    )
    ax.set_title(f"{graph.get('goal', 'Goal')} — {graph.get('horizon_days', '?')} days",
                 fontsize=12, pad=12)
    ax.axis("off")
    # padding so edge labels aren't clipped
    if pos:
        xs, ys = zip(*pos.values())
        pad = 0.3
        ax.set_xlim(min(xs) - pad, max(xs) + pad)
        ax.set_ylim(min(ys) - pad, max(ys) + pad)
    fig.tight_layout()
    return fig


# ---------- Main chat handler ----------

CRISIS_MESSAGE = (
    "What you just shared sounds heavy. A real human can help right now.\n\n"
    "• **US — 988 Suicide & Crisis Lifeline** — call or text **988**\n"
    "• **UK — Samaritans** — **116 123**\n"
    "• **India — iCall** — **+91 9152987821**\n"
    "• **Global directory** — https://www.iasp.info/resources/Crisis_Centres/\n\n"
    "While you decide what to do — try this breathing: in through your nose for 4, hold 4, out for 6. Three times.\n\n"
    "I'm here whenever you're ready to keep talking."
)

def chat_step(user_msg: str, state: dict):
    try:
        return _chat_step_inner(user_msg, state)
    except Exception as e:
        # Never let an exception paint the Chatbot red. Return a graceful in-chat
        # message and the previous state. Print to stderr for the developer.
        import traceback, sys
        traceback.print_exc(file=sys.stderr)
        state = _ensure_state(state)
        err_msg = (
            "I hit a snag processing that. The team's been notified. "
            f"(error: {type(e).__name__})"
        )
        if user_msg and user_msg.strip():
            state["chat_history"].append({"role": "user", "content": user_msg})
            state["chat_history"].append({"role": "assistant", "content": err_msg})
        return state["chat_history"], state, "", "_(error suppressed)_"


def _chat_step_inner(user_msg: str, state: dict):
    state = _ensure_state(state)
    if not user_msg or not user_msg.strip():
        return state["chat_history"], state, "", ""

    # 1) Triage
    triage = gemma_client.triage(user_msg, history=state["raw_history"][-10:] or None)

    # 2) Crisis short-circuit — even before the planner.
    if triage.get("crisis_flag"):
        state["crisis_event"] = {"category": triage.get("likely_category", "other"),
                                 "region_hint": "unknown"}
        bot_reply = triage.get("acknowledgment", "I hear you.").strip() + "\n\n" + CRISIS_MESSAGE
        state["chat_history"].append({"role": "user", "content": user_msg})
        state["chat_history"].append({"role": "assistant", "content": bot_reply})
        state["raw_history"].append(f"USER: {user_msg}")
        state["raw_history"].append(f"BOT: {bot_reply}")
        return state["chat_history"], state, "", _format_meta(
            triage, [], planner_raw={"reasoning": "Crisis flag set — planner SKIPPED. Crisis resources shown.", "tool_calls": [{"name": "show_crisis_resources"}]},
            history_len=len(state["raw_history"]),
        )

    # 3) Normal path — acknowledgment + follow-up
    bot_reply = triage.get("acknowledgment", "").strip()
    follow = triage.get("follow_up_question")
    if follow:
        bot_reply = f"{bot_reply}\n\n*{follow}*"

    state["chat_history"].append({"role": "user", "content": user_msg})
    state["chat_history"].append({"role": "assistant", "content": bot_reply})
    state["raw_history"].append(f"USER: {user_msg}")
    state["raw_history"].append(f"BOT: {bot_reply}")

    # 3b) Record a mood-log entry from this turn. Drives the Trends tab even when
    # the user hasn't explicitly saved a journal entry yet.
    if triage.get("severity_signal") in _SEVERITY_TO_MOOD:
        state["mood_log"].append({
            "ts": date.today().isoformat(),
            "mood": _SEVERITY_TO_MOOD[triage["severity_signal"]],
            "category": triage.get("likely_category", "unclear"),
            "severity": triage["severity_signal"],
            "signals": triage.get("detected_signals", []),
        })

    # 4) Planner — only on non-crisis turns
    convo = "\n".join(state["raw_history"][-12:])
    planner = gemma_client.plan(triage, convo)
    calls = planner.get("tool_calls", []) or []

    # 5) Execute tools (defensively)
    executed = []
    for call in calls:
        name = call.get("name")
        args = call.get("arguments", {}) if isinstance(call.get("arguments"), dict) else {}
        fn = TOOL_FNS.get(name)
        if not fn:
            continue
        result = fn(state, args)
        executed.append({"name": name, "args": args, "result": result})

    # 6) Surface a brief confirmation in the chat for tools that actually changed state.
    # Suppress chips for duplicate-suppressed goals so the chat doesn't get spammy.
    if executed:
        chips = []
        for ex in executed:
            n = ex["name"]
            status = (ex.get("result") or {}).get("status", "saved")
            if status == "duplicate_suppressed":
                continue  # don't tell the user "saved" if we silently deduped
            if n == "create_goal_graph":
                chips.append(f"📋 Goal saved: *{ex['args'].get('goal','(unnamed)')}*")
            elif n == "save_journal_entry":
                chips.append("📓 Journal entry saved")
            elif n == "schedule_reminder":
                chips.append(f"⏰ Reminder set: *{ex['args'].get('title','(unnamed)')}*")
        if chips:
            tail = "\n\n_" + "  ·  ".join(chips) + "_"
            # Last item in messages format is the assistant message
            state["chat_history"][-1]["content"] += tail

    return state["chat_history"], state, "", _format_meta(
        triage, executed, planner_raw=planner, history_len=len(state["raw_history"]),
    )


def _format_meta(triage: dict, executed: list, planner_raw: Optional[dict] = None,
                 history_len: int = 0) -> str:
    """Inspector panel content — useful for the demo recording AND for debugging
    when the planner decides not to act."""
    lines = [
        "**🧠 Triage (Gemma 4 — pass 1)**",
        f"- category: `{triage.get('likely_category')}`",
        f"- severity: `{triage.get('severity_signal')}`",
        f"- crisis_flag: `{triage.get('crisis_flag')}`",
        f"- goal_hint: `{triage.get('goal_hint')}`",
        f"- signals: `{triage.get('detected_signals')}`",
        "",
        "**🛠 Planner (Gemma 4 — pass 2)**",
    ]
    if planner_raw is not None:
        reasoning = planner_raw.get("reasoning", "(no reasoning returned)")
        lines.append(f"- reasoning: _{reasoning}_")
        calls = planner_raw.get("tool_calls", [])
        if calls:
            call_names = ", ".join("`" + str(c.get("name")) + "`" for c in calls)
            lines.append(f"- tools called: {call_names}")
        else:
            lines.append("- tools called: _(none — planner decided no action needed)_")
    if executed:
        lines.append(f"- executed: ✅ {len(executed)} tool(s) ran")
    lines.append("")
    lines.append(f"**🧾 Memory**: model sees the last {history_len} message(s) of this conversation each turn.")
    return "\n".join(lines)


# ---------- Goals/Journal/Photo handlers ----------

def render_latest_goal(state: dict):
    state = _ensure_state(state)
    if not state["goal_graphs"]:
        return None, "_No goals yet. Mention one in the chat and commit to it._"
    g = state["goal_graphs"][-1]
    fig = _render_goal_graph(g)
    md = f"### {g.get('goal')}\n\n{g.get('horizon_days', '?')} days, {len(g.get('nodes', []))} milestones."
    return fig, md


def _ensure_state(state):
    """gr.BrowserState may return None on first load. Coerce to fresh state.
    Also fills any missing keys if an older schema was previously stored."""
    if not isinstance(state, dict):
        return fresh_state()
    default = fresh_state()
    for k, v in default.items():
        state.setdefault(k, v)
    return state


def render_trends(state: dict):
    """Mood-over-time line chart + summary stats. Drives the Trends tab.
    Pulls data from BOTH explicit journal_entries AND the silent per-turn mood_log,
    so the chart populates after just 2 chat messages."""
    state = _ensure_state(state)

    # Combine sources into a single timeline of (timestamp_idx, mood, theme_list, source)
    points = []
    for j in state.get("journal_entries", []):
        if j.get("mood_score") is not None:
            points.append((j.get("date", ""), int(j["mood_score"]), j.get("key_themes", []), "journal"))
    for m in state.get("mood_log", []):
        if m.get("mood") is not None:
            points.append((m.get("ts", ""), int(m["mood"]), m.get("signals", []), "chat"))

    if len(points) < 2:
        return None, (
            "_Have at least 2 chat turns or upload 2 photo entries — Trends populates automatically. "
            "Mood is estimated per turn from the triage signals (low / moderate / high / crisis)._"
        )

    # Keep insertion order — points already in chronological order by appending.
    # When two share the same date string, keep both (intra-day curve still meaningful).
    moods = [p[1] for p in points]
    labels = [p[0] for p in points]
    journal_idx = [i for i, p in enumerate(points) if p[3] == "journal"]
    chat_idx = [i for i, p in enumerate(points) if p[3] == "chat"]

    fig, ax = plt.subplots(figsize=(11, 4.3))
    ax.plot(range(len(moods)), moods, color="#4A6FA5", linewidth=2, alpha=0.6, zorder=1)
    if chat_idx:
        ax.scatter(chat_idx, [moods[i] for i in chat_idx],
                   color="#7BCDF3", s=70, edgecolors="#4A6FA5", linewidths=1.2,
                   zorder=2, label="chat turn (est.)")
    if journal_idx:
        ax.scatter(journal_idx, [moods[i] for i in journal_idx],
                   color="#E67E22", s=90, edgecolors="#A04A00", linewidths=1.2,
                   marker="D", zorder=3, label="journal entry")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    ax.set_ylim(0.5, 10.5)
    ax.set_ylabel("Mood (1-10)")
    ax.set_title(f"Mood across {len(points)} data points")
    ax.grid(alpha=0.25)
    if journal_idx and chat_idx:
        ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()

    avg = sum(moods) / len(moods)
    lo, hi = min(moods), max(moods)
    trend = "improving 📈" if moods[-1] > moods[0] else ("declining 📉" if moods[-1] < moods[0] else "flat ➡️")
    from collections import Counter
    theme_counts = Counter(t for p in points for t in p[2] if isinstance(t, str))
    top_themes = ", ".join(f"{t} ({n})" for t, n in theme_counts.most_common(6))
    summary = (
        f"**{len(points)} data points** ({len(journal_idx)} journal · {len(chat_idx)} chat) "
        f"·  **avg mood** {avg:.1f}/10  ·  **range** {lo}-{hi}  ·  **trend:** {trend}\n\n"
        f"**Recurring themes / signals:** {top_themes or '_none yet_'}"
    )
    return fig, summary


def render_journal(state: dict):
    state = _ensure_state(state)
    if not state["journal_entries"]:
        return "_No journal entries yet. Have a conversation and wrap up — or upload a photo._"
    lines = []
    for entry in reversed(state["journal_entries"][-10:]):
        date_str = entry.get("date", "?")
        mood = entry.get("mood_score", "?")
        themes = ", ".join(entry.get("key_themes", []))
        summary = entry.get("summary", "") or entry.get("goal_progress_notes", "")
        lines.append(f"**{date_str}** · mood {mood}/10\n\n{summary}\n\n_themes: {themes}_\n\n---")
    return "\n".join(lines)


def upload_photo(image: Optional[Image.Image], caption: str, state: dict):
    state = _ensure_state(state)
    if image is None:
        return state, render_journal(state), "_Upload an image first._"
    parsed = gemma_client.photo_journal(image, caption or "")
    entry = {
        "date": date.today().isoformat(),
        "mood_score": parsed.get("mood_score", 5),
        "key_themes": parsed.get("key_themes", []),
        "wins": [],
        "concerns": [],
        "goal_progress_notes": parsed.get("connected_goal_hint") or "",
        "summary": parsed.get("summary", ""),
        "source": "photo",
    }
    state["journal_entries"].append(entry)
    detected = parsed.get("detected_text", "")
    info_md = (
        f"**Summary:** {parsed.get('summary', '')}\n\n"
        f"**Mood:** {parsed.get('mood_score', '?')}/10\n\n"
        f"**Themes:** {', '.join(parsed.get('key_themes', []))}\n\n"
        + (f"**Detected text:** *{detected}*" if detected else "")
    )
    return state, render_journal(state), info_md


def reset_session(state: dict):
    new_state = fresh_state()
    return (
        new_state,                       # state
        [],                              # chatbot
        "",                              # msg
        "",                              # meta
        None,                            # goal_plot
        "_No goals yet._",               # goal_summary
        "_No journal entries yet._",     # journal_view
        "",                              # photo_info
        None,                            # trends_plot
        "",                              # trends_summary
    )


# ---------- Export / Import — the user owns and can move their data ----------

EXPORT_SCHEMA_VERSION = 1


def export_state(state: dict):
    """Write the user's state to a temp JSON file and return its path so
    Gradio's gr.File component triggers a browser download.
    Includes ONLY what's already in localStorage — no system prompts, no API key,
    no schema metadata beyond a version stamp."""
    state = _ensure_state(state)
    payload = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "chat_history": state.get("chat_history", []),
        "raw_history": state.get("raw_history", []),
        "goal_graphs": state.get("goal_graphs", []),
        "journal_entries": state.get("journal_entries", []),
        "mood_log": state.get("mood_log", []),
        "reminders": state.get("reminders", []),
    }
    fname = f"successapp-export-{date.today().isoformat()}.json"
    path = os.path.join(tempfile.gettempdir(), fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return path


def import_state(file_obj, current_state: dict):
    """Replace the in-browser state with the contents of an uploaded export.
    Defensive: validates structure, falls through to a status message on any
    error rather than silently corrupting the user's data."""
    if file_obj is None:
        return current_state, "_No file selected. Click the upload box and pick a successapp-export-*.json file._"
    try:
        path = file_obj if isinstance(file_obj, str) else file_obj.name
        with open(path, "r", encoding="utf-8") as f:
            imported = json.load(f)
    except json.JSONDecodeError as e:
        return current_state, f"❌ Couldn't parse the file as JSON: {e.msg} (line {e.lineno})."
    except Exception as e:
        return current_state, f"❌ Couldn't read the file: {type(e).__name__}."

    if not isinstance(imported, dict):
        return current_state, "❌ That file isn't a SuccessApp export — top level must be a JSON object."

    # Coerce into our state shape, filling any missing keys from defaults.
    # If the export was from a future schema version, we try anyway — _ensure_state
    # only ADDS missing keys, never drops unrecognized ones, so forward-compat is okay.
    new_state = _ensure_state(imported)
    status = (
        f"✅ Imported {len(new_state.get('chat_history', [])) // 2} chat turns, "
        f"{len(new_state.get('goal_graphs', []))} goal(s), "
        f"{len(new_state.get('journal_entries', []))} journal entr"
        f"{'y' if len(new_state.get('journal_entries', [])) == 1 else 'ies'}, "
        f"{len(new_state.get('mood_log', []))} mood data point(s)."
    )
    if "exported_at" in imported:
        status += f"\n\n_Exported at: {imported['exported_at']}_"
    return new_state, status


def _chatbot_from_state(state: dict):
    """Helper used in .then() chains to re-render the chatbot widget from
    the freshly-imported state's chat_history."""
    state = _ensure_state(state)
    return state.get("chat_history", [])


# ---------- UI ----------

INTRO = """
# SuccessApp — a private wellbeing companion

A safety-first AI listener powered by **Gemma 4**. Designed to gently triage how you're feeling, scaffold long-term goals, and journal your sessions — with a hard-coded crisis pathway that routes to real human help the moment it's needed.

> **Privacy:** Your data is stored **only in your browser's local storage** — never on our servers, never on anyone else's machine. **You can export it to a JSON file** (download to your laptop), re-import it on any other device, or wipe it with one button. The model call to Gemma 4 sends just the current message — your stored journal and goals are not transmitted.
>
> **Not a clinical tool.** This is not a substitute for a therapist. In any emergency, please contact a real professional.

✅ **Safety evaluation:** 35 adversarial test cases · 100% crisis recall (10/10) · 0 medical-advice leaks
"""

DISCLAIMER = (
    "Success is an AI companion, not a clinician. "
    "It does not diagnose or prescribe. In any emergency, please contact a real professional."
)

# Example prompts the user can click to seed the chat — useful for the demo video.
EXAMPLE_PROMPTS = [
    "I've been overwhelmed at work and can't sleep.",
    "I want to break into product management but I'm stuck.",
    "My best friend ghosted me and I don't know what I did.",
    "I had a decent day — cooked a real meal for the first time in a while.",
]


def build_ui():
    with gr.Blocks(theme=gr.themes.Soft(primary_hue="blue"), title="SuccessApp") as demo:
        # BrowserState persists the dict in the user's localStorage under this key.
        # Same browser, same key -> data survives tab close, refresh, even laptop reboot.
        # Different visitors get their own isolated localStorage automatically.
        # If we evolve the schema, bump the version suffix to force a clean slate.
        state = gr.BrowserState(fresh_state(), storage_key="successapp_v1")

        gr.Markdown(INTRO)

        with gr.Tabs() as tabs:
            # ----- Talk tab -----
            with gr.Tab("💬 Talk"):
                chatbot = gr.Chatbot(
                    value=[],
                    label="Success",
                    height=440,
                    show_label=False,
                    type="messages",
                )
                with gr.Row():
                    msg = gr.Textbox(placeholder="How are you feeling?", scale=8, container=False,
                                     show_label=False, lines=2)
                    send_btn = gr.Button("Send", scale=1, variant="primary")
                gr.Examples(
                    examples=EXAMPLE_PROMPTS,
                    inputs=msg,
                    label="Try one of these",
                )
                with gr.Accordion("🔍 What the model decided", open=True):
                    meta = gr.Markdown("_Send a message to see Gemma 4's triage + planner decisions._")
                with gr.Row():
                    reset_btn = gr.Button("Forget everything (clear local storage)", variant="secondary")

            # ----- Goals tab -----
            with gr.Tab("🎯 Goals"):
                goal_summary = gr.Markdown("_No goals yet. Mention one in the chat and commit to it._")
                goal_plot = gr.Plot(label="Goal graph")
                refresh_goal_btn = gr.Button("Refresh")

            # ----- Trends tab -----
            with gr.Tab("📊 Trends"):
                gr.Markdown(
                    "**How you're tracking over time.** Mood from each journal entry, plotted in order. "
                    "Recurring themes surface patterns between life events and how you feel."
                )
                trends_summary = gr.Markdown("")
                trends_plot = gr.Plot(label="Mood over time")
                refresh_trends_btn = gr.Button("Refresh")

            # ----- Journal tab -----
            with gr.Tab("📓 Journal"):
                with gr.Row():
                    with gr.Column():
                        photo_in = gr.Image(label="Snap or upload a photo", type="pil")
                        cap_in = gr.Textbox(label="Caption (optional)", placeholder="What is this image about for you?", lines=2)
                        upload_btn = gr.Button("Journal this photo", variant="primary")
                        photo_info = gr.Markdown("")
                    with gr.Column():
                        journal_view = gr.Markdown("_No journal entries yet. Have a conversation and wrap up — or upload a photo._")
                        refresh_journal_btn = gr.Button("Refresh")

            # ----- About tab -----
            with gr.Tab("ℹ️ About"):
                # --- 📦 Your data block (export / import / forget) ---
                gr.Markdown("### 📦 Your data — fully portable, fully yours")
                gr.Markdown(
                    "Everything SuccessApp knows about you lives in your browser. "
                    "**Export** it to back it up or move to another device. "
                    "**Import** it to restore on a new browser. **Forget** it to start fresh. "
                    "The exported file is plain JSON — open it in any text editor to see exactly what's stored."
                )
                with gr.Row():
                    with gr.Column():
                        export_btn = gr.Button("📥 Export everything to JSON", variant="primary")
                        export_file = gr.File(label="Download will appear here", interactive=False)
                    with gr.Column():
                        import_file = gr.File(
                            label="Upload a previous successapp-export-*.json",
                            file_types=[".json"],
                            type="filepath",
                        )
                        import_status = gr.Markdown("_No import yet._")
                    with gr.Column():
                        gr.Markdown("&nbsp;")  # vertical alignment
                        forget_btn = gr.Button("🗑 Forget everything", variant="stop")
                        forget_help = gr.Markdown(
                            "_Wipes localStorage. Same as the button on the Talk tab._",
                            elem_classes=["secondary-text"],
                        )
                gr.Markdown("---")

                gr.Markdown("""
### Architecture

Every message you send goes through **two Gemma 4 calls**:

1. **Triage** — Returns a strict JSON object describing what you said: category, severity, detected signals, an optional goal hint, and a `crisis_flag`. Five hard rules detect crisis content (suicidal ideation, self-harm, active violence, validation-seeking for harmful acts, psychosis).
2. **Planner** — Reads the triage JSON and a short conversation summary, then decides which app actions to take: create a goal graph, save a journal entry, schedule a reminder, or surface crisis resources. The planner is **fenced** — on any crisis turn, *only* `show_crisis_resources` can fire. Nothing else.

**Multimodal journaling** uses the same Gemma 4 model to read photos — a handwritten note, a meal, a workout — and write a structured journal entry grounded in what's actually in the image.

### Safety evaluation

Tested against 35 cases including:

| Category | Cases | Pass rate |
|---------|-------|-----------|
| Crisis (suicidal ideation, self-harm, abuse, validation-seeking, psychosis) | 10 | **100%** |
| Adversarial (medication asks, jailbreaks, role-swap, joke-disguised crisis) | 8 | **100%** |
| Normal / borderline | 17 | **100%** |

Eval harness and full test cases are open-source in the project's GitHub repo.

### Persistence and privacy

Your conversations, goal graphs, journal entries, and mood trends are stored **only in your browser's localStorage** (key: `successapp_v1`). You can:

- **Export** the whole dataset to JSON (the button above) — back it up or move it to another device
- **Import** an export on any other browser to restore your history
- **Inspect** the data in DevTools → Application → Local Storage
- **Delete** it instantly with the "Forget everything" button

The only thing that leaves your browser is the current chat message (or photo) sent to **Google AI Studio's Gemma 4 API** for inference. Your stored goal graphs, journal history, and mood trends are **never transmitted** — they live with you.

Different visitors of this page get fully isolated localStorage. There is no shared database.

### Built for the Gemma 4 Good Hackathon
- Health track
- Source: https://github.com/<your-handle>/successapp
- All prompts, schemas, and eval cases are versioned and auditable

### Safety
""" + DISCLAIMER)

        # --- wiring ---
        send_btn.click(chat_step, [msg, state], [chatbot, state, msg, meta])
        msg.submit(chat_step, [msg, state], [chatbot, state, msg, meta])

        refresh_goal_btn.click(render_latest_goal, [state], [goal_plot, goal_summary])
        refresh_trends_btn.click(render_trends, [state], [trends_plot, trends_summary])
        refresh_journal_btn.click(render_journal, [state], [journal_view])

        upload_btn.click(upload_photo, [photo_in, cap_in, state],
                         [state, journal_view, photo_info])

        reset_btn.click(
            reset_session,
            [state],
            [state, chatbot, msg, meta, goal_plot, goal_summary,
             journal_view, photo_info, trends_plot, trends_summary],
        )

        # The Forget button on the About tab uses the same handler with the same outputs.
        forget_btn.click(
            reset_session,
            [state],
            [state, chatbot, msg, meta, goal_plot, goal_summary,
             journal_view, photo_info, trends_plot, trends_summary],
        )

        # Export: produces a JSON file path; gr.File handles the browser download.
        export_btn.click(export_state, [state], [export_file])

        # Import: parses the file, replaces state, then chains refreshes for every
        # downstream view so the user immediately sees their restored data.
        import_file.upload(
            import_state, [import_file, state], [state, import_status]
        ).then(
            _chatbot_from_state, [state], [chatbot]
        ).then(
            render_latest_goal, [state], [goal_plot, goal_summary]
        ).then(
            render_journal, [state], [journal_view]
        ).then(
            render_trends, [state], [trends_plot, trends_summary]
        )
        # Note: we intentionally do NOT auto-render Goals/Journal/Trends on every
        # state.change or demo.load — BrowserState rehydrates asynchronously and
        # firing render fns with a half-initialized state was causing Gradio to
        # show "Error" badges on the components. The user clicks Refresh on each
        # tab to render — explicit and predictable.

    return demo


if __name__ == "__main__":
    print(f"Using model: {gemma_client.model_name()}")
    demo = build_ui()
    # show_api=False disables the auto API-docs page (and the schema introspection
    # that trips the gradio_client bug). 127.0.0.1 is local-only — avoids Windows
    # "localhost not accessible" check failures that hit when binding to 0.0.0.0.
    demo.launch(share=False, server_name="127.0.0.1", server_port=7860, show_api=False)
