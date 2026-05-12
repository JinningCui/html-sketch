# 四模块视觉推理系统 (Four-Module Visual Reasoning System)

基于 VisualSketchpad 改进的结构化视觉推理系统，包含四个核心模块。

## 系统架构

```
Input image/question
        ↓
Initial multimodal reasoning
        ↓
┌─────────────────────────────────────────────────────────┐
│  Module 1: Visual Thought Generator                     │
│  生成结构化视觉思考状态                                    │
│  - Objects (对象)                                        │
│  - Relations (关系)                                      │
│  - Spatial Constraints (空间约束)                        │
│  - Reasoning Step (推理步骤)                             │
└─────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────┐
│  Module 2: Visual Thought Critic                        │
│  结构化错误诊断                                           │
│  - Perception Error (感知错误)                           │
│  - Grounding Error (对应错误)                            │
│  - Spatial Error (空间错误)                              │
│  - Geometric Error (几何错误)                            │
│  - State Transition Error (状态转换错误)                 │
│  - Answer Consistency Error (答案一致性错误)             │
│  - Redundancy Error (冗余错误)                           │
└─────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────┐
│  Module 3: Uncertainty-Guided Stopping                  │
│  自适应停止决策                                           │
│  - Answer Confidence (答案置信度)                        │
│  - Critic Confidence (批判者置信度)                      │
│  - Sketch Consistency (草图一致性)                       │
│  - Text-Visual Alignment (文本-视觉对齐)                 │
│  - Change Magnitude (变化幅度)                           │
│  - Answer Stability (答案稳定性)                         │
└─────────────────────────────────────────────────────────┘
        ↓
    Continue? ──No──> Final Answer
        │
       Yes
        ↓
┌─────────────────────────────────────────────────────────┐
│  Module 4: Local Visual Revision                        │
│  局部修改而非重新生成                                      │
│  - MOVE (移动)                                           │
│  - ADD (添加)                                            │
│  - DELETE (删除)                                         │
│  - RELABEL (重新标记)                                    │
│  - RESIZE (调整大小)                                     │
│  - CONNECT/DISCONNECT (连接/断开)                        │
│  - HIGHLIGHT (高亮)                                      │
└─────────────────────────────────────────────────────────┘
        ↓
    (循环回到 Module 1)
```

## 核心创新点

### 1. Visual Thought Generator (视觉思考生成器)

**传统方法的问题：**
- 只生成自由形式的图片
- 难以检查和修改
- 不可解释

**我们的改进：**
- 生成结构化的中间表示
- 包含对象、关系、空间约束
- 可解析、可检查、可修改

**数据结构示例：**
```json
{
  "step_id": 1,
  "reasoning_step": "Identify the spatial relationship between objects A and B",
  "objects": [
    {
      "id": "obj_A",
      "type": "point",
      "properties": {"position": [0.3, 0.5], "color": "red"},
      "label": "A"
    },
    {
      "id": "obj_B",
      "type": "point",
      "properties": {"position": [0.7, 0.5], "color": "blue"},
      "label": "B"
    }
  ],
  "relations": [
    {
      "relation_type": "left_of",
      "subject": "obj_A",
      "reference": "obj_B",
      "confidence": 0.95
    }
  ],
  "spatial_constraints": [
    {
      "constraint_type": "distance",
      "objects": ["obj_A", "obj_B"],
      "value": 5,
      "unit": "cm"
    }
  ],
  "sketch_instruction": "Draw point A at (0.3, 0.5) and point B at (0.7, 0.5)"
}
```

### 2. Visual Thought Critic (视觉思考批判者)

**传统方法的问题：**
- 泛泛的反思："Is your reasoning correct?"
- 没有具体的错误定位
- 难以针对性修正

**我们的改进：**
- 分类型的错误诊断
- 精确的错误定位
- 具体的修正建议

**错误类型：**
1. **Perception Error**: 看错原图或题目
2. **Grounding Error**: 题目元素和草图元素对应错
3. **Spatial Error**: 空间关系错（left/right/above/below）
4. **Geometric Error**: 比例、角度、数量关系错
5. **State Transition Error**: 多步推理状态更新错
6. **Answer Consistency Error**: 最终答案和草图不一致
7. **Redundancy Error**: 草图包含大量无关信息

**诊断结果示例：**
```json
{
  "is_valid": false,
  "error_type": "spatial_error",
  "error_location": "step_2 / object_B / relation_left_of",
  "evidence": "The diagram places B to the right of A, but the question states B is left of A.",
  "revision_target": "Move B to the left of A.",
  "confidence": 0.92
}
```

### 3. Local Visual Revision (局部视觉修订)

**传统方法的问题：**
- 每次错误都重新生成整张草图
- 改对一个地方，又改错另一个地方
- 难以证明反思真的在修正错误

**我们的改进：**
- 局部编辑操作
- 结构化修正
- 可追踪的变化

**操作类型：**
- `MOVE`: 移动对象或关系
- `ADD`: 添加新对象、关系或约束
- `DELETE`: 删除对象、关系或约束
- `RELABEL`: 更改对象标签
- `RESIZE`: 调整对象大小
- `CONNECT`: 添加对象间连接
- `DISCONNECT`: 移除连接
- `REORDER`: 改变顺序
- `HIGHLIGHT`: 强调特定元素
- `ABSTRACT`: 简化表示

