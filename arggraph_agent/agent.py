"""ArgGraph-Agent 主循环（真 ReAct 范式）

真正的 ReAct（Reasoning + Acting）循环：
- Thought: LLM 分析当前状态，决定下一步调用哪个工具
- Action: 执行工具调用
- Observation: 获取工具返回结果
- 循环直到任务完成（所有必要工具已调用，且输出完整）

可用工具：
  - adu_segmenter:  切分议论文为论证单元（ADU）
  - component_classifier: 对 ADU 进行组件分类（MC/C/A/E/EA）
  - relation_builder: 构建论证关系图（边表+树+Mermaid）
  - consistency_check: 本地图算法一致性验证（无需 LLM）

结束条件：
  - 已调用 relation_builder 且输出完整论证图
  - 或达到最大轮次上限（防止死循环）
"""

import json
from typing import Dict, Any, Optional, List
from openai import OpenAI

from .utils.api_client import create_client, get_api_key
from .tools.adu_segmenter import create_adu_segmenter
from .tools.component_classifier import create_component_classifier
from .tools.relation_builder import create_relation_builder
from .validators.consistency_check import run_consistency_check


# ── 工具注册表 ───────────────────────────────────────────────
TOOL_REGISTRY = {
    "adu_segmenter": {
        "description": "切分议论文为论证单元（ADU）。输入：essay_text（全文）、essay_topic（可选）。输出：segments 列表。",
        "required_after": [],
    },
    "component_classifier": {
        "description": "对 ADU 进行组件分类（MC/C/A/E/EA）。输入：segments 列表、essay_text、essay_topic。输出：node_table 列表。",
        "required_after": ["adu_segmenter"],
    },
    "relation_builder": {
        "description": "构建论证关系图。输入：node_table 列表、essay_text。输出：edge_table、tree_graph、mermaid_code、summary。",
        "required_after": ["component_classifier"],
    },
    "consistency_check": {
        "description": "本地图算法一致性验证（BFS可达性+DFS环检测+孤立节点）。输入：node_table、edge_table。输出：passed、issues等。",
        "required_after": ["relation_builder"],
        "is_local": True,   # 本地算法，不消耗 LLM 调用
    },
}

# ReAct 决策 Prompt 模板
REACT_SYSTEM_PROMPT = """你是一个高考议论文论证结构分析专家，使用 ReAct（Reasoning + Acting）范式逐步完成分析任务。

## 你的目标
将一篇议论文拆解为论证图（Argument Graph），包含：
1. ADU 切分（论证单元）
2. 组件分类（MC / paragraph_claim / analysis / evidence / evidence_analysis）
3. 关系构建（support / attack / explain / example-of / extend / parallel 等）
4. 一致性检查

## 可用工具
{tool_descriptions}

## 工作规则
- 你必须按顺序逐步调用工具，不能跳过依赖。
- adu_segmenter 必须在 component_classifier 之前调用。
- component_classifier 必须在 relation_builder 之前调用。
- relation_builder 完成后，可以调用 consistency_check 做验证。
- 每次回复必须严格遵循以下格式（不多不少）：

Thought: <分析当前状态，决定下一步>
Action: <工具名>
Action Input: <JSON 格式的输入参数>

或者，如果任务已完成（已调用 relation_builder 且输出完整论证图），则回复：

Thought: <说明任务已完成>
Final Answer: <完整的论证图 JSON，含 node_table、edge_table、tree_graph、mermaid_code、summary>

## 禁止
- 不得在 Action 之外自行编造分析结果。工具返回的数据就是完整的，不要怀疑被截断。
- 不得一次调用多个工具。
- 不得跳过 Thought 直接输出 Action。
- 不得"手动补全"或"推断"工具未返回的内容——工具输出是权威的，你没有权力覆盖它。
- 如果工具执行正常，直接处理其结果即可，不需要纠结格式或完整性。"""


REACT_USER_PROMPT = """## 输入议论文

作文题目（可选）：{essay_topic}

议论文全文：
{essay_text}

## 当前状态

已调用的工具及结果摘要：
{state_summary}

请决定下一步操作。严格遵守 ReAct 格式。"""


