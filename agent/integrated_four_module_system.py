"""
完整集成的四模块视觉推理系统
深度集成 VisualSketchpad 的 Jupyter 执行和视觉工具
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from visual_thought_generator import VisualThoughtGenerator, VisualThoughtState
from visual_thought_critic import VisualThoughtCritic, ErrorDiagnosis, ErrorType
from local_visual_revision import LocalVisualRevision, LocalRevision
from uncertainty_guided_stopping import UncertaintyGuidedStopping, StoppingDecision, ConfidenceMetrics
from visual_thought_renderer import VisualThoughtRenderer
from execution import CodeExecutor
from config import build_llm_client


@dataclass
class ReasoningIteration:
    """单次推理迭代的记录"""
    iteration: int
    visual_state: VisualThoughtState
    error_diagnosis: ErrorDiagnosis
    revisions: List[LocalRevision]
    confidence_metrics: ConfidenceMetrics
    answer: str
    rendered_images: List[str]  # 渲染出的草图路径


class IntegratedFourModuleSystem:
    """完整集成的四模块视觉推理系统"""

    def __init__(
        self,
        llm_config: Dict[str, Any] = None,
        llm_client: Optional[Any] = None,
        working_dir: str = "../outputs/four_module_integrated",
        use_vision_tools: bool = False,
        config: Optional[Dict] = None
    ):
        """
        初始化系统

        Args:
            llm_config: LLM配置
            working_dir: 工作目录
            use_vision_tools: 是否使用视觉工具（detection, segmentation, depth）
            config: 系统配置
        """
        self.llm_config = llm_config
        self.llm_client = llm_client or build_llm_client()
        self.working_dir = working_dir
        self.use_vision_tools = use_vision_tools
        self.config = config or {}

        # 初始化 CodeExecutor（核心！）
        self.executor = CodeExecutor(
            working_dir=working_dir,
            use_vision_tools=use_vision_tools
        )

        # 初始化四个模块
        self.generator = VisualThoughtGenerator(llm_config, llm_client=self.llm_client)
        self.critic = VisualThoughtCritic(llm_config, llm_client=self.llm_client)
        self.revisor = LocalVisualRevision(llm_config, llm_client=self.llm_client)
        self.stopping_controller = UncertaintyGuidedStopping(
            llm_config,
            confidence_threshold=self.config.get('confidence_threshold', 0.85),
            max_iterations=self.config.get('max_iterations', 5),
            min_iterations=self.config.get('min_iterations', 1)
        )

        # 初始化渲染器（新增！）
        self.renderer = VisualThoughtRenderer(self.executor)

        self.iteration_history: List[ReasoningIteration] = []

    def run(
        self,
        query: str,
        image_paths: Optional[List[str]] = None,
        task_type: str = "spatial",
        initial_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        运行完整的四模块推理流程，带 Jupyter 渲染

        Args:
            query: 用户问题
            image_paths: 输入图像路径列表
            task_type: 任务类型 ("spatial", "geometry", "graph", "math", "vision")
            initial_context: 初始上下文

        Returns:
            包含最终答案、推理历史、渲染图像等的结果字典
        """
        print("=" * 80)
        print("Integrated Four-Module Visual Reasoning System")
        print("=" * 80)

        # 如果有输入图像，先加载到 Jupyter 环境
        if image_paths:
            self._load_images(image_paths)

        iteration = 0
        current_visual_state = None
        previous_visual_state = None
        current_answer = ""

        while True:
            iteration += 1
            print(f"\n{'='*80}")
            print(f"Iteration {iteration}")
            print(f"{'='*80}")

            # Step 1: Visual Thought Generator
            print("\n[1/5] Visual Thought Generator: Generating structured visual state...")
            if iteration == 1:
                visual_state = self.generator.generate_visual_thought(
                    query,
                    context=initial_context
                )
            else:
                visual_state = current_visual_state

            if visual_state is None:
                print("Error: Failed to generate visual thought state")
                break

            print(f"  Generated {len(visual_state.objects)} objects, "
                  f"{len(visual_state.relations)} relations, "
                  f"{len(visual_state.spatial_constraints)} constraints")

            # Step 2: Render to Sketch (新增！利用 Jupyter)
            print("\n[2/5] Visual Thought Renderer: Rendering sketch with Jupyter...")
            rendered_images = []

            if task_type == "vision" and image_paths and self.use_vision_tools:
                # 使用视觉工具增强渲染
                exit_code, output, file_paths = self.renderer.render_with_vision_tools(
                    image=None,  # 已经加载到 Jupyter 环境
                    visual_state=visual_state.to_dict(),
                    use_detection=True,
                    use_segmentation=True,
                    use_depth=False
                )
                rendered_images.extend(file_paths)
                print(f"  Vision tools rendered {len(file_paths)} images")
            else:
                # 使用 matplotlib 渲染结构化状态
                exit_code, output, file_paths = self.renderer.render(
                    visual_state.to_dict(),
                    task_type=task_type
                )
                rendered_images.extend(file_paths)
                print(f"  Matplotlib rendered {len(file_paths)} images")

            if exit_code != 0:
                print(f"  Warning: Rendering failed with exit code {exit_code}")
                print(f"  Error: {output[:200]}")

            # Step 3: Visual Thought Critic
            print("\n[3/5] Visual Thought Critic: Diagnosing errors...")
            error_diagnosis = self.critic.diagnose(
                visual_state.to_dict(),
                query,
                image_context={"rendered_images": rendered_images}
            )

            print(f"  Diagnosis: {'Valid' if error_diagnosis.is_valid else 'Invalid'}")
            if not error_diagnosis.is_valid:
                print(f"  Error Type: {error_diagnosis.error_type.value}")
                print(f"  Location: {error_diagnosis.error_location}")
                print(f"  Evidence: {error_diagnosis.evidence[:100]}...")

            # 生成答案
            current_answer = self._generate_answer(visual_state, query, rendered_images)

            # Step 4: Uncertainty-Guided Stopping
            print("\n[4/5] Uncertainty-Guided Stopping: Computing confidence...")
            should_continue, decision, metrics = self.stopping_controller.should_continue(
                visual_state.to_dict(),
                error_diagnosis.to_dict(),
                query,
                current_answer,
                iteration,
                previous_visual_state.to_dict() if previous_visual_state else None
            )

            print(f"  Overall Confidence: {metrics.overall_confidence():.3f}")
            print(f"  Answer Confidence: {metrics.answer_confidence:.3f}")
            print(f"  Sketch Consistency: {metrics.sketch_consistency_score:.3f}")
            print(f"  Decision: {decision.value}")

            # Step 5: Local Visual Revision (如果需要继续)
            revisions = []
            if should_continue and not error_diagnosis.is_valid:
                print("\n[5/5] Local Visual Revision: Generating revisions...")
                revisions = self.revisor.generate_revisions(
                    visual_state.to_dict(),
                    error_diagnosis.to_dict(),
                    query
                )
                print(f"  Generated {len(revisions)} revisions")

                # 应用修订
                if revisions:
                    revised_state_dict = self.revisor.apply_revisions(
                        visual_state.to_dict(),
                        revisions
                    )
                    previous_visual_state = visual_state
                    current_visual_state = VisualThoughtState.from_dict(revised_state_dict)

                    # 打印修订操作
                    for i, rev in enumerate(revisions):
                        print(f"    Revision {i+1}: {rev.operation.value} on {rev.target}")
                        print(f"      Reason: {rev.reason[:80]}...")
                else:
                    current_visual_state = visual_state
            else:
                print("\n[5/5] Local Visual Revision: Skipped (stopping)")
                current_visual_state = visual_state

            # 记录本次迭代
            self.iteration_history.append(ReasoningIteration(
                iteration=iteration,
                visual_state=visual_state,
                error_diagnosis=error_diagnosis,
                revisions=revisions,
                confidence_metrics=metrics,
                answer=current_answer,
                rendered_images=rendered_images
            ))

            # 检查是否停止
            if not should_continue:
                print(f"\n{'='*80}")
                print(f"Stopping: {decision.value}")
                print(f"{'='*80}")
                break

            if iteration >= self.stopping_controller.max_iterations:
                print(f"\n{'='*80}")
                print(f"Reached maximum iterations ({self.stopping_controller.max_iterations})")
                print(f"{'='*80}")
                break

        # 清理
        self.executor.cleanup()

        # 返回结果
        return self._compile_results(
            final_answer=current_answer,
            final_state=current_visual_state,
            decision=decision
        )

    def _load_images(self, image_paths: List[str]):
        """加载图像到 Jupyter 环境"""
        print(f"\nLoading {len(image_paths)} images into Jupyter environment...")
        code = ""
        for idx, path in enumerate(image_paths):
            code += f"image_{idx+1} = Image.open('{path}').convert('RGB')\n"

        exit_code, output, _ = self.executor.execute(code)
        if exit_code == 0:
            print(f"  Successfully loaded {len(image_paths)} images")
        else:
            print(f"  Warning: Failed to load images: {output[:200]}")

    def _generate_answer(
        self,
        visual_state: VisualThoughtState,
        query: str,
        rendered_images: List[str]
    ) -> str:
        """基于视觉状态和渲染图像生成答案。"""
        prompt = (
            "You are solving a visual reasoning task from a structured intermediate state.\n"
            "Use the structured state and the rendered image paths as supporting context.\n"
            "If the query is multiple-choice, return the selected option clearly.\n\n"
            f"# ORIGINAL QUERY #\n{query}\n\n"
            f"# STRUCTURED VISUAL STATE #\n{json.dumps(visual_state.to_dict(), ensure_ascii=False, indent=2)}\n\n"
            f"# RENDERED IMAGES #\n{json.dumps(rendered_images, ensure_ascii=False, indent=2)}\n"
        )
        response = self.llm_client.create(
            messages=[
                {"role": "system", "content": "Answer the user's question from the provided reasoning state."},
                {"role": "user", "content": prompt},
            ]
        )
        answer, _ = self.llm_client.extract_text_or_completion_object(response)
        return answer if isinstance(answer, str) else str(answer)

    def _compile_results(
        self,
        final_answer: str,
        final_state: VisualThoughtState,
        decision: StoppingDecision
    ) -> Dict[str, Any]:
        """编译最终结果"""
        return {
            "final_answer": final_answer,
            "final_visual_state": final_state.to_dict() if final_state else None,
            "stopping_decision": decision.value,
            "total_iterations": len(self.iteration_history),
            "all_rendered_images": [
                img for it in self.iteration_history for img in it.rendered_images
            ],
            "iteration_history": [
                {
                    "iteration": it.iteration,
                    "visual_state": it.visual_state.to_dict(),
                    "error_diagnosis": it.error_diagnosis.to_dict(),
                    "revisions": [r.to_dict() for r in it.revisions],
                    "confidence": it.confidence_metrics.overall_confidence(),
                    "answer": it.answer,
                    "rendered_images": it.rendered_images
                }
                for it in self.iteration_history
            ],
            "confidence_metrics": {
                "final": self.iteration_history[-1].confidence_metrics.__dict__ if self.iteration_history else None
            }
        }

    def get_reasoning_trace(self) -> str:
        """获取可读的推理轨迹"""
        trace = []
        trace.append("=" * 80)
        trace.append("INTEGRATED VISUAL REASONING TRACE")
        trace.append("=" * 80)

        for it in self.iteration_history:
            trace.append(f"\nIteration {it.iteration}:")
            trace.append(f"  Reasoning: {it.visual_state.reasoning_step}")
            trace.append(f"  Objects: {len(it.visual_state.objects)}")
            trace.append(f"  Rendered Images: {len(it.rendered_images)}")
            for img_path in it.rendered_images:
                trace.append(f"    - {img_path}")
            trace.append(f"  Valid: {it.error_diagnosis.is_valid}")
            if not it.error_diagnosis.is_valid:
                trace.append(f"  Error: {it.error_diagnosis.error_type.value}")
                trace.append(f"  Revision Target: {it.error_diagnosis.revision_target}")
            trace.append(f"  Confidence: {it.confidence_metrics.overall_confidence():.3f}")
            trace.append(f"  Revisions Applied: {len(it.revisions)}")

        trace.append("\n" + "=" * 80)
        return "\n".join(trace)
