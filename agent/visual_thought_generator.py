"""
Visual Thought Generator Module
生成结构化的视觉思考状态，而不是纯图片
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from autogen.oai.client import OpenAIWrapper
from config import build_llm_client


@dataclass
class VisualObject:
    """视觉对象表示"""
    id: str
    type: str  # e.g., "point", "line", "circle", "box"
    properties: Dict[str, Any]  # e.g., {"color": "red", "position": [x, y]}
    label: Optional[str] = None


@dataclass
class SpatialRelation:
    """空间关系表示"""
    relation_type: str  # e.g., "left_of", "above", "inside", "tangent_to"
    subject: str  # object id
    reference: str  # object id
    confidence: float = 1.0


@dataclass
class SpatialConstraint:
    """空间约束表示"""
    constraint_type: str  # e.g., "distance", "angle", "parallel", "perpendicular"
    objects: List[str]  # object ids involved
    value: Optional[Any] = None
    unit: Optional[str] = None


@dataclass
class VisualThoughtState:
    """结构化视觉思考状态"""
    step_id: int
    reasoning_step: str
    objects: List[VisualObject]
    relations: List[SpatialRelation]
    spatial_constraints: List[SpatialConstraint]
    sketch_instruction: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "reasoning_step": self.reasoning_step,
            "objects": [asdict(obj) for obj in self.objects],
            "relations": [asdict(rel) for rel in self.relations],
            "spatial_constraints": [asdict(c) for c in self.spatial_constraints],
            "sketch_instruction": self.sketch_instruction,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VisualThoughtState':
        return cls(
            step_id=data["step_id"],
            reasoning_step=data["reasoning_step"],
            objects=[VisualObject(**obj) for obj in data["objects"]],
            relations=[SpatialRelation(**rel) for rel in data["relations"]],
            spatial_constraints=[SpatialConstraint(**c) for c in data["spatial_constraints"]],
            sketch_instruction=data["sketch_instruction"],
            metadata=data["metadata"]
        )


class VisualThoughtGenerator:
    """生成结构化视觉思考状态的模块"""

    def __init__(self, llm_config: Dict[str, Any] = None, llm_client: Optional[Any] = None):
        self.llm_config = llm_config
        self.step_counter = 0
        if llm_client is not None:
            self.client = llm_client
        elif llm_config not in (None, False):
            self.client = OpenAIWrapper(**llm_config)
        else:
            self.client = build_llm_client()

    def generate_prompt(self, query: str, context: Optional[Dict] = None) -> str:
        """生成用于LLM的提示词，要求输出结构化视觉思考状态"""
        prompt = f"""You are a visual reasoning assistant. Given a problem, generate a structured visual thought state.

# TASK #
{query}

# REQUIREMENTS #
        Generate a structured JSON representation with normalized coordinates where possible.
        Use only object types that can be rendered: point, line, circle, box, node, function.

        Generate a structured JSON representation with:
1. reasoning_step: Your reasoning for this step
2. objects: List of visual objects (id, type, properties, label)
3. relations: Spatial relations between objects
4. spatial_constraints: Geometric constraints
5. sketch_instruction: How to render this as a sketch

# OUTPUT FORMAT #
Return ONLY valid JSON in this format:
{{
  "reasoning_step": "...",
	  "objects": [
	    {{"id": "obj1", "type": "point", "properties": {{"position": [0.25, 0.5], "color": "red"}}, "label": "A"}}
	  ],
  "relations": [
    {{"relation_type": "left_of", "subject": "obj1", "reference": "obj2", "confidence": 1.0}}
  ],
  "spatial_constraints": [
    {{"constraint_type": "distance", "objects": ["obj1", "obj2"], "value": 5, "unit": "cm"}}
  ],
  "sketch_instruction": "Draw point A at position (x,y)..."
	}}
	"""
        if context:
            prompt += f"\n# CONTEXT #\n{json.dumps(context, indent=2)}\n"

        return prompt

    def _call_llm(self, prompt: str) -> str:
        """Call the configured LLM and return text."""
        if self.client is None:
            return ""
        response = self.client.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You generate compact, valid JSON for a structured visual "
                        "reasoning state. Do not wrap JSON in markdown."
                    ),
                },
                {"role": "user", "content": prompt},
            ]
        )
        extracted = self.client.extract_text_or_completion_object(response)[0]
        return extracted if isinstance(extracted, str) else str(extracted)

    def parse_llm_response(self, response: str) -> Optional[VisualThoughtState]:
        """解析LLM返回的JSON响应为结构化状态"""
        try:
            # 提取JSON部分
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                return None

            json_str = response[json_start:json_end]
            data = json.loads(json_str)

            # 构建VisualThoughtState
            state = VisualThoughtState(
                step_id=self.step_counter,
                reasoning_step=data.get("reasoning_step", ""),
                objects=[VisualObject(**obj) for obj in data.get("objects", [])],
                relations=[SpatialRelation(**rel) for rel in data.get("relations", [])],
                spatial_constraints=[SpatialConstraint(**c) for c in data.get("spatial_constraints", [])],
                sketch_instruction=data.get("sketch_instruction", ""),
                metadata=data.get("metadata", {})
            )

            self.step_counter += 1
            return state

        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            return None

    def generate_visual_thought(self, query: str, context: Optional[Dict] = None) -> Optional[VisualThoughtState]:
        """生成视觉思考状态的主方法"""
        prompt = self.generate_prompt(query, context)
        response = self._call_llm(prompt)
        state = self.parse_llm_response(response)
        if state is not None:
            return state

        # Conservative fallback keeps the integrated pipeline usable even when
        # an LLM response is malformed.
        fallback = VisualThoughtState(
            step_id=self.step_counter,
            reasoning_step="Represent the task as a generic visual reasoning state.",
            objects=[
                VisualObject(
                    id="query",
                    type="box",
                    properties={"position": [0.1, 0.35], "size": [0.8, 0.3], "color": "blue"},
                    label="Task",
                )
            ],
            relations=[],
            spatial_constraints=[],
            sketch_instruction=query[:500],
            metadata={"fallback": True, "raw_response": response[:1000]},
        )
        self.step_counter += 1
        return fallback