class ArgGraphAgent:
    """基于真 ReAct 范式的论证图自动拆解 Agent。

    接收一篇高考议论文，通过 LLM 动态决策调用工具，
    逐步生成 Argument Graph。
    """

    def __init__(self, api_key: Optional[str] = None, max_turns: int = 15):
        self.api_key = api_key or get_api_key()
        self.client = create_client(self.api_key)
        self.max_turns = max_turns

        # 初始化工具实例
        self.segmenter = create_adu_segmenter(self.client)
        self.classifier = create_component_classifier(self.client)
        self.builder = create_relation_builder(self.client)

        # 状态：保存各工具的输出
        self.state: Dict[str, Any] = {}
        self.tool_history: List[Dict[str, Any]] = []

    def _build_tool_descriptions(self) -> str:
        lines = []
        for name, meta in TOOL_REGISTRY.items():
            lines.append(f"- {name}: {meta['description']}")
        return "\n".join(lines)

    def _build_state_summary(self) -> str:
        if not self.tool_history:
            return "（尚未调用任何工具）"
        lines = []
        for h in self.tool_history:
            lines.append(f"  第{h['turn']}轮：调用 {h['tool']}，输出摘要：{h['summary']}")
        return "\n".join(lines)

    def _call_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用，返回工具输出。"""
        if tool_name == "adu_segmenter":
            return self.segmenter.segment(
                tool_input.get("essay_text", ""),
                tool_input.get("essay_topic"),
            )
        elif tool_name == "component_classifier":
            return self.classifier.classify(
                tool_input.get("essay_text", ""),
                tool_input.get("essay_topic"),
                tool_input.get("segments", []),
            )
        elif tool_name == "relation_builder":
            return self.builder.build(
                tool_input.get("essay_text", ""),
                tool_input.get("node_table", []),
            )
        elif tool_name == "consistency_check":
            node_table = tool_input.get("node_table", [])
            edge_table = tool_input.get("edge_table", [])
            return run_consistency_check(node_table, edge_table)
        else:
            raise ValueError(f"未知工具：{tool_name}")

    def _summarize_result(self, tool_name: str, result: Dict[str, Any]) -> str:
        """生成工具输出的简短摘要，供 LLM 上下文使用（节省 token）。"""
        if tool_name == "adu_segmenter":
            segs = result.get("segments", [])
            return f"切得 {len(segs)} 个 ADU，段落数 {result.get('paragraph_count', '?')}。"
        elif tool_name == "component_classifier":
            nodes = result.get("node_table", [])
            type_count = {}
            for n in nodes:
                t = n.get("type", "?")
                type_count[t] = type_count.get(t, 0) + 1
            return f"分类得 {len(nodes)} 个节点：" + "，".join(
                f"{t} × {c}" for t, c in type_count.items()
            )
        elif tool_name == "relation_builder":
            edges = result.get("edge_table", [])
            return f"构建 {len(edges)} 条关系边，生成论证树和 Mermaid 图。"
        elif tool_name == "consistency_check":
            passed = result.get("passed", False)
            return f"一致性检查{'通过' if passed else '未通过'}：" + "；".join(result.get("issues", []))[:80]
        return "输出已获取。"

    def _parse_react_response(self, response_text: str) -> Dict[str, Any]:
        """解析 LLM 的 ReAct 格式回复，提取 Thought / Action / Final Answer。"""
        result = {
            "thought": "",
            "action": None,        # 工具名
            "action_input": None,   # 工具输入 dict
            "final_answer": None,   # 最终答案（如有）
            "is_final": False,
        }

        lines = response_text.strip().split("\n")

        # 提取 Thought
        in_thought = False
        thought_lines = []
        for line in lines:
            if line.startswith("Thought:"):
                in_thought = True
                thought_lines.append(line[len("Thought:"):].strip())
            elif in_thought and (line.startswith("Action:") or line.startswith("Final Answer:")):
                in_thought = False
            elif in_thought:
                thought_lines.append(line.strip())

        result["thought"] = " ".join(thought_lines).strip()

        # 提取 Action 或 Final Answer
        in_action_input = False
        action_input_lines = []

        for i, line in enumerate(lines):
            if line.startswith("Action:") and not result["is_final"]:
                result["action"] = line[len("Action:"):].strip()
            elif line.startswith("Action Input:"):
                in_action_input = True
                action_input_lines.append(line[len("Action Input:"):].strip())
            elif in_action_input:
                if line.startswith("Thought:") or line.startswith("Action:") or line.startswith("Final Answer:"):
                    in_action_input = False
                else:
                    action_input_lines.append(line.strip())
            elif line.startswith("Final Answer:"):
                result["is_final"] = True
                fa = line[len("Final Answer:"):].strip()
                # 收集后续所有行
                fa_lines = [fa]
                for subsequent in lines[i+1:]:
                    if not (subsequent.startswith("Thought:") or subsequent.startswith("Action:")):
                        fa_lines.append(subsequent.strip())
                result["final_answer"] = "\n".join(fa_lines).strip()

        # 解析 Action Input JSON
        if action_input_lines:
            raw = " ".join(action_input_lines).strip()
            try:
                result["action_input"] = json.loads(raw)
            except json.JSONDecodeError:
                # 尝试修复：去掉可能的代码块包裹
                cleaned = raw.replace("```json", "").replace("```", "").strip()
                try:
                    result["action_input"] = json.loads(cleaned)
                except Exception:
                    result["action_input"] = {"_raw": raw}

        return result

    def analyze(
        self,
        essay_text: str,
        essay_topic: Optional[str] = None,
        verbose: bool = True,
    ) -> Dict[str, Any]:
        """使用真 ReAct 循环分析议论文。

        Args:
            essay_text: 议论文全文
            essay_topic: 作文题目（可选）
            verbose: 是否打印中间步骤

        Returns:
            完整的分析结果字典
        """
        self.state = {
            "essay_text": essay_text,
            "essay_topic": essay_topic,
        }
        self.tool_history = []

        result = {
            "input": {"essay_text": essay_text, "essay_topic": essay_topic},
            "segmentation": None,
            "classification": None,
            "graph": None,
            "consistency": None,
            "summary": None,
            "errors": [],
            "react_trace": [],   # 保存 ReAct 完整轨迹
        }

        # 构建 system prompt
        system_prompt = REACT_SYSTEM_PROMPT.format(
            tool_descriptions=self._build_tool_descriptions()
        )

        # 对话上下文（ messages ）
        messages = [
            {"role": "system", "content": system_prompt},
        ]

        for turn in range(1, self.max_turns + 1):
            if verbose:
                print(f"\n┌{'─' * 58}┐")
                print(f"│  🧠 ReAct 第 {turn} 轮".ljust(36) + f"{'│':>25}")
                print(f"└{'─' * 58}┘")

            # 构建 user prompt（含当前状态摘要）
            user_prompt = REACT_USER_PROMPT.format(
                essay_topic=essay_topic or "（无）",
                essay_text=essay_text,
                state_summary=self._build_state_summary(),
            )
            messages.append({"role": "user", "content": user_prompt})

            # 调用 LLM 决策
            try:
                llm_response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages,
                    temperature=0.1,   # 低温度，保证格式稳定
                    max_tokens=2000,
                )
                response_text = llm_response.choices[0].message.content
            except Exception as e:
                msg = f"LLM 调用失败（第 {turn} 轮）：{e}"
                result["errors"].append(msg)
                if verbose:
                    print(f"  ✗ {msg}")
                break

            # 解析 ReAct 回复
            parsed = self._parse_react_response(response_text)

            # 保存轨迹
            trace_entry = {
                "turn": turn,
                "thought": parsed["thought"],
                "action": parsed["action"],
                "action_input": parsed["action_input"],
                "is_final": parsed["is_final"],
                "llm_raw": response_text,
            }
            result["react_trace"].append(trace_entry)

            if verbose:
                # ── 展示 LLM 原始决策 ──
                print(f"  ┌─ LLM 原始决策")
                # 显示 raw response 截断
                raw_preview = response_text.replace("\n", "\n  │ ").strip()
                max_raw = 400
                if len(raw_preview) > max_raw:
                    raw_preview = raw_preview[:max_raw] + f"\n  │ ...（共 {len(response_text)} 字，已截断）"
                print(f"  │ {raw_preview}")
                print(f"  └{'─' * 50}")
                # ── 结构化展示 ──
                print(f"  💭 Thought: {parsed['thought'][:100]}")
                if parsed["action"]:
                    print(f"  🔧 Action: {parsed['action']}")
                    ai_preview = json.dumps(parsed["action_input"], ensure_ascii=False)[:120] if parsed["action_input"] else "（无）"
                    print(f"     Action Input: {ai_preview}")
                if parsed["is_final"]:
                    print(f"  ✅ Final Answer 已生成")

            # 如果 LLM 判定任务完成
            if parsed["is_final"]:
                # 尝试从 Final Answer 解析完整结果
                try:
                    fa = json.loads(parsed["final_answer"])
                    result["graph"] = fa
                    result["summary"] = fa.get("summary", "")
                except (json.JSONDecodeError, TypeError):
                    result["summary"] = parsed["final_answer"]
                break

            # 执行工具调用
            if not parsed["action"]:
                # LLM 未输出 Action，将情况反馈给它
                messages.append({
                    "role": "assistant",
                    "content": response_text,
                })
                messages.append({
                    "role": "user",
                    "content": "你的回复格式不正确。请严格按照 ReAct 格式输出：Thought / Action / Action Input，或 Thought / Final Answer。",
                })
                continue

            tool_name = parsed["action"]
            tool_input = parsed["action_input"] or {}

            # 补全工具输入（从 state 中取）
            self._fill_tool_input(tool_name, tool_input, essay_text, essay_topic)

            try:
                tool_output = self._call_tool(tool_name, tool_input)
            except Exception as e:
                msg = f"工具 {tool_name} 执行失败（第 {turn} 轮）：{e}"
                result["errors"].append(msg)
                if verbose:
                    print(f"  ✗ {msg}")
                # 将错误反馈给 LLM
                messages.append({"role": "assistant", "content": response_text})
                messages.append({
                    "role": "user",
                    "content": f"工具执行出错：{e}。请检查输入格式后重试，或说明无法继续的原因。",
                })
                continue

            # 保存状态
            self._update_state(tool_name, tool_output)
            self.tool_history.append({
                "turn": turn,
                "tool": tool_name,
                "summary": self._summarize_result(tool_name, tool_output),
            })

            # 将工具结果加入上下文（完整输出，不截断）
            obs_full = json.dumps(tool_output, ensure_ascii=False, indent=2, default=str)
            obs_text = f"Observation: 工具 {tool_name} 返回完整结果（共 {len(obs_full)} 字）：\n{obs_full}"
            messages.append({"role": "assistant", "content": response_text})
            messages.append({"role": "user", "content": obs_text})

            if verbose:
                summary = self._summarize_result(tool_name, tool_output)
                # 展示更详细的观察内容
                obs_preview = obs_full[:250].replace("\n", "\n  │ ")
                if len(obs_full) > 250:
                    obs_preview += f"\n  │ ...（共 {len(obs_full)} 字）"
                print(f"  ┌─ 👁 Observation: {summary}")
                print(f"  │ {obs_preview}")
                print(f"  └{'─' * 50}")

        # 结束后，整理最终结果
        result["segmentation"] = self.state.get("segments_result")
        result["classification"] = self.state.get("classification_result")
        result["graph"] = self.state.get("graph_result")
        result["consistency"] = self.state.get("consistency_result")
        if result["graph"]:
            result["summary"] = result["graph"].get("summary", "")

        # 如果未调用 consistency_check，自动执行
        if result["graph"] and not result.get("consistency"):
            try:
                node_table = result["graph"].get("node_table", [])
                edge_table = result["graph"].get("edge_table", [])
                consistency = run_consistency_check(node_table, edge_table)
                result["consistency"] = consistency
            except Exception:
                pass

        if verbose:
            print(f"\n{'=' * 60}")
            print("ReAct 分析完成")
            print(f"{'=' * 60}")
            # ── 全轨迹回顾 ──
            print(f"\n📋 ReAct 完整决策轨迹：")
            for entry in result.get("react_trace", []):
                icon = "✅" if entry["is_final"] else "🔧"
                action = entry.get("action", "—")
                print(f"  {icon} 第{entry['turn']}轮 → {action}  | {entry['thought'][:60]}")
            if result.get("summary"):
                print(f"\n📝 {result['summary']}")

        return result

    def _fill_tool_input(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        essay_text: str,
        essay_topic: Optional[str],
    ):
        """自动补全工具输入（从 agent 状态中取，避免 LLM 漏传参数）。"""
        if tool_name == "adu_segmenter":
            tool_input.setdefault("essay_text", essay_text)
            tool_input.setdefault("essay_topic", essay_topic)
        elif tool_name == "component_classifier":
            tool_input.setdefault("essay_text", essay_text)
            tool_input.setdefault("essay_topic", essay_topic)
            tool_input.setdefault("segments", self.state.get("segments_result", {}).get("segments", []))
        elif tool_name == "relation_builder":
            tool_input.setdefault("essay_text", essay_text)
            tool_input.setdefault("node_table", self.state.get("classification_result", {}).get("node_table", []))
        elif tool_name == "consistency_check":
            tool_input.setdefault("node_table", self.state.get("graph_result", {}).get("node_table", []))
            tool_input.setdefault("edge_table", self.state.get("graph_result", {}).get("edge_table", []))

    def _update_state(self, tool_name: str, tool_output: Dict[str, Any]):
        """将工具输出存入 agent 状态。"""
        if tool_name == "adu_segmenter":
            self.state["segments_result"] = tool_output
            # 同时存原始 segments 供后续工具使用
            self.state["_segments"] = tool_output.get("segments", [])
        elif tool_name == "component_classifier":
            self.state["classification_result"] = tool_output
            self.state["_node_table"] = tool_output.get("node_table", [])
        elif tool_name == "relation_builder":
            self.state["graph_result"] = tool_output
        elif tool_name == "consistency_check":
            self.state["consistency_result"] = tool_output

    def analyze_batch(
        self,
        essays: List[Dict[str, str]],
        verbose: bool = True,
    ) -> List[Dict[str, Any]]:
        """批量分析多篇议论文。"""
        results = []
        total = len(essays)
        for i, essay in enumerate(essays):
            if verbose:
                print(f"\n{'#' * 60}")
                print(f"样本 {i + 1}/{total}")
                print(f"{'#' * 60}")
            result = self.analyze(essay["text"], essay.get("topic"), verbose=verbose)
            results.append(result)
        return results

    def format_output(self, result: Dict[str, Any]) -> str:
        """格式化分析结果为可读文本。"""
        if result.get("errors"):
            return "分析过程中发生错误：\n" + "\n".join(result["errors"])

        lines = []
        lines.append("=" * 60)
        lines.append("ArgGraph-Agent 分析结果（真 ReAct 范式）")
        lines.append("=" * 60)

        # ReAct 轨迹
        if result.get("react_trace"):
            lines.append(f"\n{'─' * 60}")
            lines.append(f"🧠 ReAct 决策轨迹（共 {len(result['react_trace'])} 轮）")
            lines.append(f"{'─' * 60}")
            for entry in result["react_trace"]:
                icon = "✅" if entry["is_final"] else "🔧"
                action = entry.get("action", "—")
                thought_short = entry['thought'][:70]
                lines.append(f"  {icon} 第{entry['turn']}轮 → {action}")
                lines.append(f"     Thought: {thought_short}")
                if not entry["is_final"] and entry.get("action_input"):
                    ai = entry["action_input"]
                    if isinstance(ai, dict) and "_raw" not in ai:
                        lines.append(f"     Input: {json.dumps(ai, ensure_ascii=False)[:80]}")

        # 论证结构总结
        if result.get("summary"):
            lines.append(f"\n📝 论证结构总结：\n{result['summary']}")

        # 节点表
        nodes = (result.get("graph", {}) or {}).get("node_table", [])
        if not nodes:
            nodes = (result.get("classification", {}) or {}).get("node_table", [])
        if nodes:
            lines.append("\n📊 节点表：")
            for node in nodes:
                ntype = node.get("type", "?")
                lines.append(f"  [{ntype}] {node.get('node_id', '?')}: "
                             f"{node.get('text', '')[:60]}")

        # 边表
        edges = (result.get("graph", {}) or {}).get("edge_table", [])
        if edges:
            lines.append(f"\n🔗 关系边表（{len(edges)} 条）：")
            for edge in edges:
                lines.append(f"  {edge.get('from', '?')} --[{edge.get('relation', '?')}]--> "
                             f"{edge.get('to', '?')}")

        # 树状图
        tree = (result.get("graph", {}) or {}).get("tree_graph", "")
        if tree:
            lines.append(f"\n🌳 论证树：\n{tree}")

        # 一致性检查
        consistency = result.get("consistency", {})
        if consistency:
            status = "✅ 通过" if consistency.get("passed") else "❌ 未通过"
            lines.append(f"\n🔍 一致性检查：{status}")

        return "\n".join(lines)


def create_agent(api_key: Optional[str] = None, max_turns: int = 15) -> ArgGraphAgent:
    """工厂函数：创建 ArgGraphAgent 实例。"""
    return ArgGraphAgent(api_key, max_turns=max_turns)
