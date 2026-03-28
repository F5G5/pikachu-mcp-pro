"""
Pikachu Professional AI MCP Server ⚡
支持 OpenAI/Claude/Gemini + RAG + 向量数据库 + AI工具链
"""
from fastmcp import FastMCP
import urllib.request
import json
import os
import hashlib
import time
from typing import List, Dict, Optional

mcp = FastMCP("PikachuAI")

# ============ 配置管理 ============

_ai_config = {
    "openai_key": os.environ.get("OPENAI_API_KEY", ""),
    "anthropic_key": os.environ.get("ANTHROPIC_API_KEY", ""),
    "gemini_key": os.environ.get("GEMINI_API_KEY", ""),
    "openai_base": "https://api.openai.com/v1",
    "anthropic_base": "https://api.anthropic.com/v1",
    "gemini_base": "https://generativelanguage.googleapis.com/v1beta"
}

# 向量存储（简单内存实现）
_vector_store: Dict[str, List[Dict]] = {}

# ============ 配置工具 ============

@mcp.tool()
def configure_ai(openai_key: str = "", anthropic_key: str = "", gemini_key: str = "",
                openai_base: str = "", anthropic_base: str = "", gemini_base: str = "") -> str:
    """配置AI API密钥和端点"""
    if openai_key:
        _ai_config["openai_key"] = openai_key
    if anthropic_key:
        _ai_config["anthropic_key"] = anthropic_key
    if gemini_key:
        _ai_config["gemini_key"] = gemini_key
    if openai_base:
        _ai_config["openai_base"] = openai_base
    if anthropic_base:
        _ai_config["anthropic_base"] = anthropic_base
    if gemini_base:
        _ai_config["gemini_base"] = gemini_base
    
    configured = []
    if _ai_config["openai_key"]:
        configured.append(f"OpenAI ({_ai_config['openai_base'].split('/')[-1]})")
    if _ai_config["anthropic_key"]:
        configured.append(f"Claude ({_ai_config['anthropic_base'].split('/')[-1]})")
    if _ai_config["gemini_key"]:
        configured.append(f"Gemini ({_ai_config['gemini_base'].split('/')[-1]})")
    
    if configured:
        return "[AI CONFIGURED]\n" + "\n".join(f"  - {m}" for m in configured)
    return "[AI] No API keys configured. Set environment variables or pass keys."

@mcp.tool()
def ai_status() -> str:
    """检查AI服务状态"""
    result = "[AI STATUS]\n" + "=" * 50 + "\n"
    
    services = [
        ("OpenAI GPT-4", _ai_config["openai_key"], "models"),
        ("Anthropic Claude", _ai_config["anthropic_key"], "models"),
        ("Google Gemini", _ai_config["gemini_key"], "models")
    ]
    
    for name, key, endpoint in services:
        if key:
            short_key = key[:12] + "..." + key[-4:]
            result += f"\n{name}:\n  Key: {short_key}\n  Status: ✅ Configured\n"
            
            # 测试连接
            try:
                if "openai" in endpoint:
                    url = f"{_ai_config['openai_base']}/models"
                    headers = {"Authorization": f"Bearer {key}"}
                elif "anthropic" in endpoint:
                    url = f"{_ai_config['anthropic_base']}/models"
                    headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
                else:
                    url = f"{_ai_config['gemini_base']}/models?key={key}"
                    headers = {}
                
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=5):
                    result += "  Connection: ✅ OK\n"
            except:
                result += "  Connection: ⚠️ Cannot verify\n"
        else:
            result += f"\n{name}:\n  Status: ❌ Not configured\n"
    
    return result

# ============ AI对话 ============

