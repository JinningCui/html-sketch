# 四模块系统与 VisualSketchpad 的深度集成指南

## 核心集成点

### 1. Jupyter 代码执行 ✅

**原始 VisualSketchpad 的核心能力：**
- 使用 `CodeExecutor` 类执行 Python 代码
- 基于 `autogen` 的 `JupyterCodeExecutor`
- 支持持久化的 Jupyter kernel 环境

**我们的集成：**
```python
# 在 IntegratedFourModuleSystem 中
self.executor = CodeExecutor(
    working_dir=working_dir,
    use_vision_tools=use_vision_tools
)

# 在 VisualThoughtRenderer 中
self.executor.execute(rendering_code)
```

**优势：**
- 结构化状态 → Python 代码 → 实际草图
- 支持 matplotlib, networkx, PIL 等所有 Python 库
- 草图保存为图像文件，可追踪

### 2. 视觉工具集成 ✅

**原始 VisualSketchpad 的视觉工具：**
- `detection()`: Grounding DINO 目标检测
- `segment_and_mark()`: Set-of-Mark 分割
- `depth()`: Depth-Anything 深度估计
- `zoom_in_image_by_bbox()`: 图像裁剪
- `sliding_window_detection()`: 滑窗检测

**我们的集成：**
```python
# 在 VisualThoughtRenderer 中
def render_with_vision_tools(self, image, visual_state, ...):
    # 使用检测工具
    if use_detection:
        code += f"detected_img, boxes = detection(image_1, {objects})"
    
    # 使用分割工具
    if use_segmentation:
        code += "segmented_img, bboxes = segment_and_mark(image_1)"
    
    # 使用深度估计
    if use_depth:
        code += "depth_map = depth(image_1)"
```

**优势：**
- 结合结构化状态和实际图像
- 自动调用合适的视觉工具
- 增强视觉推理能力

### 3. 渲染流程

```
结构化视觉状态 (JSON)
        ↓
VisualThoughtRenderer.generate_rendering_code()
        ↓
Python 代码 (matplotlib/networkx/PIL)
        ↓
CodeExecutor.execute()
        ↓
Jupyter Kernel 执行
        ↓
草图图像 (PNG/JPG)
        ↓
保存到 working_dir
        ↓
返回图像路径
```

## 完整工作流程

### 迭代 1: 初始生成

```
1. Visual Thought Generator
   → 生成结构化状态 (objects, relations, constraints)

2. Visual Thought Renderer (新增！)
   → 将结构化状态转换为 Python 代码
   → 通过 Jupyter 执行，渲染草图
   → 保存图像: outputs/iteration_1_sketch.png

3. Visual Thought Critic
   → 基于结构化状态 + 渲染图像诊断错误

4. Uncertainty-Guided Stopping
   → 计算置信度（包括 sketch_consistency）

5. Local Visual Revision (如果需要)
   → 生成局部修订操作
```

### 迭代 2+: 修订和重新渲染

```
1. 应用修订到结构化状态

2. Visual Thought Renderer
   → 重新渲染修订后的状态
   → 保存新图像: outputs/iteration_2_sketch.png

3. Visual Thought Critic
   → 诊断修订后的状态

4. 继续循环...
```

## 代码示例

### 示例 1: 空间推理（使用 matplotlib）

```python
from integrated_four_module_system import IntegratedFourModuleSystem
from config import llm_config

system = IntegratedFourModuleSystem(
    llm_config=llm_config,
    working_dir="outputs/spatial",
    use_vision_tools=False  # 只用 matplotlib
)

result = system.run(
    query="B is left of A, C is above B. Where is C relative to A?",
    task_type="spatial"
)

# 查看渲染的草图
print(f"Rendered images: {result['all_rendered_images']}")
# ['outputs/spatial/iteration_1_sketch.png', 
#  'outputs/spatial/iteration_2_sketch.png']
```

### 示例 2: 视觉任务（使用视觉工具）

```python
system = IntegratedFourModuleSystem(
    llm_config=llm_config,
    working_dir="outputs/vision",
    use_vision_tools=True  # 启用视觉工具！
)

result = system.run(
    query="Which object is closest to the camera?",
    image_paths=["input.jpg"],
    task_type="vision"
)

# 会自动调用 detection, segmentation, depth 等工具
```

### 示例 3: 几何问题（使用 matplotlib）

```python
system = IntegratedFourModuleSystem(
    llm_config=llm_config,
    working_dir="outputs/geometry",
    use_vision_tools=False
)

result = system.run(
    query="In circle O with radius 5, angle AOB = 60°. Find chord AB.",
    task_type="geometry"
)

# 会渲染圆、点、辅助线等
```

## 渲染代码生成示例

### 空间推理的渲染代码

