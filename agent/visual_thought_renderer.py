"""
Visual Thought Renderer Module
将结构化视觉思考状态渲染成实际的草图
利用 VisualSketchpad 的 Jupyter 执行和视觉工具
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from PIL import Image
from execution import CodeExecutor


class VisualThoughtRenderer:
    """将结构化视觉思考状态渲染成草图"""

    def __init__(self, executor: CodeExecutor):
        """
        初始化渲染器

        Args:
            executor: CodeExecutor 实例，用于执行 Python 代码
        """
        self.executor = executor

    def generate_rendering_code(self, visual_state: Dict, task_type: str = "spatial") -> str:
        """
        根据结构化视觉状态生成 Python 渲染代码

        Args:
            visual_state: 结构化视觉思考状态
            task_type: 任务类型 ("spatial", "geometry", "graph", "math")

        Returns:
            Python 代码字符串
        """
        objects = visual_state.get("objects", [])
        relations = visual_state.get("relations", [])
        constraints = visual_state.get("spatial_constraints", [])
        reasoning = visual_state.get("reasoning_step", "")

        if task_type == "spatial":
            return self._generate_spatial_code(objects, relations, constraints, reasoning)
        elif task_type == "geometry":
            return self._generate_geometry_code(objects, relations, constraints, reasoning)
        elif task_type == "graph":
            return self._generate_graph_code(objects, relations, constraints, reasoning)
        elif task_type == "math":
            return self._generate_math_code(objects, relations, constraints, reasoning)
        else:
            return self._generate_generic_code(objects, relations, constraints, reasoning)

    def _generate_spatial_code(
        self,
        objects: List[Dict],
        relations: List[Dict],
        constraints: List[Dict],
        reasoning: str
    ) -> str:
        """生成空间推理的渲染代码"""
        title = json.dumps(f"Reasoning: {reasoning}")
        code = """
	import matplotlib.pyplot as plt
	import matplotlib.patches as patches
	from PIL import Image
	from io import BytesIO

