"""Tool 2: Component Classifier（论证组件分类器）

对应 SOP §3（MC 识别）、§4（段落 Claim 识别）、§5（段内 ADU 分类）、§6（节点命名规范）

实现逻辑：
1. MC 识别：首尾段搜索 + 统摄测试 + 题目贴近测试
2. 段落 Claim 识别：段首优先
3. 剩余 ADU 分类：A / E / EA 三类划分
4. 每个识别结果附带判定理由
"""

from typing import Dict, Any, Optional, List
from openai import OpenAI

from ..utils.api_client import chat_completion
from ..utils.json_parser import parse_json_response
from ..prompts.tool2_prompt import TOOL2_PROMPT, build_tool2_messages


class ComponentClassifier:
    """论证组件分类器"""

    # 节点类型常量
    MAJOR_CLAIM = "major_claim"
    PARAGRAPH_CLAIM = "paragraph_claim"
    ANALYSIS = "analysis"
    EVIDENCE = "evidence"
    EVIDENCE_ANALYSIS = "evidence_analysis"

    def __init__(self, client: OpenAI):
        self.client = client

    def classify(
        self,
        essay_text: str,
        essay_topic: Optional[str],
        adu_list: List[Dict],
    ) -> Dict[str, Any]:
        """执行论证组件分类。

        Args:
            essay_text: 原始全文
            essay_topic: 作文题目（可选）
            adu_list: ADU 切分结果列表

        Returns:
            分类结果字典，含 node_table
        """
        messages = build_tool2_messages(essay_text, essay_topic or "", adu_list)

        try:
            response = chat_completion(self.client, messages, temperature=0.2, max_tokens=8192)
            result = parse_json_response(response)
            return result
        except Exception as e:
            # LLM 失败时，使用降级策略：基于启发式规则做基本分类
            print(f"  [Tool 2 降级] LLM 分类失败 ({e})，使用启发式分类结果")
            return self._fallback_classify(essay_text, adu_list)

    def extract_node_table(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从分类结果中提取节点表"""
        return result.get("node_table", [])

    def _fallback_classify(self, essay_text: str, adu_list: List[Dict]) -> Dict[str, Any]:
        """降级方案：基于位置的启发式分类（不依赖 LLM）"""
        node_table = []
        total = len(adu_list)
        for i, adu in enumerate(adu_list):
            text = adu.get("text", "")
            seg_id = adu.get("id", f"S{i+1}")

            # 启发式规则：
            # - 第一个/最后一个 ADU → 可能是 MC
            # - 含"因此""所以""由此可见"→ analysis（总结性）
            # - 含书名号/引号的人名 → evidence
            # - 默认 → analysis
            if i == 0 or i == total - 1:
                ntype = "major_claim" if i == 0 else "analysis"
            elif any(kw in text for kw in ["因此", "所以", "由此可见", "综上所述"]):
                ntype = "analysis"
            elif ("《" in text and "》" in text) or any(name in text for name in ["孔子", "孟子", "苏轼", "鲁迅", "王充", "冯友兰", "陶渊明"]):
                ntype = "evidence"
            elif i % 3 == 0:
                ntype = "paragraph_claim"
            else:
                ntype = "analysis"

            node_table.append({
                "node_id": seg_id,
                "original_id": seg_id,
                "text": text,
                "type": ntype,
                "reasoning": ["[降级] 启发式规则分类"]
            })

        # 确保只有一个 MC
        mc_count = sum(1 for n in node_table if n["type"] == "major_claim")
        if mc_count > 1:
            for n in node_table[1:]:
                if n["type"] == "major_claim":
                    n["type"] = "analysis"

        return {"node_table": node_table}

    def get_mc(self, node_table: List[Dict]) -> Optional[Dict]:
        """从节点表中提取 MC"""
        for node in node_table:
            if node.get("type") == self.MAJOR_CLAIM or node.get("node_id") == "MC":
                return node
        return None

    def get_paragraph_claims(self, node_table: List[Dict]) -> List[Dict]:
        """从节点表中提取所有段落 Claim"""
        return [
            node for node in node_table
            if node.get("type") == self.PARAGRAPH_CLAIM
        ]

    def has_valid_mc(self, node_table: List[Dict]) -> bool:
        """检查是否成功识别出 MC"""
        return self.get_mc(node_table) is not None

    def count_paragraphs_with_claims(self, node_table: List[Dict]) -> int:
        """统计有段落 Claim 的段落数"""
        claims = self.get_paragraph_claims(node_table)
        return len(claims)


def create_component_classifier(client: OpenAI) -> ComponentClassifier:
    """工厂函数：创建 Component Classifier 实例"""
    return ComponentClassifier(client)
