"""
Pikachu NL2SQL MCP Server - 中文自然语言转SQL ⚡
核心优势：原生中文支持 + Local模型 + 准确率高

这才是真正超越Google的方向：他们不做中文NL2SQL
"""
from fastmcp import FastMCP
import json
import re
import urllib.request
from typing import Dict, List, Optional, Tuple

mcp = FastMCP("PikachuNL2SQL")

# ============ 配置 ============
_config = {
    "openai_key": "",
    "anthropic_key": "",
    "ollama_url": "http://localhost:11434",  # Ollama本地服务
    "default_model": "llama3.2",  # 默认模型
}

# 连接池
_pool: Dict[str, any] = {}

# ============ 工具函数 ============

def get_schema_for_prompt(db_name: str = "default") -> str:
    """生成用于NL2SQL的Schema描述"""
    if db_name not in _pool:
        return ""
    
    conn = _pool[db_name]
    cursor = conn.cursor()
    
    # 获取所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [r[0] for r in cursor.fetchall()]
    
    schema_parts = []
    for table in tables:
        schema_parts.append(f"### {table}")
        
        # 列信息
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        
        col_lines = []
        pk = []
        for col in columns:
            name, col_type, notnull, default, pk_flag = col[1], col[2], col[3], col[4], col[5]
            if pk_flag:
                pk.append(name)
            nullable = "NULL" if not notnull else "NOT NULL"
            default_val = f"DEFAULT {default}" if default else ""
            col_lines.append(f"  - {name} ({col_type}) {nullable} {default_val}")
        
        schema_parts.append("\n".join(col_lines))
        
        if pk:
            schema_parts.append(f"  PRIMARY KEY: {', '.join(pk)}")
        
        # 外键
        cursor.execute(f"PRAGMA foreign_key_list({table})")
        fks = cursor.fetchall()
        for fk in fks:
            schema_parts.append(f"  FOREIGN KEY: {fk[3]} -> {fk[2]}.{fk[4]}")
        
        # 索引
        cursor.execute(f"PRAGMA index_list({table})")
        indexes = cursor.fetchall()
        for idx in indexes:
            schema_parts.append(f"  INDEX: {idx[1]} (unique={idx[2]})")
        
        schema_parts.append("")
    
    return "\n".join(schema_parts)

