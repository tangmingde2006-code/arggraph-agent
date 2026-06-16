"""Tool 1: ADU Segmenter 的输入输出 Schema（对应 SOP §1-2）"""

from pydantic import BaseModel, Field
from typing import List, Optional


class ADUInput(BaseModel):
    """ADU 切分的输入"""
    essay_text: str = Field(..., description="完整议论文文本，含所有自然段")
    essay_topic: Optional[str] = Field(None, description="作文题目，可选，用于辅助判断")


class ADUItem(BaseModel):
    """单个论证单元"""
    id: str = Field(..., description="ADU 编号，格式 Pn_Sm（n=段号，m=本段第m个ADU）")
    text: str = Field(..., description="ADU 的文本内容")


class ADUOutput(BaseModel):
    """ADU 切分的输出"""
    segments: List[ADUItem] = Field(..., description="切分后的 ADU 列表")
    paragraph_count: int = Field(..., description="自然段数量")
    total_adus: int = Field(..., description="ADU 总数")


class ADUResult(BaseModel):
    """ADU 切分的完整结果，包含原始文本方便后续处理"""
    input_essay: str = Field(..., description="原始议论文文本")
    output: ADUOutput = Field(..., description="切分结果")