@mcp.tool()
def ai_chat(model: str, message: str, system: str = "", temperature: float = 0.7, 
            max_tokens: int = 1000) -> str:
    """AI对话
    model: gpt-4, gpt-4-turbo, gpt-3.5-turbo, claude-3-sonnet, claude-3-haiku, gemini-pro
    """
    try:
        if model.startswith("gpt"):
            return _call_openai(model, message, system, temperature, max_tokens)
        elif model.startswith("claude"):
            return _call_anthropic(model, message, system, temperature, max_tokens)
        elif "gemini" in model:
            return _call_gemini(model, message, system, temperature, max_tokens)
        else:
            return f"[ERROR] Unknown model: {model}\n\nSupported:\n- gpt-4, gpt-4-turbo, gpt-3.5-turbo\n- claude-3-sonnet, claude-3-haiku\n- gemini-pro"
    except Exception as e:
        return f"[ERROR] {str(e)}"

def _call_openai(model: str, message: str, system: str, temperature: float, max_tokens: int) -> str:
    if not _ai_config["openai_key"]:
        return "[ERROR] OpenAI not configured"
    
    try:
        url = f"{_ai_config['openai_base']}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_ai_config['openai_key']}"
        }
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": message})
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method="POST")
        
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode())
        
        return result["choices"][0]["message"]["content"]
    
    except Exception as e:
        return f"[ERROR] {str(e)}"

def _call_anthropic(model: str, message: str, system: str, temperature: float, max_tokens: int) -> str:
    if not _ai_config["anthropic_key"]:
        return "[ERROR] Anthropic not configured"
    
    try:
        url = f"{_ai_config['anthropic_base']}/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": _ai_config["anthropic_key"],
            "anthropic-version": "2023-06-01",
            "anthropic-dangerous-direct-browser-access": "true"
        }
        
        messages = []
        if system:
            messages.append({"role": "user", "content": [{"type": "text", "text": system}]})
        messages.append({"role": "user", "content": [{"type": "text", "text": message}]})
        
        data = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages
        }
        if system:
            data["system"] = system
        
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method="POST")
        
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode())
        
        return result["content"][0]["text"]
    
    except Exception as e:
        return f"[ERROR] {str(e)}"

def _call_gemini(model: str, message: str, system: str, temperature: float, max_tokens: int) -> str:
    if not _ai_config["gemini_key"]:
        return "[ERROR] Gemini not configured"
    
    try:
        # 模型名称映射
        model_map = {
            "gemini-pro": "gemini-1.5-pro",
            "gemini-flash": "gemini-1.5-flash"
        }
        actual_model = model_map.get(model, model)
        
        url = f"{_ai_config['gemini_base']}/models/{actual_model}:generateContent?key={_ai_config['gemini_key']}"
        headers = {"Content-Type": "application/json"}
        
        contents = [{"parts": [{"text": message}]}]
        if system:
            contents.insert(0, {"parts": [{"text": f"System: {system}"}]})
        
        data = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method="POST")
        
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode())
        
        return result["candidates"][0]["content"]["parts"][0]["text"]
    
    except Exception as e:
        return f"[ERROR] {str(e)}"

# ============ AI工具 ============

@mcp.tool()
def ai_translate(text: str, target_lang: str = "Chinese", source_lang: str = "English") -> str:
    """AI翻译"""
    prompt = f"""Translate the following {source_lang} text to {target_lang}.

Only output the translation, nothing else.

Text:
{text}

Translation:"""

    if _ai_config["anthropic_key"]:
        return _call_anthropic("claude-3-haiku-20240229", prompt, "You are an expert translator.", 0.3, 500)
    elif _ai_config["openai_key"]:
        return _call_openai("gpt-3.5-turbo", prompt, "You are an expert translator.", 0.3, 500)
    return "[ERROR] No AI API configured"

