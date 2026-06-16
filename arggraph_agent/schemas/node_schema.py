"""Tool 2: Component Classifier 的输入输出 Schema（对应 SOP §3-6）"""

from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from enum import Enum


class NodeType(str, Enum):
    """论证组件类型"""
    MAJOR_CLAIM = "major_claim"         # MC：全文中心论点
    PARAGRAPH_CLAIM = "paragraph_claim"  # Pn_C：段落主张
    ANALYSIS = "analysis"                # A：分析/解释
    EVIDENCE = "evidence"                # E：论据/事例
    EVIDENCE_ANALYSIS = "evidence_analysis"  # EA：对论据的分析/解释


class ComponentInput(BaseModel):
    """组件分类的输入"""
    essay_text: str = Field(..., description="原始全文，用于上下文参考")
    essay_topic: Optional[str] = Field(None, description="作文题目，用于 MC 的题目贴近测试")
    adu_list: List[dict] = Field(..., description="ADU 切分结果列表，每项含 id 和 text")


class NodeItem(BaseModel):
    """论证图中的一个节点"""
    node_id: str = Field(..., description="节点 ID：MC / Pn_C / Pn_Am / Pn_Em / Pn_EAm")
    original_id: str = Field(..., description="对应的原始 ADU ID（如 P1_S4）")
    text: str = Field(..., description="节点文本内容")
    type: NodeType = Field(..., description="节点类型")
    reasoning: List[str] = Field(..., description="判定理由列表，至少一条")


class ComponentOutput(BaseModel):
    """组件分类的输出"""
    node_table: List[NodeItem] = Field(..., description="完整的节点表")


class ComponentResult(BaseModel):
    """组件分类的完整结果"""
    input_adu: List[dict] = Field(..., description="输入的 ADU 列表")
    output: ComponentOutput = Field(..., description="分类结果")
