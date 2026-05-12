import argparse
import json
import math
import re
from pathlib import Path

from task_registry import TASK_SPECS, get_outputs_root, get_tasks_root, iter_task_instances, resolve_tasks
from utils import content_to_text, extract_answer_text, save_json


def _read_json(path):
    return json.loads(Path(path).read_text())


def _load_raw_output(output_path):
    if not output_path.exists():
        return None
    return _read_json(output_path)


def _extract_final_answer(raw_output):
    if not isinstance(raw_output, list):
        return None
    for message in reversed(raw_output):
        if message.get("role") != "assistant":
            continue
        text = content_to_text(message.get("content", ""))
        answer = extract_answer_text(text)
        if answer:
            return answer
    return None


def _normalize_choice(text):
    if not text:
        return None
    match = re.search(r"\(([A-Da-d])\)|\b([A-Da-d])\b", text)
    if not match:
        return None
    return (match.group(1) or match.group(2)).upper()


def _normalize_bool(text):
    if not text:
        return None
    lower = text.lower()
    if "true" in lower or "isomorphic" in lower and "not isomorphic" not in lower:
        return True
    if "false" in lower or "not isomorphic" in lower:
        return False
    if re.search(r"\byes\b", lower):
        return True
    if re.search(r"\bno\b", lower):
        return False
    return None


def _normalize_label(text):
    if not text:
        return None
    lower = text.lower()
    for token in ["convex", "concave", "even", "odd", "neither", "white", "black", "draw"]:
        if re.search(rf"\b{re.escape(token)}\b", lower):
            return token
    return None


def _extract_number(text):
    if not text:
        return None
    matches = re.findall(r"-?\d+(?:\.\d+)?", text)
    if not matches:
        return None
    return float(matches[-1])


