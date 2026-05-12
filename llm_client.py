"""
统一 LLM 客户端适配器 — 屏蔽 OpenAI / Anthropic 协议差异

对外暴露与 openai.OpenAI 完全一致的 chat.completions.create() 接口，
内部根据协议自动路由到对应 SDK。
"""

import os


def create_client(api_key: str, base_url: str, protocol: str = "openai"):
    """
    创建统一 LLM 客户端。

    Args:
        api_key: API Key
        base_url: API 端点地址
        protocol: "openai" 或 "anthropic"

    Returns:
        具有 chat.completions.create() 接口的客户端对象
    """
    if protocol == "anthropic":
        return _AnthropicWrapper(api_key, base_url)
    else:
        from openai import OpenAI
        return OpenAI(api_key=api_key, base_url=base_url)


# ═══════════════════════════════════════════
#  Anthropic → OpenAI 接口适配层
# ═══════════════════════════════════════════

class _AnthropicWrapper:
    """将 anthropic.Anthropic 包装成 openai.OpenAI 的接口形态。"""

    def __init__(self, api_key: str, base_url: str):
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic 包未安装，请运行: pip install anthropic"
            )
        self._client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
        self.chat = _AnthropicChat(self._client)


class _AnthropicChat:
    def __init__(self, client):
        self._client = client
        self.completions = _AnthropicCompletions(client)


class _AnthropicCompletions:
    def __init__(self, client):
        self._client = client

    def create(self, *, model: str, messages: list, max_tokens: int = 4096,
               temperature: float = 0.2, **kwargs):
        # 从 messages 中分离 system prompt
        system_text = ""
        user_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_text += msg.get("content", "") + "\n"
            else:
                user_messages.append(msg)

        # 调用 Anthropic API
        params = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": user_messages,
        }
        if system_text.strip():
            params["system"] = system_text.strip()

        response = self._client.messages.create(**params)

        # 包装成 OpenAI 风格的响应对象
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        return _OpenAIStyleResponse(text, model)


class _OpenAIStyleResponse:
    """模拟 openai ChatCompletion 响应结构。"""

    def __init__(self, text: str, model: str):
        self.choices = [_OpenAIStyleChoice(text)]
        self.model = model
        self.usage = None


class _OpenAIStyleChoice:
    def __init__(self, text: str):
        self.message = _OpenAIStyleMessage(text)


class _OpenAIStyleMessage:
    def __init__(self, content: str):
        self.content = content
        self.role = "assistant"
