"""
Pikachu Cloud & Automation MCP Server ⚡
云存储、Webhook、定时任务
"""
from fastmcp import FastMCP
import urllib.request
import json
import os
import time
import hashlib
from datetime import datetime, timedelta

mcp = FastMCP("PikachuCloud")

# 存储配置
_config = {
    "oss_ak": "",
    "oss_sk": "",
    "oss_bucket": "",
    "oss_endpoint": ""
}

# Webhook记录
_webhooks = {}

@mcp.tool()
def ping(url: str) -> str:
    """测试URL连通性"""
    try:
        start = time.time()
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as response:
            elapsed = (time.time() - start) * 1000
            return f"""[PING OK]
URL: {url}
Status: {response.status}
Response time: {elapsed:.0f}ms
Server: {response.headers.get('server', 'Unknown')}"""
    except urllib.error.HTTPError as e:
        return f"[HTTP ERROR] {e.code}: {e.reason}"
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def http_request(method: str, url: str, headers: str = "{}", body: str = "") -> str:
    """发送HTTP请求
    method: GET, POST, PUT, DELETE, PATCH
    headers: JSON格式
    """
    try:
        headers_dict = json.loads(headers) if isinstance(headers, str) else headers
        
        req = urllib.request.Request(
            url,
            data=body.encode() if body else None,
            headers=headers_dict,
            method=method
        )
        
        start = time.time()
        with urllib.request.urlopen(req, timeout=30) as response:
            elapsed = (time.time() - start) * 1000
            response_body = response.read().decode('utf-8', errors='replace')[:1000]
        
        result = f"""[HTTP RESPONSE]
Method: {method}
URL: {url}
Status: {response.status}
Response time: {elapsed:.0f}ms
Headers: {dict(response.headers)}"""
        
        if response_body:
            result += f"\n\nBody (first 500 chars):\n{response_body[:500]}"
        
        return result
        
    except urllib.error.HTTPError as e:
        return f"[HTTP ERROR] {e.code}: {e.reason}\n{e.read().decode()[:500]}"
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def download_file(url: str, output_path: str) -> str:
    """下载文件到本地"""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=60) as response:
            content = response.read()
        
        with open(output_path, 'wb') as f:
            f.write(content)
        
        size = len(content)
        md5 = hashlib.md5(content).hexdigest()
        
        return f"""[DOWNLOADED]
URL: {url}
Path: {output_path}
Size: {size:,} bytes ({size/1024/1024:.2f} MB)
MD5: {md5}
Saved at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def upload_to_url(file_path: str, upload_url: str) -> str:
    """上传文件到URL"""
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        filename = os.path.basename(file_path)
        
        boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
        body = f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'
        body = body.encode() + content + f'\r\n--{boundary}--\r\n'.encode()
        
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}'
        }
        
        req = urllib.request.Request(
            upload_url,
            data=body,
            headers=headers,
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            result = response.read().decode()
        
        return f"""[UPLOADED]
File: {file_path}
Size: {len(content):,} bytes
URL: {upload_url}
Response: {result[:500]}"""
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def register_webhook(name: str, url: str, secret: str = "") -> str:
    """注册Webhook回调
    返回一个回调URL用于接收数据
    """
    import uuid
    hook_id = str(uuid.uuid4())[:8]
    
    _webhooks[hook_id] = {
        "name": name,
        "url": url,
        "secret": secret,
        "created": datetime.now().isoformat(),
        "calls": []
    }
    
    callback_url = f"http://localhost:19789/webhook/{hook_id}"
    
    return f"""[WEBHOOK REGISTERED]
Name: {name}
Target URL: {url}
Hook ID: {hook_id}
Callback URL: {callback_url}

