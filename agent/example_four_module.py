"""
示例：使用四模块视觉推理系统
"""

import json
from four_module_system import FourModuleVisualReasoningSystem
from config import build_llm_runtime_config


def example_spatial_reasoning():
    """空间推理示例"""

    runtime = build_llm_runtime_config()
    # 初始化系统
    system = FourModuleVisualReasoningSystem(
        llm_client=runtime.client,
        config={
            'confidence_threshold': 0.85,
            'max_iterations': 5,
            'min_iterations': 1
        }
    )

    # 定义问题
    query = """
    Given an image with three objects: A, B, and C.
    The question states: "B is to the left of A, and C is above B."
    What is the spatial relationship between A and C?
    Options: (a) C is above-right of A (b) C is above-left of A (c) C is below A
    """

    # 运行推理
    result = system.run(
        query=query,
        image_context={"image_path": "example.jpg"},
        initial_context={"task_type": "spatial_reasoning"}
    )

    # 输出结果
    print("\n" + "="*80)
    print("FINAL RESULTS")
    print("="*80)
    print(f"Answer: {result['final_answer']}")
    print(f"Total Iterations: {result['total_iterations']}")
    print(f"Stopping Decision: {result['stopping_decision']}")

    # 输出推理轨迹
    print("\n" + system.get_reasoning_trace())

    # 保存完整结果
    with open("four_module_result.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def example_geometry_problem():
    """几何问题示例"""

    runtime = build_llm_runtime_config()
    system = FourModuleVisualReasoningSystem(
        llm_client=runtime.client,
        config={
            'confidence_threshold': 0.80,
            'max_iterations': 4,
            'min_iterations': 2
        }
    )

    query = """
    In a circle with center O, points A, B, C lie on the circumference.
    Given: OA = 5, angle AOB = 60°
    Find: The length of chord AB
    """

    result = system.run(
        query=query,
        initial_context={"task_type": "geometry"}
    )

    print(f"\nAnswer: {result['final_answer']}")
    print(f"Iterations: {result['total_iterations']}")

    return result


if __name__ == "__main__":
    print("="*80)
    print("Four-Module Visual Reasoning System - Examples")
    print("="*80)

    # 运行空间推理示例
    print("\n\n### Example 1: Spatial Reasoning ###")
    example_spatial_reasoning()

    # 运行几何问题示例
    print("\n\n### Example 2: Geometry Problem ###")
    example_geometry_problem()
