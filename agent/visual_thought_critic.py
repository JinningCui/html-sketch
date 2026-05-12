"""
Visual Thought Critic Module
结构化错误诊断模块，而不是泛泛反思
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from autogen.oai.client import OpenAIWrapper
from config import build_llm_client


class ErrorType(Enum):
    """错误类型枚举"""
    PERCEPTION_ERROR = "perception_error"  # 看错原图或题目
    GROUNDING_ERROR = "grounding_error"  # 题目元素和草图元素对应错
    SPATIAL_ERROR = "spatial_error"  # 空间关系错
    GEOMETRIC_ERROR = "geometric_error"  # 比例、角度、数量关系错
    STATE_TRANSITION_ERROR = "state_transition_error"  # 多步推理状态更新错
    ANSWER_CONSISTENCY_ERROR = "answer_consistency_error"  # 最终答案和草图不一致
    REDUNDANCY_ERROR = "redundancy_error"  # 草图包含大量无关信息
    NO_ERROR = "no_error"  # 没有错误


@dataclass
class ErrorDiagnosis:
    """结构化错误诊断结果"""
    is_valid: bool
    error_type: ErrorType
    error_location: str  # e.g., "step_2 / object_B / relation_left_of"
    evidence: str  # 错误的证据
    revision_target: str  # 修正建议
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "error_type": self.error_type.value,
            "error_location": self.error_location,
            "evidence": self.evidence,
            "revision_target": self.revision_target,
            "confidence": self.confidence
        }


class VisualThoughtCritic:
    """结构化错误诊断模块"""

    def __init__(self, llm_config: Dict[str, Any] = None, llm_client: Optional[Any] = None):
        self.llm_config = llm_config
        if llm_client is not None:
            self.client = llm_client
        elif llm_config not in (None, False):
            self.client = OpenAIWrapper(**llm_config)
        else:
            self.client = build_llm_client()

    def generate_critique_prompt(self, visual_state: Dict, query: str, image_context: Optional[Dict] = None) -> str:
        """生成批判性分析的提示词"""
        prompt = f"""You are a visual reasoning critic. Analyze the visual thought state for errors.

# ORIGINAL QUERY #
{query}

# VISUAL THOUGHT STATE #
{json.dumps(visual_state, indent=2)}

# ERROR TYPES TO CHECK #
1. PERCEPTION_ERROR: Misreading the original image or question
2. GROUNDING_ERROR: Incorrect mapping between question elements and sketch elements
3. SPATIAL_ERROR: Wrong spatial relationships (left/right/above/below)
4. GEOMETRIC_ERROR: Wrong proportions, angles, or quantities
5. STATE_TRANSITION_ERROR: Incorrect state updates in multi-step reasoning
6. ANSWER_CONSISTENCY_ERROR: Final answer inconsistent with sketch
7. REDUNDANCY_ERROR: Sketch contains irrelevant information

# OUTPUT FORMAT #
Return ONLY valid JSON:
{{
  "is_valid": true/false,
  "error_type": "error_type_name",
  "error_location": "step_X / object_Y / relation_Z",
  "evidence": "Detailed evidence of the error",
  "revision_target": "Specific revision suggestion",
  "confidence": 0.0-1.0
}}

	If no errors found, return: {{"is_valid": true, "error_type": "no_error", ...}}
	"""
        if image_context:
            prompt += f"\n# IMAGE / RENDER CONTEXT #\n{json.dumps(image_context, indent=2)}\n"
        return prompt

    def _call_llm(self, prompt: str) -> str:
        if self.client is None:
            return ""
        response = self.client.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict critic for visual reasoning states. "
                        "Return only valid JSON with the requested fields."
                    ),
                },
                {"role": "user", "content": prompt},
            ]
        )
        extracted = self.client.extract_text_or_completion_object(response)[0]
        return extracted if isinstance(extracted, str) else str(extracted)

    def _parse_diagnosis(self, response: str) -> Optional[ErrorDiagnosis]:
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                return None
            data = json.loads(response[json_start:json_end])
            error_type_value = data.get("error_type", ErrorType.NO_ERROR.value)
            try:
                error_type = ErrorType(error_type_value)
            except ValueError:
                error_type = ErrorType.NO_ERROR if data.get("is_valid", False) else ErrorType.STATE_TRANSITION_ERROR
            return ErrorDiagnosis(
                is_valid=bool(data.get("is_valid", error_type == ErrorType.NO_ERROR)),
                error_type=error_type,
                error_location=data.get("error_location", ""),
                evidence=data.get("evidence", ""),
                revision_target=data.get("revision_target", ""),
                confidence=float(data.get("confidence", 0.5)),
            )
        except Exception as e:
            print(f"Error parsing critic response: {e}")
            return None

    def diagnose(self, visual_state: Dict, query: str, image_context: Optional[Dict] = None) -> ErrorDiagnosis:
        """执行错误诊断"""
        prompt = self.generate_critique_prompt(visual_state, query, image_context)
        response = self._call_llm(prompt)
        diagnosis = self._parse_diagnosis(response)
        if diagnosis is not None:
            return diagnosis

        return ErrorDiagnosis(
            is_valid=True,
            error_type=ErrorType.NO_ERROR,
            error_location="",
            evidence="Critic response could not be parsed; falling back to valid.",
            revision_target="",
            confidence=0.5
        )
