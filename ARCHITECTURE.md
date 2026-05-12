"""
系统架构概览和设计文档
"""

# 四模块视觉推理系统 - 技术设计文档

## 1. 系统概述

本系统在 VisualSketchpad 的基础上，设计了一个四模块的结构化视觉推理框架，旨在解决以下问题：

1. **可解释性不足**：传统方法生成自由形式图片，难以追踪推理过程
2. **错误诊断粗糙**：缺乏结构化的错误分类和定位
3. **修正效率低**：每次都重新生成整个草图
4. **停止策略简单**：固定迭代次数，无法自适应

## 2. 核心模块设计

### 2.1 Visual Thought Generator (视觉思考生成器)

**职责**：生成结构化的视觉思考状态

**输入**：
- 用户问题 (query)
- 上下文信息 (context)

**输出**：
- VisualThoughtState 对象，包含：
  - reasoning_step: 推理步骤描述
  - objects: 视觉对象列表
  - relations: 空间关系列表
  - spatial_constraints: 空间约束列表
  - sketch_instruction: 草图渲染指令

**关键数据结构**：
```python
@dataclass
class VisualObject:
    id: str
    type: str  # "point", "line", "circle", "box"
    properties: Dict[str, Any]
    label: Optional[str]

@dataclass
class SpatialRelation:
    relation_type: str  # "left_of", "above", "inside"
    subject: str
    reference: str
    confidence: float

@dataclass
class SpatialConstraint:
    constraint_type: str  # "distance", "angle", "parallel"
    objects: List[str]
    value: Optional[Any]
    unit: Optional[str]
```

**优势**：
- 可解析：JSON 格式，易于程序处理
- 可检查：每个元素都有明确的语义
- 可修改：支持局部编辑
- 可解释：推理步骤明确

### 2.2 Visual Thought Critic (视觉思考批判者)

**职责**：对视觉思考状态进行结构化错误诊断

**输入**：
- 视觉思考状态 (visual_state)
- 原始问题 (query)
- 图像上下文 (image_context)

**输出**：
- ErrorDiagnosis 对象，包含：
  - is_valid: 是否有效
  - error_type: 错误类型（7种）
  - error_location: 错误位置
  - evidence: 错误证据
  - revision_target: 修正建议
  - confidence: 置信度

**错误类型分类**：
1. **PERCEPTION_ERROR**: 感知错误 - 看错原图或题目
2. **GROUNDING_ERROR**: 对应错误 - 题目元素和草图元素对应错
3. **SPATIAL_ERROR**: 空间错误 - 空间关系错误
4. **GEOMETRIC_ERROR**: 几何错误 - 比例、角度、数量关系错
5. **STATE_TRANSITION_ERROR**: 状态转换错误 - 多步推理状态更新错
6. **ANSWER_CONSISTENCY_ERROR**: 答案一致性错误 - 答案和草图不一致
7. **REDUNDANCY_ERROR**: 冗余错误 - 草图包含无关信息

**优势**：
- 精确定位：不是泛泛反思，而是具体指出错在哪里
- 分类诊断：7种错误类型覆盖常见推理错误
- 可操作性：提供具体的修正建议

### 2.3 Local Visual Revision (局部视觉修订)

**职责**：生成和应用局部修订操作

**输入**：
- 视觉思考状态 (visual_state)
- 错误诊断 (error_diagnosis)
- 原始问题 (query)

**输出**：
- 修订操作列表 (List[LocalRevision])
- 修订后的视觉状态

**操作类型**：
- MOVE: 移动对象或关系
- ADD: 添加新元素
- DELETE: 删除元素
- RELABEL: 更改标签
- RESIZE: 调整大小
- CONNECT/DISCONNECT: 连接/断开
- REORDER: 重新排序
- HIGHLIGHT: 高亮显示
- ABSTRACT: 抽象简化

**优势**：
- 高效：只修改需要改的部分
- 可追踪：每个修订操作都有明确记录
- 稳定：不会因为修改一处而影响其他正确的部分

### 2.4 Uncertainty-Guided Stopping (不确定性引导停止)

**职责**：基于综合置信度做出停止决策

**输入**：
- 视觉思考状态
- 错误诊断
- 当前答案
- 迭代次数
- 历史状态

