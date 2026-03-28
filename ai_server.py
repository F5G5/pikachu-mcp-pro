"""
Pikachu AI MCP Server ⚡
调用多种AI模型 - OpenAI/Claude/Gemini等
"""
from fastmcp import FastMCP
import urllib.request
import json
import os

mcp = FastMCP("PikachuAI")

# AI模型配置
_ai_config = {
    "openai_key": os.environ.get("OPENAI_API_KEY", ""),
    "anthropic_key": os.environ.get("ANTHROPIC_API_KEY", ""),
    "gemini_key": os.environ.get("GEMINI_API_KEY", "")
}

@mcp.tool()
def configure_ai(openai_key: str = "", anthropic_key: str = "", gemini_key: str = "") -> str:
    """配置AI API密钥"""
    if openai_key:
        _ai_config["openai_key"] = openai_key
    if anthropic_key:
        _ai_config["anthropic_key"] = anthropic_key
    if gemini_key:
        _ai_config["gemini_key"] = gemini_key
    
    configured = []
    if _ai_config["openai_key"]:
        configured.append("OpenAI GPT-4")
    if _ai_config["anthropic_key"]:
        configured.append("Claude")
    if _ai_config["gemini_key"]:
        configured.append("Google Gemini")
    
    if configured:
        return f"[AI CONFIGURED]\nConfigured models:\n" + "\n".join(f"  - {m}" for m in configured)
    else:
        return "[AI] No API keys configured. Set environment variables or pass keys."

@mcp.tool()
def ai_chat(model: str, message: str, system: str = "You are a helpful assistant.") -> str:
    """AI对话
    model: gpt-4, gpt-3.5-turbo, claude-3-sonnet, gemini-pro
    """
    try:
        if model.startswith("gpt"):
            return _call_openai(model, message, system)
        elif model.startswith("claude"):
            return _call_anthropic(model, message, system)
        elif model == "gemini-pro":
            return _call_gemini(message, system)
        else:
            return f"[ERROR] Unknown model: {model}\n\nSupported:\n- gpt-4, gpt-3.5-turbo\n- claude-3-sonnet\n- gemini-pro"
    except Exception as e:
        return f"[ERROR] {str(e)}"

def _call_openai(model: str, message: str, system: str) -> str:
    """调用OpenAI API"""
    if not _ai_config["openai_key"]:
        return "[ERROR] OpenAI API key not configured"
    
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_ai_config['openai_key']}"
        }
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": message}
            ],
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode(),
            headers=headers,
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
        
        return result["choices"][0]["message"]["content"]
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

def _call_anthropic(model: str, message: str, system: str) -> str:
    """调用Anthropic Claude API"""
    if not _ai_config["anthropic_key"]:
        return "[ERROR] Anthropic API key not configured"
    
    try:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": _ai_config["anthropic_key"],
            "anthropic-version": "2023-06-01",
            "anthropic-dangerous-direct-browser-access": "true"
        }
        data = {
            "model": model,
            "max_tokens": 1000,
            "system": system,
            "messages": [{"role": "user", "content": message}]
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode(),
            headers=headers,
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
        
        return result["content"][0]["text"]
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

def _call_gemini(message: str, system: str) -> str:
    """调用Google Gemini API"""
    if not _ai_config["gemini_key"]:
        return "[ERROR] Gemini API key not configured"
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={_ai_config['gemini_key']}"
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{"parts": [{"text": message}]}],
            "systemInstruction": {"parts": [{"text": system}]},
            "generationConfig": {"maxOutputTokens": 1000, "temperature": 0.7}
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode(),
            headers=headers,
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
        
        return result["candidates"][0]["content"]["parts"][0]["text"]
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def ai_translate(text: str, target_lang: str = "Chinese", source_lang: str = "English") -> str:
    """AI翻译"""
    prompt = f"""Translate the following {source_lang} text to {target_lang}.

{text}

Only output the translation, nothing else."""

    # 优先使用Claude（翻译效果好）
    if _ai_config["anthropic_key"]:
        return _call_anthropic("claude-3-haiku-20240229", prompt, "You are an expert translator.")
    elif _ai_config["openai_key"]:
        return _call_openai("gpt-3.5-turbo", prompt, "You are an expert translator.")
    else:
        return "[ERROR] No AI API configured for translation"

