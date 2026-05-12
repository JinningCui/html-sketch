import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Optional

from main import run_agent
from task_registry import get_runtime_output_root


def _slugify(text: str, max_len: int = 48) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text.strip())
    text = text.strip("._")
    return (text[:max_len] or "prompt").strip("._")


def _load_prompt(args):
    if args.prompt:
        return args.prompt, {"prompt": args.prompt}

    if args.prompt_file:
        path = Path(args.prompt_file)
        text = path.read_text(encoding="utf-8").strip()
        return text, {"prompt": text, "source": str(path)}

    if args.dataset_json:
        path = Path(args.dataset_json)
        data = json.loads(path.read_text(encoding="utf-8"))
        item = data[args.item_index]
        if not isinstance(item, dict):
            prompt = str(item)
            return prompt, {"prompt": prompt, "source": str(path), "item_index": args.item_index}
        prompt = item.get("prompt") or item.get("Prompt") or item.get("query") or item.get("text")
        if not prompt:
            raise ValueError(f"Dataset item {args.item_index} does not contain prompt/Prompt/query/text.")
        payload = dict(item)
        payload["source"] = str(path)
        payload["item_index"] = args.item_index
        return prompt, payload

    raise ValueError("Provide --prompt, --prompt-file, or --dataset-json.")


def _make_task_input(project_root: Path, prompt: str, payload: dict, task_id: Optional[str]) -> Path:
    digest = hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:10]
    name = task_id or f"{_slugify(prompt)}_{digest}"
    task_dir = project_root / "html_task_inputs" / name
    task_dir.mkdir(parents=True, exist_ok=True)
    request = dict(payload)
    request.setdefault("prompt", prompt)
    request.setdefault("query", prompt)
    (task_dir / "request.json").write_text(
        json.dumps(request, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return task_dir


def main():
    parser = argparse.ArgumentParser(description="Run StruVis-style HTML visual-draft reasoning.")
    parser.add_argument("--prompt", type=str, default=None, help="Prompt to reason about.")
    parser.add_argument("--prompt-file", type=str, default=None, help="Text file containing one prompt.")
    parser.add_argument("--dataset-json", type=str, default=None, help="JSON list containing prompts.")
    parser.add_argument("--item-index", type=int, default=0, help="Index used with --dataset-json.")
    parser.add_argument("--task-id", type=str, default=None, help="Stable output/input directory name.")
    parser.add_argument("--task-name", type=str, default="struvis_html", help="Reflection memory bucket name.")
    parser.add_argument("--output-dir", type=str, default="outputs_html", help="Output root.")
    parser.add_argument("--backend", type=str, default=None, choices=["api", "local"])
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--base-url", type=str, default=None)
    parser.add_argument("--api-key", type=str, default=None)
    parser.add_argument("--local-model", type=str, default=None)
    parser.add_argument("--local-dtype", type=str, default=None)
    parser.add_argument("--device-map", type=str, default=None)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    prompt, payload = _load_prompt(args)
    task_input = _make_task_input(project_root, prompt, payload, args.task_id)

    runtime_kwargs = {
        "backend": args.backend,
        "model": args.model,
        "base_url": args.base_url,
        "api_key": args.api_key,
        "local_model": args.local_model,
        "local_dtype": args.local_dtype,
        "device_map": args.device_map,
    }
    scoped_output_root = get_runtime_output_root(project_root / args.output_dir, runtime_kwargs=runtime_kwargs)
    run_agent(
        str(task_input),
        str(scoped_output_root / args.task_name),
        task_type="t2i_html",
        task_name=args.task_name,
        **runtime_kwargs,
    )
    print({"task_input": str(task_input), "output_root": str(scoped_output_root / args.task_name)})


if __name__ == "__main__":
    main()