# Create figure
fig, ax = plt.subplots(figsize=(10, 8))
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.set_aspect('equal')
	ax.grid(True, alpha=0.3)
	
	# Add title with reasoning step
	ax.set_title(""" + title + """, fontsize=12, wrap=True)
	
	# Draw objects
	"""
        # 添加对象绘制代码
        for obj in objects:
            obj_id = obj.get("id", "")
            obj_type = obj.get("type", "point")
            props = obj.get("properties", {})
            label = obj.get("label", obj_id)

            if obj_type == "point":
                pos = props.get("position", [0.5, 0.5])
                color = props.get("color", "red")
                safe_label = json.dumps(str(label))
                code += f"""
	# Draw point {obj_id}
	ax.plot({pos[0]}, {pos[1]}, 'o', color='{color}', markersize=15)
	ax.text({pos[0]}, {pos[1]+0.03}, {safe_label}, fontsize=14, ha='center', weight='bold')
	"""
            elif obj_type == "box":
                pos = props.get("position", [0.3, 0.3])
                size = props.get("size", [0.2, 0.2])
                color = props.get("color", "blue")
                safe_label = json.dumps(str(label))
                code += f"""
	# Draw box {obj_id}
	rect = patches.Rectangle(({pos[0]}, {pos[1]}), {size[0]}, {size[1]},
	                         linewidth=2, edgecolor='{color}', facecolor='none')
	ax.add_patch(rect)
	ax.text({pos[0]+size[0]/2}, {pos[1]+size[1]/2}, {safe_label},
	        fontsize=12, ha='center', va='center', weight='bold')
	"""
            elif obj_type == "circle":
                pos = props.get("position", [0.5, 0.5])
                radius = props.get("radius", 0.1)
                color = props.get("color", "green")
                safe_label = json.dumps(str(label))
                code += f"""
	# Draw circle {obj_id}
	circle = patches.Circle(({pos[0]}, {pos[1]}), {radius},
	                       linewidth=2, edgecolor='{color}', facecolor='none')
	ax.add_patch(circle)
	ax.text({pos[0]}, {pos[1]}, {safe_label}, fontsize=12, ha='center', va='center', weight='bold')
	"""

        # 添加关系绘制代码（箭头）
        code += "\n# Draw relations\n"
        for rel in relations:
            rel_type = rel.get("relation_type", "")
            subject = rel.get("subject", "")
            reference = rel.get("reference", "")

            # 找到对应的对象位置
            subj_obj = next((o for o in objects if o.get("id") == subject), None)
            ref_obj = next((o for o in objects if o.get("id") == reference), None)

            if subj_obj and ref_obj:
                subj_pos = subj_obj.get("properties", {}).get("position", [0, 0])
                ref_pos = ref_obj.get("properties", {}).get("position", [0, 0])

                    safe_rel_type = json.dumps(str(rel_type))
                    code += f"""
	# Relation: {subject} {rel_type} {reference}
	ax.annotate('', xy=({ref_pos[0]}, {ref_pos[1]}), xytext=({subj_pos[0]}, {subj_pos[1]}),
	            arrowprops=dict(arrowstyle='->', lw=1.5, color='gray', alpha=0.6))
	ax.text({(subj_pos[0]+ref_pos[0])/2}, {(subj_pos[1]+ref_pos[1])/2+0.02},
	        {safe_rel_type}, fontsize=9, ha='center', style='italic', color='gray')
	"""

        # 添加约束标注
        code += "\n# Draw constraints\n"
        for constraint in constraints:
            c_type = constraint.get("constraint_type", "")
            c_objects = constraint.get("objects", [])
            c_value = constraint.get("value", "")
            c_unit = constraint.get("unit", "")

            if len(c_objects) >= 2:
                obj1 = next((o for o in objects if o.get("id") == c_objects[0]), None)
                obj2 = next((o for o in objects if o.get("id") == c_objects[1]), None)

                if obj1 and obj2:
                    pos1 = obj1.get("properties", {}).get("position", [0, 0])
                    pos2 = obj2.get("properties", {}).get("position", [0, 0])
                    mid_x = (pos1[0] + pos2[0]) / 2
                    mid_y = (pos1[1] + pos2[1]) / 2

                    label_text = f"{c_type}: {c_value}{c_unit}" if c_value else c_type
                    safe_label_text = json.dumps(str(label_text))
                    code += f"""
	# Constraint: {c_type}
	ax.text({mid_x}, {mid_y-0.05}, {safe_label_text},
	        fontsize=9, ha='center', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
	"""

        code += """
# Save and display
buf = BytesIO()
plt.tight_layout()
plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
plt.close()
buf.seek(0)
sketch_image = Image.open(buf)
display(sketch_image)
"""
        return code

    def _generate_geometry_code(
        self,
        objects: List[Dict],
        relations: List[Dict],
        constraints: List[Dict],
        reasoning: str
    ) -> str:
        """生成几何问题的渲染代码"""
        title = json.dumps(f"Reasoning: {reasoning}")
        code = """
	import matplotlib.pyplot as plt
	import numpy as np
	from PIL import Image
	from io import BytesIO
	
	fig, ax = plt.subplots(figsize=(10, 8))
	ax.set_aspect('equal')
	ax.grid(True, alpha=0.3)
	ax.set_title(""" + title + """, fontsize=12, wrap=True)
	
	"""
        # 绘制几何对象
        for obj in objects:
            obj_type = obj.get("type", "")
            props = obj.get("properties", {})
            label = obj.get("label", "")

            if obj_type == "point":
                pos = props.get("position", [0, 0])
                safe_label = json.dumps(str(label))
                code += f"""
	ax.plot({pos[0]}, {pos[1]}, 'ro', markersize=8)
	ax.text({pos[0]}, {pos[1]+5}, {safe_label}, fontsize=14, ha='center', weight='bold')
	"""
            elif obj_type == "line":
                start = props.get("start", [0, 0])
                end = props.get("end", [1, 1])
                code += f"""
ax.plot([{start[0]}, {end[0]}], [{start[1]}, {end[1]}], 'b-', linewidth=2)
"""
            elif obj_type == "circle":
                center = props.get("center", [0, 0])
                radius = props.get("radius", 10)
                safe_label = json.dumps(str(label))
                code += f"""
	circle = plt.Circle(({center[0]}, {center[1]}), {radius}, fill=False, edgecolor='blue', linewidth=2)
	ax.add_patch(circle)
	ax.plot({center[0]}, {center[1]}, 'bo', markersize=5)
	ax.text({center[0]}, {center[1]+radius+5}, {safe_label}, fontsize=12, ha='center')
	"""

        # 添加辅助线（auxiliary lines）
        code += "\n# Auxiliary lines based on constraints\n"
        for constraint in constraints:
            if constraint.get("constraint_type") == "perpendicular":
                code += "# Draw perpendicular line\n"
            elif constraint.get("constraint_type") == "parallel":
                code += "# Draw parallel line\n"

        code += """
buf = BytesIO()
plt.tight_layout()
plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
plt.close()
buf.seek(0)
sketch_image = Image.open(buf)
display(sketch_image)
"""
        return code

    def _generate_graph_code(
        self,
        objects: List[Dict],
        relations: List[Dict],
        constraints: List[Dict],
        reasoning: str
    ) -> str:
        """生成图论问题的渲染代码"""
        code = """
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from io import BytesIO

# Create graph
G = nx.Graph()

"""
        # 添加节点
        for obj in objects:
            if obj.get("type") == "node":
                node_id = obj.get("id", "")
                label = obj.get("label", node_id)
                code += f"G.add_node('{node_id}', label='{label}')\n"

        # 添加边
        code += "\n# Add edges\n"
        for rel in relations:
            if rel.get("relation_type") == "connected_to":
                subject = rel.get("subject", "")
                reference = rel.get("reference", "")
                weight = rel.get("confidence", 1.0)
                code += f"G.add_edge('{subject}', '{reference}', weight={weight})\n"

        code += f"""
# Draw graph
fig, ax = plt.subplots(figsize=(10, 8))
pos = nx.spring_layout(G, seed=42)
nx.draw(G, pos, with_labels=True, node_color='lightblue',
        node_size=800, font_size=14, font_weight='bold',
        edge_color='gray', width=2, ax=ax)
ax.set_title("Reasoning: {reasoning}", fontsize=12, wrap=True)

buf = BytesIO()
plt.tight_layout()
plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
plt.close()
buf.seek(0)
sketch_image = Image.open(buf)
display(sketch_image)
"""
        return code

    def _generate_math_code(
        self,
        objects: List[Dict],
        relations: List[Dict],
        constraints: List[Dict],
        reasoning: str
    ) -> str:
        """生成数学函数的渲染代码"""
        title = json.dumps(f"Reasoning: {reasoning}")
        code = f"""
	import numpy as np
	import matplotlib.pyplot as plt
	from PIL import Image
	from io import BytesIO
	
	fig, ax = plt.subplots(figsize=(10, 8))
	ax.set_title({title}, fontsize=12, wrap=True)
	ax.grid(True, alpha=0.3)
	
	"""
        # 绘制函数
        for obj in objects:
            if obj.get("type") == "function":
                expr = obj.get("properties", {}).get("expression", "x")
                x_range = obj.get("properties", {}).get("x_range", [-10, 10])
                label = obj.get("label", "f(x)")

                code += f"""
# Plot function: {label}
x = np.linspace({x_range[0]}, {x_range[1]}, 400)
try:
    y = eval("{expr}")
    ax.plot(x, y, label='{label}', linewidth=2)
except:
    pass
"""

        code += """
ax.legend()
ax.axhline(y=0, color='k', linewidth=0.5)
ax.axvline(x=0, color='k', linewidth=0.5)

buf = BytesIO()
plt.tight_layout()
plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
plt.close()
buf.seek(0)
sketch_image = Image.open(buf)
display(sketch_image)
"""
        return code

    def _generate_generic_code(
        self,
        objects: List[Dict],
        relations: List[Dict],
        constraints: List[Dict],
        reasoning: str
    ) -> str:
        """生成通用的渲染代码"""
        return self._generate_spatial_code(objects, relations, constraints, reasoning)

    def render(
        self,
        visual_state: Dict,
        task_type: str = "spatial"
    ) -> Tuple[int, str, List[str]]:
        """
        渲染视觉思考状态为草图

        Args:
            visual_state: 结构化视觉思考状态
            task_type: 任务类型

        Returns:
            (exit_code, output_text, image_paths)
        """
        # 生成渲染代码
        code = self.generate_rendering_code(visual_state, task_type)

        # 执行代码
        exit_code, output, file_paths = self.executor.execute(code)

        return exit_code, output, file_paths

    def render_with_vision_tools(
        self,
        image: Image.Image,
        visual_state: Dict,
        use_detection: bool = False,
        use_segmentation: bool = False,
        use_depth: bool = False
    ) -> Tuple[int, str, List[str]]:
        """
        使用视觉工具增强渲染

        Args:
            image: 输入图像
            visual_state: 视觉思考状态
            use_detection: 是否使用目标检测
            use_segmentation: 是否使用分割
            use_depth: 是否使用深度估计

        Returns:
            (exit_code, output_text, image_paths)
        """
        code = ""

        # 使用检测工具
        if use_detection:
            objects_to_detect = [obj.get("label", "") for obj in visual_state.get("objects", [])]
            if objects_to_detect:
                code += f"""
# Use detection tool
detected_img, boxes = detection(image_1, {objects_to_detect})
display(detected_img.annotated_image)
"""

        # 使用分割工具
        if use_segmentation:
            code += """
# Use segmentation tool
segmented_img, bboxes = segment_and_mark(image_1)
display(segmented_img.annotated_image)
"""

        # 使用深度估计
        if use_depth:
            code += """
# Use depth estimation
depth_map = depth(image_1)
display(depth_map)
"""

        if code:
            exit_code, output, file_paths = self.executor.execute(code)
            return exit_code, output, file_paths

        return 0, "No vision tools used", []
