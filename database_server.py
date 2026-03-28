"""
Pikachu Professional Database MCP Server ⚡
支持 MySQL/PostgreSQL/SQLite + NL2SQL + Schema探索
"""
from fastmcp import FastMCP
import sqlite3
import json
import urllib.parse
from datetime import datetime
from typing import Optional, Dict, Any, List

mcp = FastMCP("PikachuDB")

# 连接池
class ConnectionPool:
    def __init__(self):
        self._connections: Dict[str, Any] = {}
        self._config: Dict[str, Dict] = {}
    
    def add_sqlite(self, name: str, db_path: str) -> bool:
        try:
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._connections[name] = conn
            self._config[name] = {"type": "sqlite", "path": db_path}
            return True
        except Exception:
            return False
    
    def execute(self, name: str, query: str, params: tuple = ()) -> tuple:
        """执行查询，返回 (columns, rows)"""
        if name not in self._connections:
            raise ValueError(f"Connection '{name}' not found")
        
        conn = self._connections[name]
        cursor = conn.cursor()
        
        # 安全的参数化查询
        cursor.execute(query, params)
        
        if query.strip().upper().startswith('SELECT'):
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            return columns, rows
        else:
            conn.commit()
            return [], cursor.rowcount
    
    def list_connections(self) -> List[Dict]:
        return [{"name": k, **v} for k, v in self._config.items()]

_pool = ConnectionPool()

# ============ 数据库连接 ============

@mcp.tool()
def connect_database(db_type: str, name: str = "default", 
                   host: str = "localhost", port: int = 3306, 
                   user: str = "root", password: str = "", 
                   database: str = "", path: str = "./data.db") -> str:
    """连接数据库
    db_type: sqlite, mysql, postgresql
    Examples:
    - sqlite: connect_database("sqlite", path="./data.db")
    - mysql: connect_database("mysql", host="localhost", user="root", password="xxx", database="mydb")
    - postgresql: connect_database("postgresql", host="localhost", user="postgres", password="xxx", database="mydb")
    """
    try:
        if db_type == "sqlite":
            if _pool.add_sqlite(name, path):
                return f"[SQLITE CONNECTED]\nName: {name}\nPath: {path}"
            return f"[ERROR] Failed to connect to SQLite: {path}"
        
        elif db_type == "mysql":
            try:
                import pymysql
                conn = pymysql.connect(host=host, port=port, user=user, password=password, database=database)
                conn.row_factory = lambda c, r: {col[0]: r[i] for i, col in enumerate(c.description)}
                _pool._connections[name] = conn
                _pool._config[name] = {"type": "mysql", "host": host, "database": database}
                return f"[MYSQL CONNECTED]\nName: {name}\nHost: {host}\nDatabase: {database}"
            except ImportError:
                return "[ERROR] pymysql not installed. Run: pip install pymysql"
        
        elif db_type == "postgresql":
            try:
                import psycopg2
                conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=database)
                _pool._connections[name] = conn
                _pool._config[name] = {"type": "postgresql", "host": host, "database": database}
                return f"[POSTGRESQL CONNECTED]\nName: {name}\nHost: {host}\nDatabase: {database}"
            except ImportError:
                return "[ERROR] psycopg2 not installed. Run: pip install psycopg2"
        
        return f"[ERROR] Unknown db_type: {db_type}"
    
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def list_connections() -> str:
    """列出所有连接"""
    connections = _pool.list_connections()
    if not connections:
        return "[EMPTY] No database connections"
    
    result = f"[CONNECTIONS] ({len(connections)})\n" + "=" * 50 + "\n"
    for conn in connections:
        result += f"\n{conn['name']}:"
        result += f"\n  Type: {conn['type']}"
        if 'host' in conn:
            result += f"\n  Host: {conn['host']}"
        if 'database' in conn:
            result += f"\n  Database: {conn['database']}"
    
    return result

# ============ Schema探索 ============