@mcp.tool()
def ai_summarize(text: str, max_length: int = 200) -> str:
    """AI摘要"""
    prompt = f"""Summarize the following text in no more than {max_length} characters.
Keep the key points and main ideas.

{text}

Summary:"""

    if _ai_config["anthropic_key"]:
        return _call_anthropic("claude-3-haiku-20240229", prompt, "You are a helpful assistant that summarizes text.")
    elif _ai_config["openai_key"]:
        return _call_openai("gpt-3.5-turbo", prompt, "You are a helpful assistant that summarizes text.")
    else:
        return "[ERROR] No AI API configured"

@mcp.tool()
def ai_code_review(code: str, language: str = "python") -> str:
    """AI代码审查"""
    prompt = f"""Review the following {language} code for:
1. Bugs and potential issues
2. Performance problems
3. Security vulnerabilities
4. Code style improvements

Provide specific suggestions.

Code:
```{language}
{code}
```

Review:"""

    if _ai_config["anthropic_key"]:
        return _call_anthropic("claude-3-sonnet-20240229", prompt, "You are an expert code reviewer.")
    elif _ai_config["openai_key"]:
        return _call_openai("gpt-4", prompt, "You are an expert code reviewer.")
    else:
        return "[ERROR] No AI API configured"

@mcp.tool()
def ai_sentiment(text: str) -> str:
    """AI情感分析"""
    prompt = f"""Analyze the sentiment of the following text.
Classify as: Positive, Negative, or Neutral.
Also provide a confidence score (0-100%).

Text: {text}

Output format:
Sentiment: [Positive/Negative/Neutral]
Confidence: [XX%]
Brief explanation: [why]"""

    if _ai_config["anthropic_key"]:
        return _call_anthropic("claude-3-haiku-20240229", prompt, "You are a sentiment analysis expert.")
    elif _ai_config["openai_key"]:
        return _call_openai("gpt-3.5-turbo", prompt, "You are a sentiment analysis expert.")
    else:
        return "[ERROR] No AI API configured"

@mcp.tool()
def ai_image_description(image_url: str) -> str:
    """AI图片描述"""
    prompt = """Describe this image in detail.
Include:
- What is in the image
- Key objects and their positions
- Colors and visual style
- Any text visible
- Overall scene description

Be as detailed as possible."""

    if not _ai_config["anthropic_key"]:
        return "[ERROR] Anthropic API required for image analysis"
    
    try:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": _ai_config["anthropic_key"],
            "anthropic-version": "2023-06-01",
            "anthropic-dangerous-direct-browser-access": "true"
        }
        data = {
            "model": "claude-3-haiku-20240229",
            "max_tokens": 500,
            "messages": [
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image", "source": {"type": "url", "url": image_url}}
                ]}
            ]
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode(),
            headers=headers,
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
        
        return result["content"][0]["text"]
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def ai_models_status() -> str:
    """检查AI模型配置状态"""
    status = "[AI MODELS STATUS]\n" + "=" * 40 + "\n\n"
    
    models = [
        ("OpenAI GPT-4", _ai_config["openai_key"]),
        ("Anthropic Claude", _ai_config["anthropic_key"]),
        ("Google Gemini", _ai_config["gemini_key"])
    ]
    
    for name, key in models:
        status += f"{name}: "
        if key:
            status += f"Configured ({key[:8]}...{key[-4:]})\n"
        else:
            status += "Not configured\n"
    
    status += "\n" + "=" * 40 + "\n"
    status += "\nTo configure, use configure_ai tool or set environment variables:\n"
    status += "- OPENAI_API_KEY\n"
    status += "- ANTHROPIC_API_KEY\n"
    status += "- GEMINI_API_KEY"
    
    return status

if __name__ == "__main__":
    mcp.run()