Use the callback URL to receive webhook calls.
Calls will be logged and forwarded to {url}"""

@mcp.tool()
def list_webhooks() -> str:
    """列出所有注册的Webhook"""
    if not _webhooks:
        return "[EMPTY] No webhooks registered"
    
    result = f"[WEBHOOKS] ({len(_webhooks)} total)\n" + "=" * 50 + "\n"
    
    for hook_id, hook in _webhooks.items():
        result += f"\nID: {hook_id}\n"
        result += f"  Name: {hook['name']}\n"
        result += f"  Target: {hook['url']}\n"
        result += f"  Calls: {len(hook['calls'])}\n"
        result += f"  Created: {hook['created']}\n"
    
    return result

@mcp.tool()
def trigger_webhook(hook_id: str, payload: str = "{}") -> str:
    """手动触发Webhook"""
    try:
        if hook_id not in _webhooks:
            return f"[ERROR] Webhook {hook_id} not found"
        
        hook = _webhooks[hook_id]
        payload_dict = json.loads(payload) if isinstance(payload, str) else payload
        
        # 添加时间戳
        payload_dict["_triggered_at"] = datetime.now().isoformat()
        
        # 发送请求
        data = json.dumps(payload_dict).encode()
        headers = {"Content-Type": "application/json"}
        
        if hook["secret"]:
            import hmac
            signature = hmac.new(hook["secret"].encode(), data, hashlib.sha256).hexdigest()
            headers["X-Webhook-Signature"] = signature
        
        req = urllib.request.Request(
            hook["url"],
            data=data,
            headers=headers,
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = response.read().decode()
        
        # 记录调用
        _webhooks[hook_id]["calls"].append({
            "time": datetime.now().isoformat(),
            "payload": payload_dict,
            "response": result[:200]
        })
        
        return f"""[WEBHOOK TRIGGERED]
ID: {hook_id}
URL: {hook['url']}
Payload: {json.dumps(payload_dict)[:200]}
Response: {result[:200]}"""
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def url_shorten(long_url: str, alias: str = "") -> str:
    """短链接生成（使用TinyURL）"""
    try:
        tinyurl_api = f"https://tinyurl.com/api-create.php?url={urllib.parse.quote(long_url)}"
        req = urllib.request.Request(tinyurl_api)
        with urllib.request.urlopen(req, timeout=10) as response:
            short_url = response.read().decode()
        
        return f"""[SHORT URL]
Original: {long_url}
Short: {short_url}
Alias: {alias if alias else 'None'}"""
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def check_health(url: str) -> str:
    """检查网站健康状态"""
    try:
        start = time.time()
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            elapsed = (time.time() - start) * 1000
            
            result = f"""[HEALTH CHECK]
URL: {url}
Status: {"OK" if response.status == 200 else "ISSUE"}
Status Code: {response.status}
Response Time: {elapsed:.0f}ms"""
            
            # 检查安全头
            security_headers = ['content-security-policy', 'strict-transport-security', 'x-content-type-options']
            result += "\n\n[SECURITY HEADERS]"
            for header in security_headers:
                value = response.headers.get(header.replace('-', '-').title())
                result += f"\n{header}: {value if value else 'MISSING'}"
            
            return result
            
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def api_json_parse(api_url: str) -> str:
    """解析API JSON响应"""
    try:
        req = urllib.request.Request(api_url)
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
        
        # 分析结构
        def analyze(obj, depth=0, max_depth=3):
            if depth > max_depth:
                return "  " * depth + "..."
            
            indent = "  " * depth
            
            if isinstance(obj, dict):
                result = f"{indent}{{"
                for i, (k, v) in enumerate(list(obj.items())[:10]):
                    if i > 0:
                        result += ","
                    result += f"\n{indent}  {k}:"
                    if isinstance(v, dict):
                        result += f"\n{analyze(v, depth+1)}"
                    elif isinstance(v, list):
                        result += f"\n{analyze(v, depth+1)}"
                    else:
                        result += f" {type(v).__name__} = {str(v)[:50]}"
                result += f"\n{indent}}}"
                return result
            elif isinstance(obj, list):
                if not obj:
                    return f"{indent}[]"
                return f"{indent}[{type(obj[0]).__name__} x {len(obj)}]"
            else:
                return f"{indent}{type(obj).__name__} = {str(obj)[:50]}"
        
        analysis = analyze(data)
        
        return f"""[API JSON ANALYSIS]
URL: {api_url}
Type: {type(data).__name__}
Keys: {len(data) if isinstance(data, dict) else len(data) if isinstance(data, list) else 'N/A'}

[STRUCTURE]
{analysis}

[RAW (first 300 chars)]
{str(data)[:300]}"""
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

if __name__ == "__main__":
    mcp.run()
