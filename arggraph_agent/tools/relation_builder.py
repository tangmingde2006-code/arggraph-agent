"""Tool 3: Relation Builder（论证关系构建器）

对应 SOP §7（关系类型定义）、§8（段内关系规则）、§9（C→MC 关系）、
§10（段间关系）、§11（关系标记符号）、§12（图的构造方法）、
§13（完整输出模板）、§14（一致性检查）

实现逻辑：
1. C→MC 关系构建（全文骨架）
2. 段内关系构建（A→C, E→C, EA→E）
3. 段间关系构建（仅在有明确标志词时）
4. 生成完整输出（节点表 + 边表 + 树状图 + Mermaid + 总结）
5. 一致性检查
"""

from typing import Dict, Any, List
from openai import OpenAI

from ..utils.api_client import chat_completion
from ..utils.json_parser import parse_json_response
from ..prompts.tool3_prompt import TOOL3_PROMPT, build_tool3_messages


class RelationBuilder:
    """论证关系构建器"""

    def __init__(self, client: OpenAI):
        self.client = client

    def build(
        self,
        essay_text: str,
        node_table: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """执行论证关系构建。

        Args:
            essay_text: 原始全文
            node_table: 节点表

        Returns:
            关系构建结果字典，含 edge_table / tree_graph / mermaid_code / consistency_check / summary
        """
        messages = build_tool3_messages(essay_text, node_table)

        try:
            response = chat_completion(self.client, messages, temperature=0.2, max_tokens=16384)
            result = parse_json_response(response)
            return result
        except ValueError as e:
            # JSON 解析失败时，保存原始输出到文件供调试
            import os, datetime
            debug_dir = os.path.join(os.path.dirname(__file__), "..", "outputs")
            os.makedirs(debug_dir, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = os.path.join(debug_dir, f"tool3_raw_{ts}.txt")
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(response)
            raise RuntimeError(f"关系构建失败: {e}\n原始输出已保存到 {debug_file}")
        except Exception as e:
            raise RuntimeError(f"关系构建失败: {e}")

    def extract_edge_table(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从构建结果中提取边表"""
        return result.get("edge_table", [])

    def extract_tree_graph(self, result: Dict[str, Any]) -> str:
        """从构建结果中提取树状图"""
        return result.get("tree_graph", "")

    def extract_mermaid(self, result: Dict[str, Any]) -> str:
        """从构建结果中提取 Mermaid 代码"""
        return result.get("mermaid_code", "")

    def extract_summary(self, result: Dict[str, Any]) -> str:
        """从构建结果中提取论证结构总结"""
        return result.get("summary", "")

    def check_consistency(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """从构建结果中提取一致性检查报告"""
        return result.get("consistency_check", {
            "all_claims_connected_to_mc": False,
            "all_evidence_connected": False,
            "orphan_nodes": [],
            "cycles_detected": True,
        })


def create_relation_builder(client: OpenAI) -> RelationBuilder:
    """工厂函数：创建 Relation Builder 实例"""
    return RelationBuilder(client)
