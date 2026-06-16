"""JSON 解析与修复工具。

处理 LLM 输出中常见的 JSON 格式问题：
- Markdown code block 包裹（```json ... ```）
- 多余逗号（trailing comma）
- 中文引号混入
- 未闭合的括号
"""

import json
import re
from typing import Any, Dict, Optional


def extract_json(text: str) -> str:
    """从 LLM 输出中提取 JSON 内容。

    处理常见情况：
    1. 纯 JSON 文本
    2. ```json ... ``` 包裹
    3. ``` ... ``` 包裹
    4. JSON 前后有解释性文字
    """
    text = text.strip()

    # 1. 尝试提取 ```json ... ``` 块
    match = re.search(r'```json\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 2. 尝试提取 ``` ... ``` 块
    match = re.search(r'```\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 3. 尝试找到第一个 { 和最后一个 }
    first_brace = text.find('{')
    first_bracket = text.find('[')
    if first_brace == -1 and first_bracket == -1:
        return text

    if first_brace >= 0 and (first_bracket == -1 or first_brace < first_bracket):
        # JSON object
        last_brace = text.rfind('}')
        if last_brace > first_brace:
            return text[first_brace:last_brace + 1]
    else:
        # JSON array
        last_bracket = text.rfind(']')
        if last_bracket > first_bracket:
            return text[first_bracket:last_bracket + 1]

    return text


def _escape_chinese_quotes_in_json(json_text: str) -> str:
    """将 JSON 字符串值内部的中文引号风格 ASCII 双引号转为转义形式。

    DeepSeek 经常输出类似 "text": "他说："坚持就是胜利"" 的 JSON，
    其中内部的 ASCII 双引号会破坏 JSON 结构。
    此函数将这些内部引号替换为中文弯引号。
    """
    # 策略：在 JSON 字符串值的上下文中，
    # 紧跟在中文/标点后或紧跟中文/标点前的 ASCII " 转为中文弯引号
    # 模式: 中文字符后的 "  → 可能是右引号，中文字符前的 " → 可能是左引号
    result = []
    in_string = False
    escape_next = False
    prev_char = ''

    for i, ch in enumerate(json_text):
        if escape_next:
            result.append(ch)
            escape_next = False
            prev_char = ch
            continue

        if ch == '\\':
            result.append(ch)
            escape_next = True
            prev_char = ch
            continue

        if ch == '"':
            if not in_string:
                result.append(ch)
                in_string = True
                prev_char = ch
                continue

            # 在字符串内部：检查下一个非空白字符
            # 如果下一个字符是 : 或 , 或 } 或 ]，说明这个 " 是字符串结束
            rest = json_text[i+1:].lstrip()
            if rest and rest[0] in ': ,}]':
                result.append(ch)
                in_string = False
                prev_char = ch
                continue

            # 在字符串内部但看起来像中文引号：替换为弯引号
            # 检查前一个字符是否为中文字符（或中文标点）
            if _is_cjk_or_punct(prev_char):
                # 前一个是中文 → 这是右引号 → 替换为 」
                result.append('\u201d')  # ”
                prev_char = '\u201d'
                continue
            else:
                # 前一个不是中文 → 检查后一个
                if i + 1 < len(json_text) and _is_cjk_or_punct(json_text[i+1]):
                    # 后一个是中文 → 这是左引号 → 替换为 「
                    result.append('\u201c')  # "
                    prev_char = '\u201c'
                    continue
                # 无法判断，保留原样
                result.append(ch)
                prev_char = ch
                continue

        result.append(ch)
        prev_char = ch

    return ''.join(result)


def _is_cjk_or_punct(ch: str) -> bool:
    """判断字符是否为 CJK 字符或中文标点"""
    cp = ord(ch)
    return (
        (0x4E00 <= cp <= 0x9FFF) or   # CJK 统一汉字
        (0x3400 <= cp <= 0x4DBF) or   # CJK 扩展 A
        (0x3000 <= cp <= 0x303F) or   # CJK 标点符号
        (0xFF00 <= cp <= 0xFFEF) or   # 全角字符
        (0x2000 <= cp <= 0x206F) or   # 通用标点
        (0x2E80 <= cp <= 0x2EFF)      # CJK 部首补充
    )


def fix_json(text: str) -> str:
    """修复常见 JSON 格式错误"""
    # 1. 关键修复：将 JSON 字符串值内部的 ASCII 双引号（中文引号风格）转为弯引号
    #    DeepSeek 常输出 {"text":"他说："坚持就是胜利""}——内部 " 破坏 JSON 结构
    #    转为弯引号后 {"text":"他说："坚持就是胜利""} JSON 可正确解析
    text = _escape_chinese_quotes_in_json(text)

    # 2. 移除行内注释（// ...）
    text = re.sub(r'//[^\n]*', '', text)

    # 3. 修复 trailing comma（, ] 和 , }）
    text = re.sub(r',\s*(\}|\])', r'\1', text)

    # 4. 修复缺失逗号：在两个字符串之间
    text = re.sub(r'"\s*\n\s*"', '",\n"', text)

    return text


def parse_json_response(text: str, max_attempts: int = 3) -> Dict[str, Any]:
    """解析 LLM 输出为 Python 字典，带多次修复尝试。

    Args:
        text: LLM 原始输出文本
        max_attempts: 最大修复尝试次数

    Returns:
        解析后的 Python 字典

    Raises:
        ValueError: 如果所有尝试均失败
    """
    errors = []
    for attempt in range(max_attempts):
        try:
            if attempt == 0:
                extracted = extract_json(text)
            elif attempt == 1:
                extracted = fix_json(extract_json(text))
            else:
                # 最后尝试：更激进的修复
                extracted = fix_json(extract_json(text))
                # 尝试使用 ast.literal_eval 作为备选
                try:
                    import ast
                    return ast.literal_eval(extracted)
                except Exception:
                    pass

            return json.loads(extracted)
        except json.JSONDecodeError as e:
            errors.append(f"尝试 {attempt + 1}: {e}")
            if attempt == max_attempts - 1:
                raise ValueError(
                    f"JSON 解析失败（{max_attempts} 次尝试）:\n" +
                    "\n".join(errors) +
                    f"\n\n原始输出前 500 字符:\n{text[:500]}"
                )
    return {}
