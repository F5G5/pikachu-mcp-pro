"""
Pikachu Remote MCP Server - 远程MCP服务器支持 ⚡
支持HTTP/SSE远程调用，部署到云端或本地网络

Google Toolbox有的，我们也要有！而且更简单！
"""
from fastmcp import FastMCP
import json
import asyncio
from typing import Any, Dict, Optional
import urllib.request
import urllib.error

mcp = FastMCP("PikachuRemote", 
              transport="http",  # 启用HTTP传输
              port=8080,          # 默认端口
              host="0.0.0.0")     # 监听所有网络接口

# ============ 远程配置 ============
_remote_config = {
    "port": 8080,
    "host": "0.0.0.0",
    "cors": True,
    "auth": None,  # 可设置API Key认证
}

# ============ 远程工具 ============

@mcp.tool()
def remote_status() -> str:
    """查看远程服务器状态"""
    return f"""[REMOTE SERVER STATUS]
Host: {_remote_config['host']}
Port: {_remote_config['port']}
Transport: HTTP/SSE
Auth: {'Enabled' if _remote_config['auth'] else 'Disabled'}
CORS: {'Enabled' if _remote_config['cors'] else 'Disabled'}

远程调用示例:
curl -X POST http://localhost:{_remote_config['port']}/mcp \\
  -H 'Content-Type: application/json' \\
  -d '{{"jsonrpc":"2.0","id":1,"method":"tools/list"}}'
"""

@mcp.tool()
def configure_remote(host: str = "0.0.0.0", port: int = 8080, 
                    cors: bool = True, api_key: str = "") -> str:
    """配置远程服务器"""
    _remote_config["host"] = host
    _remote_config["port"] = port
    _remote_config["cors"] = cors
    _remote_config["auth"] = api_key if api_key else None
    
    return f"""[REMOTE CONFIGURED]
Host: {host}
Port: {port}
CORS: {cors}
Auth: {'Enabled' if api_key else 'Disabled'}
"""

@mcp.tool()
def test_remote_connection(url: str) -> str:
    """测试远程MCP服务器连接"""
    try:
        # 发送JSON-RPC请求
        data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode(),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            },
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            
            if "result" in result and "tools" in result["result"]:
                tools = result["result"]["tools"]
                return f"""[REMOTE CONNECT OK]
URL: {url}
Tools: {len(tools)}
{chr(10).join(['  - ' + t['name'] for t in tools[:10]])}"""
            
            return f"[CONNECTED] Response: {str(result)[:200]}"
    
    except urllib.error.URLError as e:
        return f"[ERROR] 连接失败: {str(e)}\n\n可能原因:\n1. 服务器未启动\n2. URL错误\n3. 网络不通"
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def call_remote_tool(url: str, tool_name: str, arguments: str = "{}") -> str:
    """调用远程MCP工具
    url: 远程服务器URL
    tool_name: 工具名
    arguments: JSON格式参数
    """
    try:
        args = json.loads(arguments) if isinstance(arguments, str) else arguments
        
        data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": args
            }
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode(),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            
            if "result" in result:
                content = result["result"].get("content", [])
                if content and isinstance(content, list):
                    return content[0].get("text", str(result))
                return str(result["result"])
            
            if "error" in result:
                return f"[ERROR] {result['error']}"
            
            return str(result)
    
    except Exception as e:
        return f"[ERROR] {str(e)}"

# ============ 远程发现 ============

@mcp.tool()
def discover_mcp_servers(config: str = "[]") -> str:
    """发现网络上的MCP服务器
    config: JSON数组，每项包含URL列表
    
    示例: discover_mcp_servers('["http://localhost:8080", "http://localhost:8081"]')
    """
    try:
        urls = json.loads(config) if isinstance(config, str) else config
        
        result = "[DISCOVERED SERVERS]\n" + "=" * 50 + "\n"
        
        found = []
        for url in urls:
            try:
                resp = test_remote_connection(url)
                if "OK" in resp:
                    found.append((url, resp))
            except:
                pass
        
        if not found:
            return "[NONE FOUND] 未发现运行的MCP服务器"
        
        for url, resp in found:
            result += f"\n{resp}\n"
        
        return result
    
    except Exception as e:
        return f"[ERROR] {str(e)}"

# ============ 远程执行工具 ============

@mcp.tool()
def remote_sql_query(url: str, query: str, params: str = "{}") -> str:
    """远程SQL查询（如果服务器有sql工具）"""
    return call_remote_tool(url, "execute_sql", json.dumps({
        "query": query,
        "params": params
    }))

@mcp.tool()
def remote_ai_chat(url: str, model: str, message: str) -> str:
    """远程AI对话（如果服务器有ai_chat工具）"""
    return call_remote_tool(url, "ai_chat", json.dumps({
        "model": model,
        "message": message
    }))

@mcp.tool()
def remote_nl2sql(url: str, query: str) -> str:
    """远程NL2SQL（如果服务器有nl2sql工具）"""
    return call_remote_tool(url, "nl2sql", json.dumps({
        "query": query
    }))

if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║     Pikachu Remote MCP Server ⚡                               ║
║     远程MCP服务器 - 部署到云端或本地网络                         ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # 启动HTTP服务器
    mcp.run(transport="http", port=_remote_config["port"], host=_remote_config["host"])
