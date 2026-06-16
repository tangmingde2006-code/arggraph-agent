"""对话历史管理器。

管理 Agent 的 messages 列表：
- 滑动窗口策略：防止 Token 超限
- 关键信息保留：MC、段落 Claim 不丢弃
- Token 计数
"""

from typing import List, Dict, Any, Tuple


MAX_CONTEXT_TOKENS = 80000  # 保留安全裕度（DeepSeek-v3 支持 128K）
AVG_CHARS_PER_TOKEN = 2.0   # 中文字符到 token 的粗略估算


def estimate_tokens(messages: List[Dict[str, str]]) -> int:
    """估算 messages 的总 token 数"""
    total_chars = sum(len(m.get("content", "")) for m in messages)
    return int(total_chars / AVG_CHARS_PER_TOKEN)


def manage_context(
    messages: List[Dict[str, str]],
    max_tokens: int = MAX_CONTEXT_TOKENS,
    preserve_key_info: bool = True,
) -> List[Dict[str, str]]:
    """管理对话上下文，必要时进行滑动窗口截断。

    策略：
    1. System Prompt 永不丢弃
    2. 最后一条 user 消息永不丢弃
    3. 从旧到新截断 assistant 和 tool 消息
    4. 保留包含"MC""P?_C""节点表""边表"等关键信息标记的消息

    Args:
        messages: 完整消息列表
        max_tokens: 最大 token 限制
        preserve_key_info: 是否保留关键信息

    Returns:
        截断后的消息列表
    """
    if estimate_tokens(messages) <= max_tokens:
        return messages

    key_markers = ["MC", "major_claim", "P?_C", "paragraph_claim",
                   "节点表", "node_table", "边表", "edge_table",
                   "Argument Graph"]

    system_msg = None
    last_user_msg = None
    middle_msgs = []

    for msg in messages:
        if msg["role"] == "system" and system_msg is None:
            system_msg = msg
        elif msg is messages[-1] and msg["role"] == "user":
            last_user_msg = msg
        else:
            middle_msgs.append(msg)

    # 从旧到新截断中间消息
    result = [system_msg] if system_msg else []
    budget = max_tokens - estimate_tokens(result) - estimate_tokens([last_user_msg] if last_user_msg else [])

    for msg in reversed(middle_msgs):
        if preserve_key_info and any(m in str(msg.get("content", "")) for m in key_markers):
            # 关键信息消息优先保留
            result.append(msg)
            budget -= estimate_tokens([msg])
        elif budget > 0:
            result.append(msg)
            budget -= estimate_tokens([msg])
        if budget <= 0:
            break

    if last_user_msg:
        result.append(last_user_msg)

    return result
