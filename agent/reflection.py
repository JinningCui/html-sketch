import json
import re
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
import fcntl

from config import build_llm_client
from evaluate_tasks import compare_prediction, load_gold_label, normalize_gold, normalize_prediction
from task_registry import TASK_SPECS
from utils import save_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MEMORY_PATH = PROJECT_ROOT / "agent" / "reflection_memory.json"
MEMORY_LOCK_PATH = PROJECT_ROOT / "agent" / "reflection_memory.lock"
MAX_MEMORY_ENTRIES = 40
MAX_PROMPT_INSIGHTS = 12


def _load_json(path, default):
    if not Path(path).exists():
        return default
    return json.loads(Path(path).read_text())


def load_memory():
    return _load_json(MEMORY_PATH, {"buckets": {}})


def save_memory(memory):
    save_json(MEMORY_PATH, memory)


@contextmanager
def _memory_lock():
    MEMORY_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_LOCK_PATH, "a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _dedupe_entries(entries):
    seen = set()
    deduped = []
    for entry in reversed(entries):
        insights = []
        for insight in entry.get("insights", []):
            key = insight.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            insights.append(insight.strip())
        if insights:
            cloned = dict(entry)
            cloned["insights"] = insights
            deduped.append(cloned)
    deduped.reverse()
    return deduped[-MAX_MEMORY_ENTRIES:]


def _get_bucket(memory, task_name):
    buckets = memory.setdefault("buckets", {})
    return buckets.setdefault(task_name, {"entries": []})


def build_memory_prompt(task_name=None):
    memory = load_memory()
    if not task_name:
        return ""

    entries = memory.get("buckets", {}).get(task_name, {}).get("entries", [])
    if not entries:
        return ""

    selected = entries[-MAX_PROMPT_INSIGHTS:]

    lines = []
    for entry in selected:
        outcome = entry.get("outcome", "unknown")
        source_task = entry.get("task_name", "unknown")
        for insight in entry.get("insights", []):
            lines.append(f"- [{source_task}/{outcome}] {insight}")

    if not lines:
        return ""

    return (
        "\n\nCross-task reflection memory. Use these as soft heuristics, not as fixed rules:\n"
        + "\n".join(lines)
    )


def build_reflection_system_prompt():
    return (
        "You are extracting compact, generalizable reasoning improvements from a solved task. "
        "Only keep insights that are reusable across future tasks. "
        "Do not store task-specific answers, raw numbers, IDs, or long chain-of-thought. "
        "Return strict JSON only."
    )


def build_reflection_user_prompt(task_name, outcome, gold, prediction, final_answer, structured_trace):
    turns = structured_trace.get("turns", [])[-4:]
    compact_turns = []
    for turn in turns:
        compact_turns.append(
            {
                "reflection": (turn.get("reflection") or {}).get("text"),
                "thought": (turn.get("thought") or {}).get("text"),
                "action": (turn.get("action") or {}).get("text"),
                "observation": turn.get("observation"),
                "answer": turn.get("answer"),
            }
        )

    payload = {
        "task_name": task_name,
        "outcome": outcome,
        "gold": gold,
        "prediction": prediction,
        "final_answer": final_answer,
        "recent_turns": compact_turns,
    }
    return (
        "Analyze this result and extract 0-3 reusable insights that could improve future tasks.\n"
        "Prefer short operational rules like 'for X, verify Y before answering'.\n"
        "If the run was wrong, focus on the mistake pattern and the future safeguard.\n"
        "Return JSON with keys: should_store (bool), insights (list[str]), notes (str).\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def _extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Reflection response did not contain JSON.")
    return json.loads(text[start : end + 1])


def reflect_and_update_memory(task_name, task_input, structured_trace, output_dir, llm_client=None):
    final_answer = structured_trace.get("final_answer")
    if not final_answer:
        return None

    if task_name in TASK_SPECS:
        gold_raw = load_gold_label(task_name, Path(task_input))
        gold = normalize_gold(task_name, gold_raw)
        prediction = normalize_prediction(task_name, final_answer)
        correct = compare_prediction(task_name, prediction, gold)
        outcome = "correct" if correct else "incorrect"
    else:
        gold = None
        prediction = final_answer
        outcome = "unknown"

    client = llm_client or build_llm_client()
    response = client.create(
        messages=[
            {"role": "system", "content": build_reflection_system_prompt()},
            {
                "role": "user",
                "content": build_reflection_user_prompt(
                    task_name=task_name,
                    outcome=outcome,
                    gold=gold,
                    prediction=prediction,
                    final_answer=final_answer,
                    structured_trace=structured_trace,
                ),
            },
        ],
    )
    reflection_text, _ = client.extract_text_or_completion_object(response)
    reflection_text = reflection_text or "{}"
    reflection = _extract_json(reflection_text)
    reflection_record = {
        "task_name": task_name,
        "task_input": str(task_input),
        "gold": gold,
        "prediction": prediction,
        "outcome": outcome,
        "final_answer": final_answer,
        "should_store": bool(reflection.get("should_store")),
        "insights": [item.strip() for item in reflection.get("insights", []) if str(item).strip()],
        "notes": reflection.get("notes", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    save_json(Path(output_dir) / "reflection.json", reflection_record)

    if reflection_record["should_store"] and reflection_record["insights"]:
        with _memory_lock():
            memory = load_memory()
            bucket = _get_bucket(memory, task_name)
            bucket.setdefault("entries", []).append(reflection_record)
            bucket["entries"] = _dedupe_entries(bucket["entries"])
            save_memory(memory)

    return reflection_record