输入结构化状态：
```json
{
  "objects": [
    {"id": "A", "type": "point", "properties": {"position": [0.7, 0.5]}, "label": "A"},
    {"id": "B", "type": "point", "properties": {"position": [0.3, 0.5]}, "label": "B"},
    {"id": "C", "type": "point", "properties": {"position": [0.3, 0.8]}, "label": "C"}
  ],
  "relations": [
    {"relation_type": "left_of", "subject": "B", "reference": "A"},
    {"relation_type": "above", "subject": "C", "reference": "B"}
  ]
}
```

生成的 Python 代码：
```python
import matplotlib.pyplot as plt
import matplotlib.patches as patches

fig, ax = plt.subplots(figsize=(10, 8))
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)

# Draw point A
ax.plot(0.7, 0.5, 'o', color='red', markersize=15)
ax.text(0.7, 0.53, 'A', fontsize=14, ha='center', weight='bold')

# Draw point B
ax.plot(0.3, 0.5, 'o', color='red', markersize=15)
ax.text(0.3, 0.53, 'B', fontsize=14, ha='center', weight='bold')

# Draw point C
ax.plot(0.3, 0.8, 'o', color='red', markersize=15)
ax.text(0.3, 0.83, 'C', fontsize=14, ha='center', weight='bold')

# Relation: B left_of A
ax.annotate('', xy=(0.7, 0.5), xytext=(0.3, 0.5),
            arrowprops=dict(arrowstyle='->', lw=1.5, color='gray'))

# Relation: C above B
ax.annotate('', xy=(0.3, 0.5), xytext=(0.3, 0.8),
            arrowprops=dict(arrowstyle='->', lw=1.5, color='gray'))

plt.savefig('sketch.png')
display(Image.open('sketch.png'))
```

执行后生成草图！

## 与原始 VisualSketchpad 的对比

| 特性 | 原始 VisualSketchpad | 集成四模块系统 |
|------|---------------------|---------------|
| **代码执行** | ✅ Jupyter | ✅ Jupyter (保留) |
| **视觉工具** | ✅ Detection/Seg/Depth | ✅ 完全集成 |
| **草图生成** | ❌ 自由形式 | ✅ 结构化 → 渲染 |
| **错误诊断** | ❌ 无 | ✅ 7种错误类型 |
| **局部修订** | ❌ 重新生成 | ✅ 局部编辑 |
| **自适应停止** | ❌ 固定迭代 | ✅ 置信度引导 |
| **可追踪性** | ⚠️ 低 | ✅ 高 |

## 关键优势

### 1. 保留原有能力
- ✅ 所有 VisualSketchpad 的功能都保留
- ✅ Jupyter 执行环境
- ✅ 视觉工具集成
- ✅ 代码生成能力

### 2. 增强推理能力
- ✅ 结构化中间表示
- ✅ 分类型错误诊断
- ✅ 局部修订机制
- ✅ 自适应停止

### 3. 更好的可解释性
- ✅ 每一步都有结构化状态
- ✅ 每一步都有渲染的草图
- ✅ 错误诊断有具体位置
- ✅ 修订操作可追踪

### 4. 灵活性
- ✅ 支持多种任务类型（spatial, geometry, graph, math, vision）
- ✅ 可选择是否使用视觉工具
- ✅ 可配置置信度阈值和迭代次数

## 运行示例

```bash
cd agent

# 运行完整示例
python example_integrated_system.py

# 查看渲染的草图
ls -la ../outputs/four_module_spatial/*.png
ls -la ../outputs/four_module_geometry/*.png
```

## 文件结构

```
agent/
├── visual_thought_generator.py      # 模块1: 生成结构化状态
├── visual_thought_critic.py         # 模块2: 错误诊断
├── local_visual_revision.py         # 模块3: 局部修订
├── uncertainty_guided_stopping.py   # 模块4: 自适应停止
├── visual_thought_renderer.py       # 新增: 渲染器（利用Jupyter）
├── integrated_four_module_system.py # 主控制器（完整集成）
├── example_integrated_system.py     # 完整示例
│
├── execution.py                     # VisualSketchpad 原有
├── tools.py                         # VisualSketchpad 原有
└── config.py                        # VisualSketchpad 原有
```

## 总结

现在的系统**完全集成**了 VisualSketchpad 的 Jupyter 渲染能力：

1. ✅ **结构化状态** → Python 代码 → **实际草图**
2. ✅ 支持 **matplotlib, networkx, PIL** 等所有渲染方式
3. ✅ 集成 **detection, segmentation, depth** 等视觉工具
4. ✅ 每次迭代都会**重新渲染**修订后的状态
5. ✅ 所有草图都**保存为图像文件**，可追踪

这样就真正实现了"结构化视觉推理 + 实际草图渲染"的完整系统！
