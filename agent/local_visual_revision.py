"""
Local Visual Revision Module
局部修改模块，而不是重新生成整张草图
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from autogen.oai.client import OpenAIWrapper
from config import build_llm_client


class RevisionOperation(Enum):
    """修订操作类型"""
    MOVE = "move"
    ADD = "add"
    DELETE = "delete"
    RELABEL = "relabel"
    RESIZE = "resize"
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    REORDER = "reorder"
    HIGHLIGHT = "highlight"
    ABSTRACT = "abstract"


@dataclass
class LocalRevision:
    """局部修订操作"""
    operation: RevisionOperation
    target: str  # object id or relation id
    parameters: Dict[str, Any]  # operation-specific parameters
    reason: str  # why this revision is needed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation.value,
            "target": self.target,
            "parameters": self.parameters,
            "reason": self.reason
        }


class LocalVisualRevision:
    """局部视觉修订模块"""

    def __init__(self, llm_config: Dict[str, Any] = None, llm_client: Optional[Any] = None):
        self.llm_config = llm_config
        if llm_client is not None:
            self.client = llm_client
        elif llm_config not in (None, False):
            self.client = OpenAIWrapper(**llm_config)
        else:
            self.client = build_llm_client()

    def generate_revision_prompt(
        self,
        visual_state: Dict,
        error_diagnosis: Dict,
        query: str
    ) -> str:
        """生成局部修订的提示词"""
        prompt = f"""You are a visual reasoning revision assistant. Generate LOCAL revisions to fix errors.

# ORIGINAL QUERY #
{query}

# CURRENT VISUAL STATE #
{json.dumps(visual_state, indent=2)}

# ERROR DIAGNOSIS #
{json.dumps(error_diagnosis, indent=2)}

# AVAILABLE OPERATIONS #
- MOVE: Change object position or relation
- ADD: Add new object, relation, or constraint
- DELETE: Remove object, relation, or constraint
- RELABEL: Change object label
- RESIZE: Change object size
- CONNECT: Add connection between objects
- DISCONNECT: Remove connection
- REORDER: Change ordering
- HIGHLIGHT: Emphasize specific element
- ABSTRACT: Simplify representation

# OUTPUT FORMAT #
Return ONLY valid JSON array of revisions:
[
  {{
    "operation": "move",
    "target": "object_B",
    "parameters": {{"new_relation": "left_of(object_A)"}},
    "reason": "Fix spatial error identified in diagnosis"
  }},
  {{
    "operation": "add",
    "target": "angle_label",
    "parameters": {{"value": "60°", "location": "between line_AB and line_AC"}},
    "reason": "Add missing geometric constraint"
  }}
]

Generate MINIMAL revisions that directly address the error.
"""
        return prompt

    def _call_llm(self, prompt: str) -> str:
        if self.client is None:
            return ""
        response = self.client.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You generate minimal local edits for JSON visual states. "
                        "Return only a valid JSON array."
                    ),
                },
                {"role": "user", "content": prompt},
            ]
        )
        extracted = self.client.extract_text_or_completion_object(response)[0]
        return extracted if isinstance(extracted, str) else str(extracted)

    def _parse_revisions(self, response: str) -> List[LocalRevision]:
        try:
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            if json_start == -1 or json_end == 0:
                return []
            data = json.loads(response[json_start:json_end])
            revisions = []
            for item in data:
                try:
                    operation = RevisionOperation(item.get("operation"))
                except ValueError:
                    continue
                revisions.append(
                    LocalRevision(
                        operation=operation,
                        target=item.get("target", ""),
                        parameters=item.get("parameters", {}),
                        reason=item.get("reason", ""),
                    )
                )
            return revisions
        except Exception as e:
            print(f"Error parsing revision response: {e}")
            return []

    def generate_revisions(
        self,
        visual_state: Dict,
        error_diagnosis: Dict,
        query: str
    ) -> List[LocalRevision]:
        """生成局部修订操作列表"""
        prompt = self.generate_revision_prompt(visual_state, error_diagnosis, query)
        return self._parse_revisions(self._call_llm(prompt))

    def _find_object(self, visual_state: Dict, target: str) -> Optional[Dict]:
        for obj in visual_state.get("objects", []):
            if obj.get("id") == target or obj.get("label") == target:
                return obj
        return None

    def apply_revision(
        self,
        visual_state: Dict,
        revision: LocalRevision
    ) -> Dict:
        """应用单个修订操作到视觉状态"""
        new_state = json.loads(json.dumps(visual_state))  # deep copy

        if revision.operation == RevisionOperation.MOVE:
            obj = self._find_object(new_state, revision.target)
            if obj:
                props = obj.setdefault("properties", {})
                if "position" in revision.parameters:
                    props["position"] = revision.parameters["position"]
                if "new_position" in revision.parameters:
                    props["position"] = revision.parameters["new_position"]
                if "start" in revision.parameters:
                    props["start"] = revision.parameters["start"]
                if "end" in revision.parameters:
                    props["end"] = revision.parameters["end"]
        elif revision.operation == RevisionOperation.ADD:
            item = revision.parameters.get("object")
            if item:
                new_state.setdefault("objects", []).append(item)
            relation = revision.parameters.get("relation")
            if relation:
                new_state.setdefault("relations", []).append(relation)
            constraint = revision.parameters.get("constraint")
            if constraint:
                new_state.setdefault("spatial_constraints", []).append(constraint)
        elif revision.operation == RevisionOperation.DELETE:
            for key in ("objects", "relations", "spatial_constraints"):
                new_state[key] = [
                    item for item in new_state.get(key, [])
                    if item.get("id") != revision.target and item.get("label") != revision.target
                ]
        elif revision.operation == RevisionOperation.RELABEL:
            obj = self._find_object(new_state, revision.target)
            if obj and "label" in revision.parameters:
                obj["label"] = revision.parameters["label"]
        elif revision.operation == RevisionOperation.RESIZE:
            obj = self._find_object(new_state, revision.target)
            if obj:
                props = obj.setdefault("properties", {})
                for key in ("size", "radius", "width", "height"):
                    if key in revision.parameters:
                        props[key] = revision.parameters[key]
        elif revision.operation == RevisionOperation.CONNECT:
            relation = revision.parameters.get("relation")
            if relation:
                new_state.setdefault("relations", []).append(relation)
        elif revision.operation == RevisionOperation.DISCONNECT:
            subject = revision.parameters.get("subject")
            reference = revision.parameters.get("reference")
            new_state["relations"] = [
                rel for rel in new_state.get("relations", [])
                if not (
                    rel.get("subject") in {subject, revision.target}
                    and rel.get("reference") in {reference, revision.target}
                )
            ]
        elif revision.operation == RevisionOperation.HIGHLIGHT:
            obj = self._find_object(new_state, revision.target)
            if obj:
                obj.setdefault("properties", {})["highlight"] = True
        elif revision.operation == RevisionOperation.ABSTRACT:
            new_state["metadata"] = new_state.get("metadata", {})
            new_state["metadata"]["abstracted"] = True

        return new_state

    def apply_revisions(
        self,
        visual_state: Dict,
        revisions: List[LocalRevision]
    ) -> Dict:
        """应用所有修订操作"""
        current_state = visual_state
        for revision in revisions:
            current_state = self.apply_revision(current_state, revision)
        return current_state
