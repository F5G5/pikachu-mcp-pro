"""
Pikachu Professional All-in-One MCP Server ⚡
整合数据库 + AI + NL2SQL + Remote支持

真正的超越不是功能多，而是每个功能都专业！
"""
from fastmcp import FastMCP
import json
import sqlite3
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

mcp = FastMCP("PikachuPro")

# ============ 连接池 ============
class ConnectionPool:
    def __init__(self):
        self._conns: Dict[str, Any] = {}
        self._config: Dict[str, Dict] = {}
    
    def add_sqlite(self, name: str, path: str) -> bool:
        try:
            conn = sqlite3.connect(path)
            conn.row_factory = sqlite3.Row
            self._conns[name] = conn
            self._config[name] = {"type": "sqlite", "path": path}
            return True
        except:
            return False
    
    def execute(self, name: str, query: str, params: tuple = ()):
        if name not in self._conns:
            raise ValueError(f"Connection '{name}' not found")
        conn = self._conns[name]
        cursor = conn.cursor()
        cursor.execute(query, params)
        if query.strip().upper().startswith("SELECT"):
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description] if cursor.description else []
            return cols, rows
        else:
            conn.commit()
            return [], cursor.rowcount
    
    def list(self) -> List[Dict]:
        return [{"name": k, **v} for k, v in self._config.items()]

_pool = ConnectionPool()

# ============ AI配置 ============
_ai_config = {
    "openai_key": "",
    "anthropic_key": "",
    "ollama_url": "http://localhost:11434",
    "default_model": "llama3.2",
}

# ============ NL2SQL Prompt优化（中文） ============
_NL2SQL_SYSTEM_PROMPT = """你是一个专业的NL2SQL专家，专门处理中文自然语言查询。

你的任务是：将用户的中文问题转换为准确、高效的SQL查询。

【核心能力】
1. 准确理解中文语义（即使表述不精确）
2. 处理复杂的JOIN和子查询
3. 优化SQL性能
4. 处理聚合、分组、排序

【Schema理解】
- PRIMARY KEY: 主键，用于JOIN和子查询优化
- FOREIGN KEY: 外键关系，自动识别表间关联
- INDEX: 索引，用于性能优化

【SQL规范】
- 只生成SELECT查询（数据分析场景）
- 使用明确的表别名提高可读性
- 合理使用JOIN（优先使用外键关系）
- 聚合查询添加GROUP BY
- 排序使用有索引的列提高性能

【输出格式】
只返回SQL语句，不要任何解释。
"""

def get_schema_for_nl2sql(db_name: str = "default") -> str:
    if db_name not in _pool._conns:
        return ""
    conn = _pool._conns[db_name]
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [r[0] for r in cursor.fetchall()]
    
    parts = []
    for table in tables:
        parts.append(f"## {table}")
        cursor.execute(f"PRAGMA table_info({table})")
        cols = cursor.fetchall()
        for col in cols:
            parts.append(f"  {col[1]}: {col[2]} {'PK' if col[5] else ''}")
        cursor.execute(f"PRAGMA foreign_key_list({table})")
        fks = cursor.fetchall()
        for fk in fks:
            parts.append(f"  FK: {fk[3]} -> {fk[2]}.{fk[4]}")
        parts.append("")
    
    return "\n".join(parts)

def nl2sql_core(query: str, db_name: str, model: str = "ollama") -> Optional[str]:
    """NL2SQL核心引擎"""
    schema = get_schema_for_nl2sql(db_name)
    if not schema:
        return None
    
    prompt = f"""数据库Schema:
{schema}

用户问题: {query}

请只返回SQL语句:"""
    
    # Ollama调用
    if model == "ollama" or not _ai_config["openai_key"]:
        try:
            url = f"{_ai_config['ollama_url']}/api/generate"
            data = {
                "model": _ai_config["default_model"],
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 300}
            }
            req = urllib.request.Request(url, data=json.dumps(data).encode(),
                                       headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                return extract_sql(result.get("response", ""))
        except Exception as e:
            pass
    
    # OpenAI fallback
    if _ai_config["openai_key"]:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {_ai_config['openai_key']}"}
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "system", "content": _NL2SQL_SYSTEM_PROMPT},
                           {"role": "user", "content": prompt}],
                "temperature": 0.1, "max_tokens": 300
            }
            req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                return extract_sql(result["choices"][0]["message"]["content"])
        except:
            pass
    
    return None

def extract_sql(response: str) -> Optional[str]:
    """从AI响应提取SQL"""
    import re
    patterns = [r"```sql\s*\n(.*?)\n```", r"```\s*\n(.*?)\n```", r"(SELECT\s+.+?;)", r"(SELECT\s+.+)", ]
    for p in patterns:
        m = re.search(p, response, re.DOTALL | re.IGNORECASE)
        if m:
            sql = m.group(1).strip()
            if sql.endswith(";"):
                sql = sql[:-1]
            return sql
    return response.strip() if response.strip().upper().startswith("SELECT") else None

# ============ 工具：数据库 ============

@mcp.tool()
def db_connect(db_type: str, name: str = "default", path: str = "./data.db",
             host: str = "localhost", port: int = 3306,
             user: str = "root", password: str = "", database: str = "") -> str:
    """连接数据库"""
    if db_type == "sqlite":
        if _pool.add_sqlite(name, path):
            cursor = _pool._conns[name].cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cursor.fetchall()]
            return f"[SQLITE] {name}@{path}\nTables: {len(tables)}"
        return "[ERROR] Failed"
    return "[ERROR] Only SQLite supported in this version"

@mcp.tool()
def db_list() -> str:
    """列出连接"""
    conns = _pool.list()
    if not conns:
        return "[EMPTY] No connections"
    return "[CONNECTIONS]\n" + "\n".join([f"- {c['name']}: {c['type']}" for c in conns])

