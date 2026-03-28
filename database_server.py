"""
Pikachu Database MCP Server ⚡
MySQL/PostgreSQL/SQLite 数据库操作
"""
from fastmcp import FastMCP
import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager

mcp = FastMCP("PikachuDatabase")

# 存储数据库连接信息
_connections = {}

@mcp.tool()
def sqlite_connect(db_path: str) -> str:
    """连接SQLite数据库"""
    try:
        conn = sqlite3.connect(db_path)
        _connections['sqlite_default'] = conn
        cursor = conn.cursor()
        cursor.execute("SELECT sqlite_version()")
        version = cursor.fetchone()[0]
        return f"[SQLITE] Connected!\nDatabase: {db_path}\nSQLite Version: {version}"
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def sqlite_execute(query: str, params: str = "{}") -> str:
    """执行SQL查询"""
    try:
        if 'sqlite_default' not in _connections:
            return "[ERROR] Not connected. Use sqlite_connect first."
        
        conn = _connections['sqlite_default']
        cursor = conn.cursor()
        
        # 判断是查询还是修改
        query_lower = query.strip().lower()
        if query_lower.startswith('select'):
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            if not rows:
                return "[RESULT] Query returned no rows"
            
            # 格式化输出
            result = f"[SQL] Query Results ({len(rows)} rows)\n"
            result += "-" * 60 + "\n"
            result += " | ".join(columns) + "\n"
            result += "-" * 60 + "\n"
            
            for row in rows[:20]:  # 限制最多20行
                result += " | ".join([str(v) for v in row]) + "\n"
            
            if len(rows) > 20:
                result += f"\n... and {len(rows) - 20} more rows"
            
            return result
        else:
            cursor.execute(query)
            conn.commit()
            return f"[OK] Query executed. {cursor.rowcount} rows affected."
            
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def sqlite_create_table(table_name: str, columns: str) -> str:
    """创建表
    columns格式: {'name': 'TEXT', 'age': 'INTEGER', 'email': 'TEXT'}
    """
    try:
        if 'sqlite_default' not in _connections:
            return "[ERROR] Not connected. Use sqlite_connect first."
        
        conn = _connections['sqlite_default']
        cursor = conn.cursor()
        
        col_defs = []
        cols_dict = json.loads(columns) if isinstance(columns, str) else columns
        
        for name, col_type in cols_dict.items():
            col_defs.append(f"{name} {col_type}")
        
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(col_defs)})"
        cursor.execute(sql)
        conn.commit()
        
        return f"[OK] Table '{table_name}' created successfully!"
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def sqlite_insert(table_name: str, data: str) -> str:
    """插入数据
    data格式: {'name': 'John', 'age': 25}
    """
    try:
        if 'sqlite_default' not in _connections:
            return "[ERROR] Not connected. Use sqlite_connect first."
        
        conn = _connections['sqlite_default']
        cursor = conn.cursor()
        
        data_dict = json.loads(data) if isinstance(data, str) else data
        columns = list(data_dict.keys())
        placeholders = ['?' for _ in columns]
        values = list(data_dict.values())
        
        sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        cursor.execute(sql, values)
        conn.commit()
        
        return f"[OK] Row inserted! ID: {cursor.lastrowid}"
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def sqlite_list_tables() -> str:
    """列出所有表"""
    try:
        if 'sqlite_default' not in _connections:
            return "[ERROR] Not connected. Use sqlite_connect first."
        
        conn = _connections['sqlite_default']
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        if not tables:
            return "[EMPTY] No tables in database"
        
        result = "[TABLES]\n" + "=" * 40 + "\n"
        for (table_name,) in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            result += f"  {table_name} ({count} rows)\n"
        
        return result
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def sqlite_disconnect() -> str:
    """断开数据库连接"""
    try:
        if 'sqlite_default' in _connections:
            _connections['sqlite_default'].close()
            del _connections['sqlite_default']
            return "[OK] Disconnected from database"
        return "[INFO] Not connected"
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def csv_to_sqlite(csv_path: str, table_name: str) -> str:
    """导入CSV到SQLite"""
    try:
        import csv
        
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            if not rows:
                return "[ERROR] CSV file is empty"
            
            # 获取列
            columns = list(rows[0].keys())
            col_types = {col: 'TEXT' for col in columns}
            
            # 创建表
            col_defs = [f"{k} {v}" for k, v in col_types.items()]
            cursor.execute(f"CREATE TABLE {table_name} ({', '.join(col_defs)})")
            
            # 插入数据
            for row in rows:
                placeholders = ['?' for _ in columns]
                values = [row[col] for col in columns]
                cursor.execute(f"INSERT INTO {table_name} VALUES ({', '.join(placeholders)})", values)
        
        conn.commit()
        _connections['sqlite_default'] = conn
        
        return f"[OK] CSV imported! {len(rows)} rows into table '{table_name}'"
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def export_to_csv(query: str, output_path: str) -> str:
    """导出查询结果到CSV"""
    try:
        if 'sqlite_default' not in _connections:
            return "[ERROR] Not connected. Use sqlite_connect first."
        
        import csv
        
        conn = _connections['sqlite_default']
        cursor = conn.cursor()
        cursor.execute(query)
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)
        
        return f"[OK] Exported {len(rows)} rows to {output_path}"
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def sql_query_builder(table: str, operation: str, filters: str = "{}") -> str:
    """SQL查询构建器
    operation: select, insert, update, delete
    filters: WHERE条件
    """
    try:
        filters_dict = json.loads(filters) if isinstance(filters, str) else filters
        
        if operation == "select":
            cols = filters_dict.get('columns', '*')
            where = filters_dict.get('where', '')
            limit = filters_dict.get('limit', '')
            
            sql = f"SELECT {cols} FROM {table}"
            if where:
                sql += f" WHERE {where}"
            if limit:
                sql += f" LIMIT {limit}"
            
            return f"[SQL]\n{sql}"
        
        elif operation == "insert":
            data = filters_dict.get('data', {})
            cols = list(data.keys())
            vals = list(data.values())
            
            sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(['?' for _ in vals])})"
            
            return f"[SQL]\n{sql}\n\n[VALUES]\n{json.dumps(vals, indent=2)}"
        
        return "[ERROR] Unknown operation"
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

if __name__ == "__main__":
    mcp.run()