def extract_sql_from_response(response: str) -> Optional[str]:
    """从AI响应中提取SQL语句"""
    # 移除markdown代码块
    response = response.strip()
    
    # 匹配 ```sql ... ``` 或 ``` ... ```
    patterns = [
        r"```sql\s*\n(.*?)\n```",
        r"```sql(.*?)```",
        r"```\s*\n(.*?)\n```",
        r"```(.*?)```",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            sql = match.group(1).strip()
            # 移除可能的注释
            sql = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
            return sql
    
    # 如果没有代码块，尝试直接提取SELECT/UPDATE/DELETE/INSERT
    patterns2 = [
        r"(SELECT\s+.+?;)",
        r"(UPDATE\s+.+?;)",
        r"(INSERT\s+.+?;)",
        r"(DELETE\s+.+?;)",
    ]
    
    for pattern in patterns2:
        match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
    
    return None

def validate_sql(sql: str, conn) -> Tuple[bool, str]:
    """验证SQL安全性"""
    sql_upper = sql.upper().strip()
    
    # 危险SQL检查
    dangerous = ["DROP", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE"]
    for kw in dangerous:
        if sql_upper.startswith(kw):
            return False, f"禁止执行的SQL: {kw}"
    
    # 只允许SELECT查询（可以扩展）
    if not sql_upper.startswith("SELECT"):
        return False, "仅支持SELECT查询"
    
    # 尝试解析（不执行）
    try:
        cursor = conn.cursor()
        cursor.execute(f"EXPLAIN QUERY PLAN {sql}")
        return True, "OK"
    except Exception as e:
        return False, f"SQL解析失败: {str(e)}"

# ============ NL2SQL核心 ============

@mcp.tool()
def nl2sql(query: str, db_name: str = "default", model: str = "ollama") -> str:
    """中文自然语言转SQL
    query: 中文问题，如'查询所有年龄大于20的用户'
    db_name: 数据库连接名
    model: ollama(默认)/openai/claude
    
    示例:
    - nl2sql("查询所有用户", "default")
    - nl2sql("找出销售额最高的前10个产品", "default")
    """
    if db_name not in _pool:
        return "[ERROR] 请先连接数据库: sqlite_connect 或 connect_database"
    
    conn = _pool[db_name]
    schema = get_schema_for_prompt(db_name)
    
    if not schema:
        return "[ERROR] 无法获取数据库结构"
    
    # 构建Prompt
    prompt = f"""你是一个SQL专家。根据用户的中文问题，生成准确的SQL查询。

数据库Schema:
{schema}

规则:
1. 只生成SELECT查询
2. 使用正确的SQL语法
3. 考虑表之间的关系（外键）
4. 返回简洁的SQL，不要多余解释

用户问题: {query}

请只返回SQL语句，不要其他内容:"""

    # 调用AI生成SQL
    sql = None
    
    if model == "ollama":
        sql = _call_ollama(prompt)
    elif model == "openai" and _config["openai_key"]:
        sql = _call_openai(prompt)
    elif model == "claude" and _config["anthropic_key"]:
        sql = _call_anthropic(prompt)
    else:
        # 默认尝试ollama
        sql = _call_ollama(prompt)
        if not sql:
            return "[ERROR] 请启动Ollama服务或配置API密钥\nOllama: ollama serve"
    
    if not sql:
        return "[ERROR] 未能生成SQL"
    
    # 提取SQL
    clean_sql = extract_sql_from_response(sql)
    if not clean_sql:
        return f"[ERROR] 无法解析SQL\n原始响应:\n{sql}"
    
    # 验证SQL
    valid, msg = validate_sql(clean_sql, conn)
    if not valid:
        return f"[ERROR] SQL验证失败: {msg}"
    
    # 执行SQL预览（不返回数据，只验证）
    try:
        cursor = conn.cursor()
        cursor.execute(f"EXPLAIN QUERY PLAN {clean_sql}")
        plan = cursor.fetchall()
        plan_str = "\n".join([str(p) for p in plan])
        
        return f"""[NL2SQL SUCCESS]

[问题] {query}

[生成SQL]
```sql
{clean_sql}
```

[执行计划]
{plan_str}

[使用说明]
如需执行此SQL，请使用 execute_sql 工具"""
    
    except Exception as e:
        return f"[ERROR] SQL验证失败: {str(e)}\n\n生成的SQL:\n{clean_sql}"

def _call_ollama(prompt: str) -> Optional[str]:
    """调用本地Ollama"""
    try:
        import urllib.request
        url = f"{_config['ollama_url']}/api/generate"
        data = {
            "model": _config["default_model"],
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 500
            }
        }
        
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            return result.get("response", "")
    except Exception as e:
        return None

def _call_openai(prompt: str) -> Optional[str]:
    """调用OpenAI"""
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_config['openai_key']}"
        }
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 500
        }
        
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method="POST")
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            return result["choices"][0]["message"]["content"]
    except:
        return None

def _call_anthropic(prompt: str) -> Optional[str]:
    """调用Claude"""
    try:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": _config["anthropic_key"],
            "anthropic-version": "2023-06-01"
        }
        data = {
            "model": "claude-3-haiku-20240229",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method="POST")
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            return result["content"][0]["text"]
    except:
        return None

# ============ 数据库连接 ============

@mcp.tool()
def sqlite_connect(db_path: str, name: str = "default") -> str:
    """连接SQLite数据库（NL2SQL专用）"""
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        _pool[name] = conn
        
        # 获取基本信息
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [r[0] for r in cursor.fetchall()]
        
        return f"""[SQLITE CONNECTED]
名称: {name}
路径: {db_path}
表数量: {len(tables)}
表: {', '.join(tables)}"""
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def connect_database(db_type: str, name: str = "default", 
                   host: str = "localhost", port: int = 3306, 
                   user: str = "root", password: str = "", 
                   database: str = "", path: str = "./data.db") -> str:
    """连接数据库"""
    if db_type == "sqlite":
        return sqlite_connect(path, name)
    
    return "[ERROR] 目前只支持SQLite"