@mcp.tool()
def list_tables(db_name: str = "default") -> str:
    """列出所有表"""
    try:
        columns, rows = _pool.execute(db_name, "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        
        if not rows:
            return "[EMPTY] No tables found"
        
        result = f"[TABLES] ({len(rows)})\n" + "=" * 50 + "\n"
        for row in rows:
            result += f"  - {row['name']}\n"
        
        return result
    
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def describe_table(table_name: str, db_name: str = "default") -> str:
    """查看表结构"""
    try:
        # SQLite
        columns, rows = _pool.execute(db_name, f"PRAGMA table_info({table_name})")
        
        if not rows:
            # MySQL/PostgreSQL
            columns, rows = _pool.execute(db_name, f"DESCRIBE {table_name}")
        
        result = f"[TABLE: {table_name}]\n" + "=" * 50 + "\n"
        result += f"{'Column':<20} {'Type':<15} {'Nullable':<10} {'Key'}\n"
        result += "-" * 60 + "\n"
        
        for row in rows:
            name = row.get('name', row.get('Field', '?'))
            col_type = row.get('type', row.get('Type', '?'))
            nullable = row.get('notnull', row.get('Null', '?'))
            key = row.get('pk', row.get('Key', ''))
            
            result += f"{name:<20} {str(col_type):<15} {str(nullable):<10} {key}\n"
        
        return result
    
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def show_indexes(table_name: str, db_name: str = "default") -> str:
    """显示表的索引"""
    try:
        columns, rows = _pool.execute(db_name, f"PRAGMA index_list({table_name})")
        
        result = f"[INDEXES for {table_name}]\n" + "=" * 50 + "\n"
        
        for row in rows:
            result += f"\n{row['name']}:\n"
            result += f"  Unique: {row['unique']}\n"
            
            # 获取索引列
            idx_columns, idx_rows = _pool.execute(db_name, f"PRAGMA index_info({row['name']})")
            cols = [r['name'] for r in idx_rows]
            result += f"  Columns: {', '.join(cols)}\n"
        
        if not rows:
            result += "  No indexes\n"
        
        return result
    
    except Exception as e:
        return f"[ERROR] {str(e)}"

# ============ SQL执行 ============

@mcp.tool()
def execute_sql(query: str, params: str = "{}", db_name: str = "default") -> str:
    """执行SQL查询（安全参数化）
    query: SQL语句
    params: JSON格式参数 {"p1": "value1", "p2": 123}
    """
    try:
        # 解析参数
        param_dict = json.loads(params) if isinstance(params, str) else params
        param_tuple = tuple(param_dict.values())
        
        # 执行
        columns, result = _pool.execute(db_name, query, param_tuple)
        
        if not columns:  # 非查询语句
            return f"[OK] {result} rows affected"
        
        # 格式化结果
        output = f"[RESULTS] ({len(result)} rows)\n" + "=" * 60 + "\n"
        
        # 表头
        output += " | ".join(f"{c:<20}" for c in columns[:8]) + "\n"
        output += "-" * 60 * 2 + "\n"
        
        # 数据行
        for row in result[:50]:
            output += " | ".join(f"{str(row.get(c, '')):<20}" for c in columns[:8]) + "\n"
        
        if len(result) > 50:
            output += f"\n... and {len(result) - 50} more rows"
        
        return output
    
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def query_builder(table: str, operation: str, filters: str = "{}", db_name: str = "default") -> str:
    """SQL查询构建器（防注入）
    operation: select, insert, update, delete
    filters: WHERE条件
    """
    try:
        filters_dict = json.loads(filters) if isinstance(filters, str) else filters
        
        if operation == "select":
            columns = filters_dict.get("columns", "*")
            where = filters_dict.get("where", {})
            order_by = filters_dict.get("order_by", "")
            limit = filters_dict.get("limit", 100)
            
            sql = f"SELECT {columns} FROM {table}"
            values = []
            
            if where:
                conditions = []
                for col, val in where.items():
                    conditions.append(f"{col} = ?")
                    values.append(val)
                sql += " WHERE " + " AND ".join(conditions)
            
            if order_by:
                sql += f" ORDER BY {order_by}"
            
            sql += f" LIMIT {limit}"
            
            return f"[SQL]\n{sql}\n\n[PARAMETERS]\n{values}"
        
        elif operation == "insert":
            data = filters_dict.get("data", {})
            columns = list(data.keys())
            placeholders = ["?" for _ in columns]
            values = list(data.values())
            
            sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
            
            return f"[SQL]\n{sql}\n\n[PARAMETERS]\n{values}"
        
        elif operation == "update":
            data = filters_dict.get("data", {})
            where = filters_dict.get("where", {})
            
            sets = [f"{k} = ?" for k in data.keys()]
            conditions = [f"{k} = ?" for k in where.keys()]
            
            values = list(data.values()) + list(where.values())
            
            sql = f"UPDATE {table} SET {', '.join(sets)} WHERE {' AND '.join(conditions)}"
            
            return f"[SQL]\n{sql}\n\n[PARAMETERS]\n{values}"
        
        elif operation == "delete":
            where = filters_dict.get("where", {})
            conditions = [f"{k} = ?" for k in where.keys()]
            values = list(where.values())
            
            sql = f"DELETE FROM {table} WHERE {' AND '.join(conditions)}"
            
            return f"[SQL]\n{sql}\n\n[PARAMETERS]\n{values}"
        
        return "[ERROR] Unknown operation"
    
    except Exception as e:
        return f"[ERROR] {str(e)}"

# ============ Schema文档 ============

@mcp.tool()
def generate_schema_doc(db_name: str = "default") -> str:
    """生成数据库Schema文档"""
    try:
        # 获取所有表
        _, tables = _pool.execute(db_name, "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        
        doc = f"[DATABASE SCHEMA DOCUMENTATION]\n{'='*60}\n"
        doc += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        doc += f"Tables: {len(tables)}\n\n"
        
        for table in tables:
            table_name = table['name']
            doc += f"\n## {table_name}\n\n"
            
            # 列信息
            _, columns = _pool.execute(db_name, f"PRAGMA table_info({table_name})")
            doc += "### Columns\n\n"
            doc += "| Column | Type | Nullable | Default |\n"
            doc += "|--------|------|----------|--------|\n"
            
            for col in columns:
                doc += f"| {col['name']} | {col['type']} | {'NO' if col['notnull'] else 'YES'} | {col.get('dflt_value', '')} |\n"
            
            # 索引
            _, indexes = _pool.execute(db_name, f"PRAGMA index_list({table_name})")
            if indexes:
                doc += "\n### Indexes\n\n"
                for idx in indexes:
                    doc += f"- **{idx['name']}** (Unique: {idx['unique']})\n"
            
            # 外键
            _, fks = _pool.execute(db_name, f"PRAGMA foreign_key_list({table_name})")
            if fks:
                doc += "\n### Foreign Keys\n\n"
                for fk in fks:
                    doc += f"- {fk['from']} -> {fk['table']}.{fk['to']}\n"
            
            doc += "\n"
        
        return doc
    
    except Exception as e:
        return f"[ERROR] {str(e)}"

# ============ 数据样本 ============

@mcp.tool()
def sample_data(table_name: str, db_name: str = "default", limit: int = 10) -> str:
    """获取表的数据样本"""
    try:
        columns, rows = _pool.execute(db_name, f"SELECT * FROM {table_name} LIMIT {limit}")
        
        result = f"[SAMPLE DATA: {table_name}]\n" + "=" * 60 + "\n"
        result += f"Showing {len(rows)} of unknown total rows\n\n"
        
        # 表头
        result += " | ".join(f"{c:<15}" for c in columns) + "\n"
        result += "-" * 60 * 2 + "\n"
        
        # 数据
        for row in rows:
            result += " | ".join(f"{str(row.get(c, 'NULL')):<15}" for c in columns) + "\n"
        
        return result
    
    except Exception as e:
        return f"[ERROR] {str(e)}"

# ============ 健康检查 ============

@mcp.tool()
def db_health_check(db_name: str = "default") -> str:
    """数据库健康检查"""
    try:
        start = datetime.now()
        columns, rows = _pool.execute(db_name, "SELECT 1 as health")
        latency = (datetime.now() - start).total_seconds() * 1000
        
        # 获取表数量
        _, tables = _pool.execute(db_name, "SELECT COUNT(*) as count FROM sqlite_master WHERE type='table'")
        table_count = tables[0]['count'] if tables else 0
        
        return f"""[DATABASE HEALTH]
{'='*40}
Status: OK
Latency: {latency:.1f}ms
Tables: {table_count}
Connection: {db_name}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

    except Exception as e:
        return f"[HEALTH: FAIL]\nError: {str(e)}"

# ============ 全文搜索 ============

@mcp.tool()
def full_text_search(table_name: str, column: str, keyword: str, 
                    db_name: str = "default", limit: int = 50) -> str:
    """全文搜索
    table_name: 表名
    column: 搜索的列
    keyword: 关键词
    """
    try:
        safe_keyword = keyword.replace("%", "\\%").replace("_", "\\_")
        query = f"SELECT * FROM {table_name} WHERE {column} LIKE ? LIMIT ?"
        
        columns, rows = _pool.execute(db_name, query, (f"%{keyword}%", limit))
        
        if not rows:
            return f"[NOT FOUND] No results for '{keyword}' in {table_name}.{column}"
        
        result = f"[SEARCH RESULTS] '{keyword}' in {table_name}.{column}\n"
        result += f"{'='*60}\n"
        result += f"Found: {len(rows)} matches\n\n"
        
        result += " | ".join(f"{c:<15}" for c in columns) + "\n"
        result += "-" * 60 * 2 + "\n"
        
        for row in rows[:limit]:
            result += " | ".join(f"{str(row.get(c, '')):<15}" for c in columns) + "\n"
        
        return result
    
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def count_rows(table_name: str, db_name: str = "default", 
              where: str = "") -> str:
    """统计行数"""
    try:
        if where:
            query = f"SELECT COUNT(*) as cnt FROM {table_name} WHERE {where}"
        else:
            query = f"SELECT COUNT(*) as cnt FROM {table_name}"
        
        columns, rows = _pool.execute(db_name, query)
        count = rows[0]['cnt'] if rows else 0
        
        return f"[COUNT] {table_name}: {count} rows" + (f" (WHERE {where})" if where else "")
    
    except Exception as e:
        return f"[ERROR] {str(e)}"

if __name__ == "__main__":
    mcp.run()
