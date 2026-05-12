"""
完整示例：使用集成的四模块系统
展示如何利用 Jupyter 渲染视觉草图
"""

import json
from integrated_four_module_system import IntegratedFourModuleSystem
from config import build_llm_runtime_config


def example_spatial_reasoning_with_rendering():
    """空间推理示例 - 带 Jupyter 渲染"""

    runtime = build_llm_runtime_config()
    print("="*80)
    print("Example 1: Spatial Reasoning with Jupyter Rendering")
    print("="*80)

    # 初始化集成系统
    system = IntegratedFourModuleSystem(
        llm_client=runtime.client,
        working_dir="../outputs/four_module_spatial",
        use_vision_tools=False,  # 不使用视觉工具，只用 matplotlib
        config={
            'confidence_threshold': 0.85,
            'max_iterations': 3,
            'min_iterations': 1
        }
    )

    # 定义空间推理问题
    query = """
    There are three objects: A, B, and C.
    - B is to the left of A
    - C is above B
    - The distance between A and B is 5 units

    Question: What is the spatial relationship between A and C?
    Options: (a) C is above-right of A (b) C is above-left of A (c) C is below A
    """

    # 运行推理（会自动用 Jupyter 渲染草图）
    result = system.run(
        query=query,
        task_type="spatial",
        initial_context={"task_type": "spatial_reasoning"}
    )

    # 输出结果
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    print(f"Final Answer: {result['final_answer']}")
    print(f"Total Iterations: {result['total_iterations']}")
    print(f"Stopping Decision: {result['stopping_decision']}")
    print(f"\nRendered Images ({len(result['all_rendered_images'])}):")
    for img_path in result['all_rendered_images']:
        print(f"  - {img_path}")

    # 输出推理轨迹
    print("\n" + system.get_reasoning_trace())

    # 保存结果
    with open("../outputs/four_module_spatial/result.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def example_geometry_with_rendering():
    """几何问题示例 - 带 Jupyter 渲染"""

    runtime = build_llm_runtime_config()
    print("\n\n" + "="*80)
    print("Example 2: Geometry Problem with Jupyter Rendering")
    print("="*80)

    system = IntegratedFourModuleSystem(
        llm_client=runtime.client,
        working_dir="../outputs/four_module_geometry",
        use_vision_tools=False,
        config={
            'confidence_threshold': 0.80,
            'max_iterations': 4,
            'min_iterations': 2
        }
    )

    query = """
    In a circle with center O and radius 5:
    - Points A and B lie on the circumference
    - Angle AOB = 60°

    Find: The length of chord AB

    Hint: Draw auxiliary lines from O to A and O to B, then use the properties of triangles.
    """

    result = system.run(
        query=query,
        task_type="geometry",
        initial_context={"task_type": "geometry"}
    )

    print(f"\nFinal Answer: {result['final_answer']}")
    print(f"Iterations: {result['total_iterations']}")
    print(f"Rendered Images: {len(result['all_rendered_images'])}")

    return result


def example_vision_task_with_tools():
    """视觉任务示例 - 使用视觉工具"""

    runtime = build_llm_runtime_config()
    print("\n\n" + "="*80)
    print("Example 3: Vision Task with Detection/Segmentation Tools")
    print("="*80)

    # 这个示例需要视觉工具服务器运行
    system = IntegratedFourModuleSystem(
        llm_client=runtime.client,
        working_dir="../outputs/four_module_vision",
        use_vision_tools=True,  # 启用视觉工具！
        config={
            'confidence_threshold': 0.85,
            'max_iterations': 3,
            'min_iterations': 1
        }
    )

    query = """
    In the given image, identify all the objects and their spatial relationships.
    Which object is closest to the camera?
    """

    # 假设有输入图像
    image_paths = ["../tasks/blink_spatial/processed/val_Spatial_Relation_1/image.jpg"]

    result = system.run(
        query=query,
        image_paths=image_paths,
        task_type="vision",
        initial_context={"task_type": "spatial_relation"}
    )

    print(f"\nFinal Answer: {result['final_answer']}")
    print(f"Iterations: {result['total_iterations']}")
    print(f"Rendered Images: {len(result['all_rendered_images'])}")

    return result


def example_graph_problem():
    """图论问题示例"""

    runtime = build_llm_runtime_config()
    print("\n\n" + "="*80)
    print("Example 4: Graph Problem with NetworkX Rendering")
    print("="*80)

    system = IntegratedFourModuleSystem(
        llm_client=runtime.client,
        working_dir="../outputs/four_module_graph",
        use_vision_tools=False,
        config={
            'confidence_threshold': 0.85,
            'max_iterations': 3,
            'min_iterations': 1
        }
    )

    query = """
    Given a graph with 5 nodes (A, B, C, D, E) and edges:
    - A connects to B and C
    - B connects to D
    - C connects to D and E

    Question: Is there a path from A to E?
    If yes, what is the shortest path?
    """

    result = system.run(
        query=query,
        task_type="graph",
        initial_context={"task_type": "graph_connectivity"}
    )

    print(f"\nFinal Answer: {result['final_answer']}")
    print(f"Iterations: {result['total_iterations']}")

    return result


if __name__ == "__main__":
    print("="*80)
    print("Integrated Four-Module System - Complete Examples")
    print("Demonstrating Jupyter Rendering Integration")
    print("="*80)

    # 示例 1: 空间推理（使用 matplotlib 渲染）
    try:
        example_spatial_reasoning_with_rendering()
    except Exception as e:
        print(f"Example 1 failed: {e}")

    # 示例 2: 几何问题（使用 matplotlib 渲染）
    try:
        example_geometry_with_rendering()
    except Exception as e:
        print(f"Example 2 failed: {e}")

    # 示例 3: 视觉任务（使用视觉工具）
    # 注意：需要视觉工具服务器运行
    # try:
    #     example_vision_task_with_tools()
    # except Exception as e:
    #     print(f"Example 3 failed: {e}")

    # 示例 4: 图论问题（使用 networkx 渲染）
    try:
        example_graph_problem()
    except Exception as e:
        print(f"Example 4 failed: {e}")

    print("\n" + "="*80)
    print("All examples completed!")
    print("Check the outputs/ directory for rendered images and results")
    print("="*80)
