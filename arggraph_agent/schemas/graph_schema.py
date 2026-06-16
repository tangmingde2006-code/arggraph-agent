"""Tool 3: Relation Builder 的输入输出 Schema（对应 SOP §7-14）"""

from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from enum import Enum


class RelationType(str, Enum):
    """论证关系类型"""
    SUPPORT = "support"        # 支持
    ATTACK = "attack"          # 攻击/反驳
    EXAMPLE_OF = "example-of"  # 例证
    EXPLAIN = "explain"        # 解释/展开
    EXTEND = "extend"          # 延伸/补充
    PARALLEL = "parallel"      # 并列
    INCLUDE = "include"        # 包含/具体化
    DISCONNECTED = "disconnected"  # 无直接关系


class RelationInput(BaseModel):
    """关系构建的输入"""
    essay_text: str = Field(..., description="原始全文，用于上下文参考")
    node_table: List[dict] = Field(..., description="节点表，每项含 node_id, text, type")


class EdgeItem(BaseModel):
    """论证图中的一条边"""
    source: str = Field(..., alias="from", description="起始节点 ID")
    target: str = Field(..., alias="to", description="目标节点 ID")
    relation: RelationType = Field(..., description="论证关系类型")
    reasoning: str = Field(..., description="判定理由")

    class Config:
        populate_by_name = True


class ConsistencyReport(BaseModel):
    """一致性检查报告"""
    all_claims_connected_to_mc: bool = Field(..., description="所有段落 Claim 是否连接到 MC")
    all_evidence_connected: bool = Field(..., description="所有 Evidence 是否连接到某个 Claim")
    orphan_nodes: List[str] = Field(default_factory=list, description="孤立节点列表")
    cycles_detected: bool = Field(False, description="是否检测到循环")


class GraphOutput(BaseModel):
    """关系构建的完整输出"""
    edge_table: List[EdgeItem] = Field(..., description="边表")
    tree_graph: str = Field(..., description="树状图文本")
    mermaid_code: str = Field(..., description="Mermaid 图代码")
    consistency_check: ConsistencyReport = Field(..., description="一致性检查报告")
    summary: str = Field(..., description="论证结构总结（一段话）")


class GraphResult(BaseModel):
    """关系构建的完整结果"""
    input_nodes: List[dict] = Field(..., description="输入的节点表")
    output: GraphOutput = Field(..., description="图构建结果")