@mcp.tool()
def get_schema(db_name: str = "default") -> str:
    """获取数据库Schema（用于NL2SQL）"""
    if db_name not in _pool:
        return "[ERROR] 请先连接数据库"
    
    schema = get_schema_for_prompt(db_name)
    
    if not schema:
        return "[EMPTY] 数据库为空"
    
    return f"[DATABASE SCHEMA]\n{schema}"

# ============ NL2SQL执行 ============

@mcp.tool()
def nl2sql_execute(query: str, db_name: str = "default", model: str = "ollama") -> str:
    """中文自然语言查询（直接返回结果）
    query: 中文问题
    db_name: 数据库名称
    model: 使用的模型
    
    示例:
    - nl2sql_execute("查询用户表有多少条记录", "default")
    """
    if db_name not in _pool:
        return "[ERROR] 请先连接数据库"
    
    # 先NL2SQL
    nl2sql_result = nl2sql(query, db_name, model)
    
    if nl2sql_result.startswith("[ERROR]"):
        return nl2sql_result
    
    # 提取SQL
    sql_match = re.search(r"```sql\s*\n(.*?)\n```", nl2sql_result, re.DOTALL)
    if not sql_match:
        return nl2sql_result
    
    sql = sql_match.group(1).strip()
    
    # 执行SQL
    try:
        conn = _pool[db_name]
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        
        if not rows:
            return f"[EMPTY] 查询无结果\n\nSQL:\n{sql}"
        
        # 格式化结果
        result = f"[RESULT] ({len(rows)} rows)\n"
        result += f"SQL: {sql}\n\n"
        result += " | ".join(f"{c:<20}" for c in columns) + "\n"
        result += "-" * 60 * 2 + "\n"
        
        for row in rows[:50]:
            result += " | ".join(f"{str(row[i]):<20}" for i in range(len(columns))) + "\n"
        
        if len(rows) > 50:
            result += f"\n... and {len(rows) - 50} more rows"
        
        return result
    
    except Exception as e:
        return f"[ERROR] 执行失败: {str(e)}\n\nSQL:\n{sql}"

# ============ 配置 ============

@mcp.tool()
def configure_nl2sql(ollama_url: str = "http://localhost:11434", 
                    default_model: str = "llama3.2",
                    openai_key: str = "", anthropic_key: str = "") -> str:
    """配置NL2SQL"""
    if ollama_url:
        _config["ollama_url"] = ollama_url
    if default_model:
        _config["default_model"] = default_model
    if openai_key:
        _config["openai_key"] = openai_key
    if anthropic_key:
        _config["anthropic_key"] = anthropic_key
    
    configured = []
    configured.append(f"Ollama: {_config['ollama_url']} ({_config['default_model']})")
    if _config["openai_key"]:
        configured.append("OpenAI: ✅")
    if _config["anthropic_key"]:
        configured.append("Claude: ✅")
    
    return "[NL2SQL CONFIGURED]\n" + "\n".join(configured)

@mcp.tool()
def check_ollama() -> str:
    """检查Ollama服务状态"""
    try:
        import urllib.request
        url = f"{_config['ollama_url']}/api/tags"
        req = urllib.request.Request(url)
        
        with urllib.request.urlopen(req, timeout=5) as response:
            models = json.loads(response.read().decode())
            
            result = "[OLLAMA ONLINE]\n"
            result += f"URL: {_config['ollama_url']}\n"
            result += f"已安装模型:\n"
            
            for m in models.get("models", []):
                result += f"  - {m['name']}\n"
            
            return result
    except Exception as e:
        return f"[OLLAMA OFFLINE]\n{str(e)}\n\n启动Ollama: ollama serve"

@mcp.tool()
def test_nl2sql(question: str = "查询所有表", db_name: str = "default") -> str:
    """测试NL2SQL"""
    return nl2sql(question, db_name)

if __name__ == "__main__":
    mcp.run()
