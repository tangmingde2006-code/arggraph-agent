"""API 调用封装：DeepSeek 兼容的 openai SDK 客户端。

支持：
- 自动重试（最多 3 次）+ 指数退避
- 超时控制
- 流式输出（进阶）
"""

import os
import time
from typing import Optional, List, Dict, Any
from openai import OpenAI


DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

MAX_RETRIES = 3
BASE_DELAY = 2.0  # 基础退避延迟（秒）
TIMEOUT = 120


def get_api_key() -> str:
    """获取 DeepSeek API Key。

    优先级：环境变量 DEEPSEEK_API_KEY > .env 文件
    """
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key

    # 尝试从 .env 文件读取
    env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DEEPSEEK_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def create_client(api_key: Optional[str] = None) -> OpenAI:
    """创建 DeepSeek API 客户端"""
    key = api_key or get_api_key()
    if not key:
        raise ValueError(
            "未找到 DeepSeek API Key！请设置环境变量 DEEPSEEK_API_KEY，"
            "或在 arggraph_agent/ 目录下创建 .env 文件，内容为：\n"
            "DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx"
        )
    return OpenAI(api_key=key, base_url=DEEPSEEK_BASE_URL, timeout=TIMEOUT)


def chat_completion(
    client: OpenAI,
    messages: List[Dict[str, str]],
    temperature: float = 0.3,
    max_tokens: int = 4096,
    max_retries: int = MAX_RETRIES,
) -> str:
    """发送 chat completion 请求，带自动重试。

    Args:
        client: OpenAI 客户端
        messages: 对话历史列表
        temperature: 生成温度（越低越确定）
        max_tokens: 最大输出 token 数
        max_retries: 最大重试次数

    Returns:
        LLM 输出的文本内容
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = BASE_DELAY * (2 ** attempt)  # 指数退避
                print(f"  [API 重试 {attempt + 1}/{max_retries}] {e}，{delay:.0f}秒后重试...")
                time.sleep(delay)
            else:
                raise RuntimeError(
                    f"API 调用失败（已重试 {max_retries} 次）: {last_error}"
                ) from last_error
    return ""