**修订操作示例：**
```json
[
  {
    "operation": "move",
    "target": "object_B",
    "parameters": {"new_relation": "left_of(object_A)"},
    "reason": "Fix spatial error: B should be left of A"
  },
  {
    "operation": "add",
    "target": "angle_label",
    "parameters": {
      "value": "60°",
      "location": "between line_AB and line_AC"
    },
    "reason": "Add missing geometric constraint"
  }
]
```

### 4. Uncertainty-Guided Stopping (不确定性引导停止)

**传统方法的问题：**
- 固定迭代 N 次
- 简单样本过度反思会伤害性能
- 只是增加 test-time compute

**我们的改进：**
- 自适应停止
- 综合置信度评估
- 选择性视觉反思

**置信度指标：**
1. **Answer Confidence**: 答案置信度
2. **Critic Confidence**: 批判者置信度
3. **Sketch Consistency Score**: 草图一致性分数
4. **Text-Visual Alignment Score**: 文本-视觉对齐分数
5. **Change Magnitude**: 变化幅度
6. **Answer Stability**: 多轮答案稳定性

**停止决策：**
- `CONTINUE_REFINEMENT`: 继续优化
- `STOP_SUCCESS`: 成功停止
- `FALLBACK_TO_DIRECT`: 回退到直接答案

**决策逻辑：**
```python
overall_confidence = weighted_sum([
    0.25 * answer_confidence,
    0.20 * critic_confidence,
    0.20 * sketch_consistency,
    0.20 * text_visual_alignment,
    0.10 * (1 - change_magnitude),
    0.05 * answer_stability
])

if overall_confidence >= threshold:
    return STOP_SUCCESS
elif overall_confidence < 0.5 and change_magnitude < 0.1:
    return FALLBACK_TO_DIRECT
else:
    return CONTINUE_REFINEMENT
```

## 安装和使用

### 安装依赖

```bash
cd agent
pip install -r requirements.txt  # 如果有的话
```

### 基本使用

```python
from four_module_system import FourModuleVisualReasoningSystem
from config import llm_config

# 初始化系统
system = FourModuleVisualReasoningSystem(
    llm_config=llm_config,
    config={
        'confidence_threshold': 0.85,
        'max_iterations': 5,
        'min_iterations': 1
    }
)

# 运行推理
result = system.run(
    query="Your visual reasoning question here",
    image_context={"image_path": "path/to/image.jpg"},
    initial_context={"task_type": "spatial_reasoning"}
)

# 查看结果
print(f"Answer: {result['final_answer']}")
print(f"Iterations: {result['total_iterations']}")
print(f"Confidence: {result['confidence_metrics']['final']}")

# 查看推理轨迹
print(system.get_reasoning_trace())
```

### 运行示例

```bash
cd agent
python example_four_module.py
```

## 文件结构

```
agent/
├── visual_thought_generator.py      # 模块1: 视觉思考生成器
├── visual_thought_critic.py         # 模块2: 视觉思考批判者
├── local_visual_revision.py         # 模块3: 局部视觉修订
├── uncertainty_guided_stopping.py   # 模块4: 不确定性引导停止
├── four_module_system.py            # 主控制器
├── example_four_module.py           # 使用示例
└── FOUR_MODULE_README.md            # 本文档
```

## 与原始 VisualSketchpad 的对比

| 特性 | 原始 VisualSketchpad | 四模块系统 |
|------|---------------------|-----------|
| 视觉表示 | 自由形式图片 | 结构化中间表示 |
| 错误诊断 | 无 | 7种分类错误类型 |
| 修正方式 | 重新生成 | 局部编辑操作 |
| 停止策略 | 固定迭代 | 自适应置信度 |
| 可解释性 | 低 | 高 |
| 可追踪性 | 低 | 高 |

## 优势

1. **更强的可解释性**：结构化表示使得每一步推理都可追踪
2. **更精确的错误诊断**：7种错误类型覆盖常见推理错误
3. **更高效的修正**：局部修改避免重复工作
4. **更智能的停止**：自适应决策避免过度或不足的推理
5. **更适合论文发表**：审稿人更容易接受结构化方法

## 论文贡献点

1. **Structured Visual Thought State**: 提出可解析的视觉思考中间表示
2. **Typed Visual Error Diagnosis**: 提出分类型的视觉推理错误诊断框架
3. **Local Visual Revision**: 提出局部编辑操作而非全局重生成
4. **Selective Visual Reflection**: 提出选择性视觉反思，避免过度推理

## 未来工作

1. 集成实际的 LLM 调用（目前是框架）
2. 实现草图渲染功能
3. 添加更多错误类型
4. 优化置信度计算方法
5. 在更多数据集上评估

## 引用

如果使用本系统，请引用：

```bibtex
@article{visualsketchpad2024,
  title={Visual Sketchpad: Sketching as a Visual Chain of Thought for Multimodal Language Models},
  author={...},
  journal={NeurIPS},
  year={2024}
}

@article{fourmodule2026,
  title={Four-Module Visual Reasoning: Structured Reflection with Selective Refinement},
  author={...},
  year={2026}
}
```

## 联系

如有问题或建议，请提交 Issue 或 Pull Request。