@mcp.tool()
def ai_summarize(text: str, max_length: int = 200, style: str = "concise") -> str:
    """AI摘要"""
    styles = {
        "concise": "Provide a brief summary in 2-3 sentences.",
        "detailed": "Provide a comprehensive summary with key points.",
        "bullets": "Summarize as bullet points.",
        "tldr": "Provide a TL;DR summary."
    }
    
    style_hint = styles.get(style, styles["concise"])
    
    prompt = f"""{style_hint}

Text to summarize:
{text}

Summary:"""

    if _ai_config["anthropic_key"]:
        return _call_anthropic("claude-3-haiku-20240229", prompt, "You are a helpful assistant.", 0.3, max_length * 2)
    elif _ai_config["openai_key"]:
        return _call_openai("gpt-3.5-turbo", prompt, "You are a helpful assistant.", 0.3, max_length * 2)
    return "[ERROR] No AI API configured"

@mcp.tool()
def ai_sentiment(text: str) -> str:
    """AI情感分析"""
    prompt = f"""Analyze the sentiment of this text.
Classify as: Positive, Negative, or Neutral.
Provide a brief explanation.

Text: {text}"""

    if _ai_config["anthropic_key"]:
        result = _call_anthropic("claude-3-haiku-20240229", prompt, "You are a sentiment analysis expert.", 0.3, 200)
    elif _ai_config["openai_key"]:
        result = _call_openai("gpt-3.5-turbo", prompt, "You are a sentiment analysis expert.", 0.3, 200)
    else:
        return "[ERROR] No AI API configured"
    
    # 简单分类
    text_lower = result.lower()
    if "positive" in text_lower:
        sentiment = "🟢 Positive"
    elif "negative" in text_lower:
        sentiment = "🔴 Negative"
    else:
        sentiment = "🟡 Neutral"
    
    return f"[SENTIMENT] {sentiment}\n\n{result}"

@mcp.tool()
def ai_code_review(code: str, language: str = "python") -> str:
    """AI代码审查"""
    prompt = f"""Review this {language} code for:
1. Bugs and potential issues
2. Performance problems  
3. Security vulnerabilities
4. Code style improvements
5. Best practices

Provide specific suggestions with code examples if helpful.

Code:
```{language}
{code}
```

Review:"""

    if _ai_config["anthropic_key"]:
        return _call_anthropic("claude-3-sonnet-20240229", prompt, "You are an expert code reviewer.", 0.3, 1500)
    elif _ai_config["openai_key"]:
        return _call_openai("gpt-4", prompt, "You are an expert code reviewer.", 0.3, 1500)
    return "[ERROR] No AI API configured for code review"

# ============ 向量存储 (RAG) ============

@mcp.tool()
def vector_store(collection: str, text: str, metadata: str = "{}") -> str:
    """存储文本到向量集合（简单实现）
    实际生产应使用 Pinecone/Milvus/Chroma"""
    try:
        if collection not in _vector_store:
            _vector_store[collection] = []
        
        meta = json.loads(metadata) if isinstance(metadata, str) else metadata
        
        # 简单hash作为ID
        doc_id = hashlib.md5(f"{text}{time.time()}".encode()).hexdigest()[:12]
        
        _vector_store[collection].append({
            "id": doc_id,
            "text": text,
            "metadata": meta,
            "created": time.time()
        })
        
        return f"[STORED] Document {doc_id} in collection '{collection}'\nCollection size: {len(_vector_store[collection])}"
    
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def vector_search(collection: str, query: str, top_k: int = 5) -> str:
    """搜索向量集合（简单实现）
    实际生产应使用向量相似度搜索"""
    try:
        if collection not in _vector_store:
            return f"[EMPTY] Collection '{collection}' not found"
        
        docs = _vector_store[collection]
        if not docs:
            return f"[EMPTY] Collection '{collection}' is empty"
        
        # 简单关键词匹配（生产应使用向量嵌入）
        query_words = set(query.lower().split())
        scored = []
        
        for doc in docs:
            text_words = set(doc["text"].lower().split())
            # Jaccard相似度
            intersection = query_words & text_words
            union = query_words | text_words
            score = len(intersection) / len(union) if union else 0
            scored.append((score, doc))
        
        # 排序
        scored.sort(reverse=True)
        
        result = f"[SEARCH RESULTS] for '{query}'\n" + "=" * 50 + "\n"
        result += f"Collection: {collection}\n"
        result += f"Total docs: {len(docs)}\n"
        result += f"Results: {min(top_k, len(scored))}\n\n"
        
        for i, (score, doc) in enumerate(scored[:top_k], 1):
            result += f"{i}. [Score: {score:.2f}] {doc['text'][:100]}...\n"
            if doc.get("metadata"):
                result += f"   Meta: {doc['metadata']}\n"
            result += f"   ID: {doc['id']}\n\n"
        
        return result
    
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def vector_list_collections() -> str:
    """列出所有向量集合"""
    if not _vector_store:
        return "[EMPTY] No collections"
    
    result = f"[COLLECTIONS] ({len(_vector_store)})\n" + "=" * 50 + "\n"
    
    for name, docs in _vector_store.items():
        total_chars = sum(len(d["text"]) for d in docs)
        result += f"\n{name}:\n"
        result += f"  Documents: {len(docs)}\n"
        result += f"  Total chars: {total_chars:,}\n"
    
    return result