def _normalize_math_text(text):
    if not text:
        return ""
    text = text.lower()
    text = text.replace("\\", "")
    text = text.replace("{", "")
    text = text.replace("}", "")
    text = text.replace("(", " ").replace(")", " ")
    text = text.replace("[", " ").replace("]", " ")
    text = text.replace("^circ", " ")
    text = text.replace("circumference", " ")
    text = text.replace("approximately", " ")
    text = text.replace("rounded to the nearest tenth", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _geometry_choice_from_text(text, task_instance):
    if not text:
        return None
    ex = _read_json(Path(task_instance) / "ex.json")
    choices = ex.get("choices") or ex.get("compact_choices") or []
    normalized_answer = _normalize_math_text(text)
    if not normalized_answer:
        return None

    for idx, choice in enumerate(choices):
        normalized_choice = _normalize_math_text(str(choice))
        if normalized_choice and normalized_choice in normalized_answer:
            return "ABCD"[idx]
    return None


def _geometry_choice_from_numeric(text, task_instance):
    if not text:
        return None
    number = _extract_number(text)
    if number is None:
        return None

    ex = _read_json(Path(task_instance) / "ex.json")
    values = ex.get("precise_value") or ex.get("rough_value")
    if not values:
        return None

    best_idx = None
    best_delta = None
    for idx, value in enumerate(values):
        try:
            delta = abs(float(number) - float(value))
        except Exception:
            continue
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best_idx = idx

    if best_idx is None:
        return None

    # Geometry options are A/B/C/D in order. Reject wildly mismatched numbers.
    tolerance = max(0.25, abs(float(values[best_idx])) * 0.03)
    if best_delta is not None and best_delta <= tolerance:
        return "ABCD"[best_idx]
    return None


def normalize_prediction(task_name, final_answer, task_instance=None):
    if task_name in {"geometry", "blink_depth", "blink_jigsaw", "blink_spatial", "mmvp"}:
        choice = _normalize_choice(final_answer)
        if choice is not None:
            return choice
        if task_name == "geometry" and task_instance is not None:
            text_choice = _geometry_choice_from_text(final_answer, task_instance)
            if text_choice is not None:
                return text_choice
            return _geometry_choice_from_numeric(final_answer, task_instance)
        return None
    if task_name in {"graph_connectivity", "graph_isomorphism"}:
        return _normalize_bool(final_answer)
    if task_name == "graph_maxflow":
        return _extract_number(final_answer)
    if task_name in {"math_convexity", "math_parity", "winner_id"}:
        return _normalize_label(final_answer)
    return final_answer


def normalize_gold(task_name, gold):
    if task_name in {"geometry", "blink_depth", "blink_jigsaw", "blink_spatial", "mmvp"}:
        return str(gold).strip().replace("(", "").replace(")", "").upper()
    if task_name in {"graph_connectivity", "graph_isomorphism"}:
        return bool(gold)
    if task_name == "graph_maxflow":
        return float(gold)
    if task_name in {"math_convexity", "math_parity", "winner_id"}:
        return str(gold).strip().lower()
    return gold


def compare_prediction(task_name, pred, gold):
    if pred is None:
        return False
    if task_name == "graph_maxflow":
        return math.isclose(float(pred), float(gold), rel_tol=0.0, abs_tol=1e-6)
    return pred == gold


def load_gold_label(task_name, task_instance):
    spec = TASK_SPECS[task_name]
    data = _read_json(task_instance / spec["input_file"])
    return data[spec["label_key"]]


def evaluate_task(task_name, outputs_root=None, project_root=None):
    outputs_root = Path(outputs_root) if outputs_root else get_outputs_root(project_root)
    task_output_root = outputs_root / task_name

    rows = []
    for task_instance in iter_task_instances(task_name, project_root):
        gold = normalize_gold(task_name, load_gold_label(task_name, task_instance))
        output_path = task_output_root / task_instance.name / "output.json"
        raw_output = _load_raw_output(output_path)
        final_answer = _extract_final_answer(raw_output)
        pred = normalize_prediction(task_name, final_answer, task_instance=task_instance)
        correct = compare_prediction(task_name, pred, gold)
        rows.append(
            {
                "task": task_name,
                "instance": task_instance.name,
                "gold": gold,
                "final_answer": final_answer,
                "prediction": pred,
                "correct": correct,
                "has_output": raw_output is not None,
            }
        )

    total = len(rows)
    answered = sum(1 for row in rows if row["has_output"])
    parsed = sum(1 for row in rows if row["prediction"] is not None)
    correct = sum(1 for row in rows if row["correct"])
    correct_instances = [row["instance"] for row in rows if row["correct"]]
    return {
        "task": task_name,
        "total": total,
        "answered": answered,
        "parsed": parsed,
        "correct": correct,
        "correct_instances": correct_instances,
        "accuracy": (correct / total) if total else 0.0,
        "rows": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", nargs="+", default=["all"])
    parser.add_argument("--outputs-dir", type=str, default=str(get_outputs_root()))
    parser.add_argument("--report-dir", type=str, default=None)
    args = parser.parse_args()

    task_names = resolve_tasks(args.task)
    results = [evaluate_task(task_name, args.outputs_dir) for task_name in task_names]
    summary_tasks = []
    correct_task_lists = {}
    for result in results:
        compact = {key: value for key, value in result.items() if key != "rows"}
        summary_tasks.append(compact)
        correct_task_lists[result["task"]] = result["correct_instances"]
    summary = {"tasks": summary_tasks}

    report_dir = Path(args.report_dir) if args.report_dir else Path(args.outputs_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    save_json(report_dir / "evaluation_summary.json", summary)
    save_json(report_dir / "evaluation_details.json", results)
    save_json(report_dir / "correct_task_lists.json", correct_task_lists)

    for item in summary["tasks"]:
        print(
            f"{item['task']}: accuracy={item['accuracy']:.4f} "
            f"correct={item['correct']}/{item['total']} answered={item['answered']}"
        )


if __name__ == "__main__":
    main()
