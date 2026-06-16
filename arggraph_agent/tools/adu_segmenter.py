"""Tool 1: ADU Segmenter（论证单元切分器）

对应 SOP §1（ADU 划分规则）、§2（分析范围）

实现逻辑（两阶段混合方案）：
1. 正则预处理：按句号类标点进行一级切分
2. LLM 精细切分：识别关联词触发二级切分

这种两阶段设计结合了规则方法的效率和 LLM 的语义理解能力。
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI

from ..utils.api_client import chat_completion
from ..utils.json_parser import parse_json_response
from ..prompts.tool1_prompt import TOOL1_PROMPT, build_tool1_messages


# 一级切分标点
SENTENCE_BOUNDARIES = re.compile(r'[。？！；]')


def preprocess_paragraphs(text: str) -> List[str]:
    """将文本按自然段分解为 {P1, P2, ..., Pn}。

    首先尝试按双换行分段，如果只有一段，则按单换行分段。
    """
    text = text.strip()
    # 先按双换行分段
    paragraphs = re.split(r'\n\s*\n', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    # 如果只有一段，按单换行分段
    if len(paragraphs) <= 1:
        paragraphs = re.split(r'\n', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

    return paragraphs


def base_segmentation(text: str) -> List[str]:
    """一级切分：按句号类标点切分为基础句。

    使用 lookahead 保留标点符号在句尾。
    """
    sentences = re.split(r'(?<=[。？！；])\s*', text)
    return [s.strip() for s in sentences if s.strip()]


def detect_connectors(text: str) -> List[Tuple[str, str]]:
    """检测关联词模式，返回 [(模式名, 匹配文本), ...]。

    常用的关联词组合模式。
    """
    patterns = [
        (r'(因为|由于).*?(所以|因此|因而)', '因果'),
        (r'(虽然|尽管).*?(但是|但|然而|却)', '转折'),
        (r'(如果|假如|倘若).*?(那么|就|则)', '假设'),
        (r'(不是|并非).*?(而是)', '并列否定'),
        (r'(不仅|不但).*?(而且|并且|还)', '递进'),
        (r'(一方面).*?(另一方面)', '并列'),
        (r'(例如|比如|譬如).*?(这说[明明])', '例证'),
    ]

    found = []
    for pattern, name in patterns:
        match = re.search(pattern, text)
        if match:
            found.append((name, match.group(0)))
    return found


def is_likely_argumentative(text: str) -> bool:
    """快速判断文本是否可能是议论文。

    简单启发式：检查议论文常见特征词。
    """
    markers = [
        '因此', '所以', '可见', '应当', '应该',
        '因为', '但是', '然而', '例如', '比如',
        '首先', '其次', '最后', '总之',
        '论点', '论证', '论据',
    ]
    count = sum(1 for m in markers if m in text)
    return count >= 2


class ADUSegmenter:
    """ADU 切分器"""

    def __init__(self, client: OpenAI):
        self.client = client

    def segment(self, essay_text: str, essay_topic: Optional[str] = None) -> Dict[str, Any]:
        """执行 ADU 切分。

        Args:
            essay_text: 原始议论文文本
            essay_topic: 作文题目（可选）

        Returns:
            切分结果字典
        """
        # 预处理：按段落分解
        paragraphs = preprocess_paragraphs(essay_text)

        # 第一阶段：正则一级切分
        base_segments = []
        for i, para in enumerate(paragraphs):
            sentences = base_segmentation(para)
            for j, sent in enumerate(sentences):
                base_segments.append({
                    "para_index": i + 1,
                    "sent_index": j + 1,
                    "text": sent,
                    "connectors": detect_connectors(sent),
                })

        # 第二阶段：LLM 精细切分
        # 构建 LLM 消息
        messages = build_tool1_messages(essay_text)

        try:
            response = chat_completion(self.client, messages, temperature=0.2, max_tokens=8192)
            result = parse_json_response(response)
            return result
        except Exception as e:
            # LLM 切分失败时，降级为纯正则切分
            print(f"  [Tool 1 降级] LLM 切分失败 ({e})，使用正则切分结果")
            return self._fallback_segmentation(base_segments, paragraphs)

    def _fallback_segmentation(
        self, base_segments: list, paragraphs: list
    ) -> Dict[str, Any]:
        """降级方案：纯正则切分"""
        segments = []
        for seg in base_segments:
            segments.append({
                "id": f"P{seg['para_index']}_S{seg['sent_index']}",
                "text": seg["text"],
            })

        return {
            "segments": segments,
            "paragraph_count": len(paragraphs),
            "total_adus": len(segments),
        }


def create_adu_segmenter(client: OpenAI) -> ADUSegmenter:
    """工厂函数：创建 ADU Segmenter 实例"""
    return ADUSegmenter(client)