@mcp.tool()
def db_schema(db_name: str = "default") -> str:
    """获取Schema"""
    schema = get_schema_for_nl2sql(db_name)
    if not schema:
        return "[ERROR] No connection or empty DB"
    return f"[SCHEMA]\n{schema}"

@mcp.tool()
def db_query(sql: str, db_name: str = "default", limit: int = 50) -> str:
    """执行SQL"""
    try:
        cols, rows = _pool.execute(db_name, sql)
        if not cols:
            return f"[OK] {rows} rows affected"
        
        result = f"[ROWS: {len(rows)}]\n"
        result += " | ".join(f"{c:<15}" for c in cols[:8]) + "\n"
        result += "-" * 60 * 2 + "\n"
        for row in rows[:limit]:
            result += " | ".join(f"{str(row[i]):<15}" for i in range(min(len(cols), 8))) + "\n"
        if len(rows) > limit:
            result += f"\n... {len(rows) - limit} more"
        return result
    except Exception as e:
        return f"[ERROR] {e}"

# ============ 工具：NL2SQL ============

@mcp.tool()
def nl2sql(query: str, db_name: str = "default", model: str = "auto") -> str:
    """中文自然语言转SQL（生成模式）
    query: 中文问题，如"查询每个用户的订单数量"
    """
    sql = nl2sql_core(query, db_name, model)
    if not sql:
        return "[ERROR] NL2SQL failed. Check: 1) DB connected 2) Ollama running or OpenAI configured"
    
    # 验证
    try:
        _pool.execute(db_name, f"EXPLAIN QUERY PLAN {sql}")
    except Exception as e:
        return f"[SQL] {sql}\n[WARNING] May have issues: {e}"
    
    return f"[NL2SQL]\nQuery: {query}\n\n```sql\n{sql}\n```"

@mcp.tool()
def nl2sql_run(query: str, db_name: str = "default", model: str = "auto") -> str:
    """中文自然语言查询（执行模式）"""
    sql = nl2sql_core(query, db_name, model)
    if not sql:
        return "[ERROR] NL2SQL failed"
    
    try:
        cols, rows = _pool.execute(db_name, sql)
        if not cols:
            return f"[OK] {rows} rows"
        
        result = f"[{len(rows)} rows]\nQuery: {query}\nSQL: {sql}\n\n"
        result += " | ".join(f"{c:<15}" for c in cols[:8]) + "\n"
        result += "-" * 60 * 2 + "\n"
        for row in rows[:30]:
            result += " | ".join(f"{str(row[i]):<15}" for i in range(min(len(cols), 8))) + "\n"
        return result
    except Exception as e:
        return f"[ERROR] {e}\nSQL: {sql}"

@mcp.tool()
def nl2sql_preview(question: str, db_name: str = "default") -> str:
    """NL2SQL预览（显示问题->SQL映射）"""
    return nl2sql(question, db_name)

# ============ 工具：AI ============

@mcp.tool()
def ai_configure(openai_key: str = "", anthropic_key: str = "",
                ollama_url: str = "http://localhost:11434",
                default_model: str = "llama3.2") -> str:
    """配置AI"""
    if openai_key:
        _ai_config["openai_key"] = openai_key
    if anthropic_key:
        _ai_config["anthropic_key"] = anthropic_key
    if ollama_url:
        _ai_config["ollama_url"] = ollama_url
    if default_model:
        _ai_config["default_model"] = default_model
    
    return "[AI CONFIGURED]\n" + json.dumps({k: v[:10]+"..." if len(v) > 10 else v for k, v in _ai_config.items()}, indent=2)

@mcp.tool()
def ai_status() -> str:
    """AI状态"""
    status = ["[AI STATUS]"]
    
    # Ollama
    try:
        req = urllib.request.Request(f"{_ai_config['ollama_url']}/api/tags")
        with urllib.request.urlopen(req, timeout=3):
            status.append("Ollama: ✅")
    except:
        status.append("Ollama: ❌")
    
    status.append(f"OpenAI: {'✅' if _ai_config['openai_key'] else '❌'}")
    status.append(f"Claude: {'✅' if _ai_config['anthropic_key'] else '❌'}")
    
    return "\n".join(status)

@mcp.tool()
def ai_chat(model: str, message: str, system: str = "") -> str:
    """AI对话"""
    try:
        if model == "ollama" or not _ai_config["openai_key"]:
            url = f"{_ai_config['ollama_url']}/api/generate"
            data = {"model": _ai_config["default_model"], "prompt": message, "stream": False}
            req = urllib.request.Request(url, data=json.dumps(data).encode(),
                                       headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode())["response"]
        
        if _ai_config["openai_key"]:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {_ai_config['openai_key']}"}
            msgs = []
            if system:
                msgs.append({"role": "system", "content": system})
            msgs.append({"role": "user", "content": message})
            data = {"model": model if "gpt" in model else "gpt-3.5-turbo", "messages": msgs}
            req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode())["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[ERROR] {e}"

# ============ 工具：远程 ============

@mcp.tool()
def remote_status(port: int = 8080) -> str:
    """远程服务状态"""
    return f"""[REMOTE]
This server supports MCP remote transport.
Start with: python professional_server.py --transport http --port {port}

Client config example:
{{
  "mcpServers": {{
    "pikachu-pro": {{
      "url": "http://your-server:{port}/mcp"
    }}
  }}
}}"""

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║     Pikachu Professional MCP Server ⚡                       ║
║     Database + NL2SQL + AI + Remote                          ║
╚══════════════════════════════════════════════════════════════╝
    """)
    mcp.run()