@mcp.tool()
def vector_delete_collection(collection: str) -> str:
    """删除向量集合"""
    if collection in _vector_store:
        count = len(_vector_store[collection])
        del _vector_store[collection]
        return f"[DELETED] Collection '{collection}' with {count} documents"
    return f"[NOT FOUND] Collection '{collection}' not found"

# ============ Prompt模板 ============

@mcp.tool()
def prompt_template(name: str, variables: str = "{}") -> str:
    """使用Prompt模板
    name: template_name
    variables: JSON格式变量
    """
    templates = {
        "code_explain": {
            "template": "Explain this code in simple terms:\n```{language}\n{code}\n```",
            "variables": ["language", "code"]
        },
        "bug_fix": {
            "template": "Find and fix bugs in this code:\n```{language}\n{code}\n```\n\nExplain the fixes:",
            "variables": ["language", "code"]
        },
        "write_tests": {
            "template": "Write unit tests for:\n```{language}\n{code}\n```\n\nUse {framework}:",
            "variables": ["language", "code", "framework"]
        },
        "refactor": {
            "template": "Refactor this {language} code to be more idiomatic:\n```{language}\n{code}\n```",
            "variables": ["language", "code"]
        },
        "security_scan": {
            "template": "Scan this code for security vulnerabilities:\n```{language}\n{code}\n```",
            "variables": ["language", "code"]
        },
        "optimize": {
            "template": "Optimize this {language} code for performance:\n```{language}\n{code}\n```",
            "variables": ["language", "code"]
        }
    }
    
    if name not in templates:
        return f"[ERROR] Unknown template: {name}\n\nAvailable templates:\n" + "\n".join(f"  - {k}" for k in templates.keys())
    
    try:
        vars_dict = json.loads(variables) if isinstance(variables, str) else variables
        tmpl = templates[name]["template"]
        
        result = tmpl
        for var, val in vars_dict.items():
            result = result.replace(f"{{{var}}}", str(val))
        
        return f"[PROMPT TEMPLATE: {name}]\n\n{result}"
    
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def list_prompt_templates() -> str:
    """列出所有Prompt模板"""
    templates = [
        ("code_explain", "解释代码含义"),
        ("bug_fix", "查找并修复bug"),
        ("write_tests", "编写单元测试"),
        ("refactor", "重构代码"),
        ("security_scan", "安全漏洞扫描"),
        ("optimize", "性能优化")
    ]
    
    result = "[PROMPT TEMPLATES]\n" + "=" * 50 + "\n"
    for name, desc in templates:
        result += f"\n{name}:\n  {desc}\n"
    
    return result

if __name__ == "__main__":
    mcp.run()