**输出**：
- 是否继续 (bool)
- 停止决策 (StoppingDecision)
- 置信度指标 (ConfidenceMetrics)

**置信度指标**：
1. **answer_confidence**: 答案置信度 (25%)
2. **critic_confidence**: 批判者置信度 (20%)
3. **sketch_consistency_score**: 草图一致性 (20%)
4. **text_visual_alignment_score**: 文本-视觉对齐 (20%)
5. **change_magnitude**: 变化幅度 (10%)
6. **answer_stability**: 答案稳定性 (5%)

**停止决策**：
- CONTINUE_REFINEMENT: 继续优化
- STOP_SUCCESS: 成功停止
- FALLBACK_TO_DIRECT: 回退到直接答案

**优势**：
- 自适应：根据实际情况决定是否继续
- 多维度：综合考虑多个置信度指标
- 避免过度推理：简单问题不会浪费计算资源

## 3. 系统工作流程

```
1. 初始化
   ↓
2. Visual Thought Generator 生成初始状态
   ↓
3. Visual Thought Critic 诊断错误
   ↓
4. Uncertainty-Guided Stopping 计算置信度
   ↓
5. 判断是否继续
   ├─ 否 → 返回最终答案
   └─ 是 → Local Visual Revision 生成修订
       ↓
       应用修订，更新状态
       ↓
       回到步骤 3
```

## 4. 与原始 VisualSketchpad 的集成

本系统可以作为 VisualSketchpad 的增强模块：

1. **保留原有功能**：
   - 保留 ReACT agent 框架
   - 保留 vision tools (detection, segmentation, depth)
   - 保留 code execution 能力

2. **增强推理能力**：
   - 在原有基础上添加结构化状态表示
   - 添加错误诊断和局部修订
   - 添加自适应停止机制

3. **集成方式**：
   - 可以在 `agent.py` 中集成四模块系统
   - 可以在 `prompt.py` 中添加结构化提示词
   - 可以在 `main.py` 中调用四模块系统

## 5. 实现状态

### 已完成：
- ✅ 四个核心模块的框架设计
- ✅ 数据结构定义
- ✅ 主控制器实现
- ✅ 示例代码
- ✅ 文档

### 待完成：
- ⏳ LLM 调用集成（需要连接到实际的 LLM API）
- ⏳ 草图渲染功能
- ⏳ 与 VisualSketchpad 原有代码的深度集成
- ⏳ 在实际数据集上的评估

## 6. 使用示例

```python
from four_module_system import FourModuleVisualReasoningSystem
from config import llm_config

# 初始化
system = FourModuleVisualReasoningSystem(
    llm_config=llm_config,
    config={
        'confidence_threshold': 0.85,
        'max_iterations': 5,
        'min_iterations': 1
    }
)

# 运行
result = system.run(
    query="Your question here",
    image_context={"image_path": "image.jpg"}
)

# 查看结果
print(f"Answer: {result['final_answer']}")
print(f"Iterations: {result['total_iterations']}")
print(system.get_reasoning_trace())
```

## 7. 论文贡献点

1. **Structured Visual Thought State**: 
   - 提出可解析的视觉思考中间表示
   - 比纯图片更易于分析和修改

2. **Typed Visual Error Diagnosis**: 
   - 提出7种视觉推理错误类型
   - 精确定位和诊断错误

3. **Local Visual Revision**: 
   - 提出局部编辑操作
   - 避免全局重生成的低效

4. **Selective Visual Reflection**: 
   - 提出选择性视觉反思
   - 自适应停止避免过度推理

## 8. 评估指标

建议的评估指标：

1. **准确率**：最终答案的正确率
2. **效率**：平均迭代次数
3. **置信度校准**：置信度与准确率的相关性
4. **修订有效性**：修订操作是否真的修正了错误
5. **可解释性**：人类评估推理过程的可理解性

## 9. 未来扩展方向

1. **多模态融合**：更好地融合文本和视觉信息
2. **增量学习**：从错误中学习，改进诊断能力
3. **协作推理**：多个 agent 协作进行视觉推理
4. **工具学习**：自动学习使用新的视觉工具

## 10. 总结

本系统通过四个模块的协同工作，实现了：
- 更强的可解释性
- 更精确的错误诊断
- 更高效的修正
- 更智能的停止决策

这些改进使得视觉推理系统更加实用和可靠，也更容易被学术界接受。
