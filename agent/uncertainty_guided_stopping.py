"""
Uncertainty-Guided Stopping Module
自适应停止模块，而不是固定迭代N次
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class StoppingDecision(Enum):
    """停止决策"""
    CONTINUE_REFINEMENT = "continue_refinement"
    STOP_SUCCESS = "stop_success"
    FALLBACK_TO_DIRECT = "fallback_to_direct"


@dataclass
class ConfidenceMetrics:
    """综合置信度指标"""
    answer_confidence: float  # 答案置信度
    critic_confidence: float  # 批判者置信度
    sketch_consistency_score: float  # 草图一致性分数
    text_visual_alignment_score: float  # 文本-视觉对齐分数
    change_magnitude: float  # 变化幅度
    answer_stability: float  # 多轮答案稳定性

    def overall_confidence(self) -> float:
        """计算综合置信度"""
        weights = {
            'answer': 0.25,
            'critic': 0.20,
            'sketch_consistency': 0.20,
            'text_visual_alignment': 0.20,
            'change_magnitude': 0.10,
            'answer_stability': 0.05
        }

        return (
            weights['answer'] * self.answer_confidence +
            weights['critic'] * self.critic_confidence +
            weights['sketch_consistency'] * self.sketch_consistency_score +
            weights['text_visual_alignment'] * self.text_visual_alignment_score +
            weights['change_magnitude'] * (1 - self.change_magnitude) +
            weights['answer_stability'] * self.answer_stability
        )


class UncertaintyGuidedStopping:
    """不确定性引导的停止模块"""

    def __init__(
        self,
        llm_config: Dict[str, Any],
        confidence_threshold: float = 0.85,
        max_iterations: int = 5,
        min_iterations: int = 1
    ):
        self.llm_config = llm_config
        self.confidence_threshold = confidence_threshold
        self.max_iterations = max_iterations
        self.min_iterations = min_iterations
        self.iteration_history: List[Dict] = []

    def compute_answer_confidence(self, visual_state: Dict, answer: str) -> float:
        """计算答案置信度"""
        # 实际实现需要基于LLM或其他方法
        return 0.8

    def compute_critic_confidence(self, error_diagnosis: Dict) -> float:
        """计算批判者置信度"""
        if error_diagnosis.get("is_valid", False):
            return error_diagnosis.get("confidence", 1.0)
        return 1.0 - error_diagnosis.get("confidence", 0.5)

    def compute_sketch_consistency(self, visual_state: Dict) -> float:
        """计算草图一致性分数"""
        # 检查对象、关系、约束之间的一致性
        objects = visual_state.get("objects", [])
        relations = visual_state.get("relations", [])
        constraints = visual_state.get("spatial_constraints", [])

        if not objects:
            return 0.0

        # 简单的一致性检查
        object_ids = {obj.get("id") for obj in objects}
        relation_refs = set()
        for rel in relations:
            relation_refs.add(rel.get("subject"))
            relation_refs.add(rel.get("reference"))

        # 检查关系引用的对象是否都存在
        if relation_refs and not relation_refs.issubset(object_ids):
            return 0.5

        return 0.9

    def compute_text_visual_alignment(
        self,
        visual_state: Dict,
        query: str
    ) -> float:
        """计算文本-视觉对齐分数"""
        # 实际实现需要基于LLM或语义相似度
        return 0.85

    def compute_change_magnitude(
        self,
        previous_state: Optional[Dict],
        current_state: Dict
    ) -> float:
        """计算变化幅度"""
        if not previous_state:
            return 1.0

        # 简单比较对象数量变化
        prev_obj_count = len(previous_state.get("objects", []))
        curr_obj_count = len(current_state.get("objects", []))

        if prev_obj_count == 0:
            return 1.0

        change_ratio = abs(curr_obj_count - prev_obj_count) / prev_obj_count
        return min(change_ratio, 1.0)

    def compute_answer_stability(self, answers: List[str]) -> float:
        """计算多轮答案稳定性"""
        if len(answers) < 2:
            return 1.0

        # 检查最近几轮答案是否一致
        recent_answers = answers[-3:]
        if len(set(recent_answers)) == 1:
            return 1.0

        return 0.5

    def compute_confidence_metrics(
        self,
        visual_state: Dict,
        error_diagnosis: Dict,
        query: str,
        answer: str,
        previous_state: Optional[Dict] = None
    ) -> ConfidenceMetrics:
        """计算所有置信度指标"""
        answers = [item.get("answer", "") for item in self.iteration_history]
        answers.append(answer)

        return ConfidenceMetrics(
            answer_confidence=self.compute_answer_confidence(visual_state, answer),
            critic_confidence=self.compute_critic_confidence(error_diagnosis),
            sketch_consistency_score=self.compute_sketch_consistency(visual_state),
            text_visual_alignment_score=self.compute_text_visual_alignment(visual_state, query),
            change_magnitude=self.compute_change_magnitude(previous_state, visual_state),
            answer_stability=self.compute_answer_stability(answers)
        )

    def make_stopping_decision(
        self,
        confidence_metrics: ConfidenceMetrics,
        iteration: int
    ) -> StoppingDecision:
        """做出停止决策"""
        overall_conf = confidence_metrics.overall_confidence()

        # 达到最大迭代次数
        if iteration >= self.max_iterations:
            if overall_conf >= 0.6:
                return StoppingDecision.STOP_SUCCESS
            else:
                return StoppingDecision.FALLBACK_TO_DIRECT

        # 未达到最小迭代次数
        if iteration < self.min_iterations:
            return StoppingDecision.CONTINUE_REFINEMENT

        # 置信度足够高
        if overall_conf >= self.confidence_threshold:
            return StoppingDecision.STOP_SUCCESS

        # 置信度太低且变化很小
        if overall_conf < 0.5 and confidence_metrics.change_magnitude < 0.1:
            return StoppingDecision.FALLBACK_TO_DIRECT

        # 继续优化
        return StoppingDecision.CONTINUE_REFINEMENT

    def should_continue(
        self,
        visual_state: Dict,
        error_diagnosis: Dict,
        query: str,
        answer: str,
        iteration: int,
        previous_state: Optional[Dict] = None
    ) -> tuple[bool, StoppingDecision, ConfidenceMetrics]:
        """判断是否应该继续优化"""
        metrics = self.compute_confidence_metrics(
            visual_state, error_diagnosis, query, answer, previous_state
        )

        decision = self.make_stopping_decision(metrics, iteration)

        # 记录历史
        self.iteration_history.append({
            "iteration": iteration,
            "visual_state": visual_state,
            "answer": answer,
            "metrics": metrics,
            "decision": decision.value
        })

        should_continue = (decision == StoppingDecision.CONTINUE_REFINEMENT)
        return should_continue, decision, metrics
