"""
Pikachu File Processing MCP Server ⚡
PDF/Excel/Word/CSV 文件处理
"""
from fastmcp import FastMCP
import json
import csv
import os
from datetime import datetime

mcp = FastMCP("PikachuFile")

@mcp.tool()
def read_csv(file_path: str, max_rows: int = 100) -> str:
    """读取CSV文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        if not rows:
            return "[EMPTY] CSV file is empty"
        
        # 获取列
        columns = list(rows[0].keys())
        
        result = f"[CSV READY]\n{'='*50}\n"
        result += f"File: {file_path}\n"
        result += f"Total rows: {len(rows)}\n"
        result += f"Columns: {', '.join(columns)}\n"
        result += f"{'='*50}\n\n"
        
        # 显示前几行
        result += "[FIRST 10 ROWS]\n"
        for i, row in enumerate(rows[:10], 1):
            result += f"{i}. " + " | ".join([f"{k}={row[k]}" for k in columns[:5]]) + "\n"
        
        if len(rows) > 10:
            result += f"\n... and {len(rows) - 10} more rows"
        
        return result
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def write_csv(file_path: str, data: str, columns: str) -> str:
    """写入CSV文件
    data: JSON数组格式
    columns: 逗号分隔的列名
    """
    try:
        data_list = json.loads(data) if isinstance(data, str) else data
        col_list = [c.strip() for c in columns.split(',')]
        
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=col_list)
            writer.writeheader()
            writer.writerows(data_list)
        
        return f"[OK] CSV written!\nFile: {file_path}\nRows: {len(data_list)}\nColumns: {columns}"
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def append_csv(file_path: str, row_data: str) -> str:
    """追加CSV行
    row_data: JSON对象格式
    """
    try:
        row = json.loads(row_data) if isinstance(row_data, str) else row_data
        
        file_exists = os.path.exists(file_path)
        
        with open(file_path, 'a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow(row)
        
        return f"[OK] Row appended to {file_path}"
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def csv_stats(file_path: str) -> str:
    """CSV文件统计"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        if not rows:
            return "[EMPTY] CSV file is empty"
        
        headers = rows[0]
        data_rows = rows[1:]
        
        # 统计每列
        col_stats = []
        for i, header in enumerate(headers):
            values = [row[i] for row in data_rows if i < len(row) and row[i]]
            col_stats.append({
                "name": header,
                "count": len(values),
                "empty": len(data_rows) - len(values)
            })
        
        result = f"[CSV STATS]\n{'='*50}\n"
        result += f"File: {os.path.basename(file_path)}\n"
        result += f"Total rows: {len(data_rows)}\n"
        result += f"Columns: {len(headers)}\n\n"
        result += "[COLUMN DETAILS]\n"
        
        for stat in col_stats:
            result += f"  {stat['name']}: {stat['count']} values, {stat['empty']} empty\n"
        
        return result
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def filter_csv(file_path: str, condition: str) -> str:
    """CSV数据筛选
    condition: JSON格式筛选条件
    例: {"column": "age", "operator": ">", "value": 18}
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        cond = json.loads(condition) if isinstance(condition, str) else condition
        col = cond.get("column")
        op = cond.get("operator")
        val = cond.get("value")
        
        # 筛选
        filtered = []
        for row in rows:
            if col not in row:
                continue
            
            row_val = row[col]
            
            try:
                row_val_num = float(row_val)
                val_num = float(val)
                
                if op == ">":
                    if row_val_num > val_num:
                        filtered.append(row)
                elif op == "<":
                    if row_val_num < val_num:
                        filtered.append(row)
                elif op == ">=":
                    if row_val_num >= val_num:
                        filtered.append(row)
                elif op == "<=":
                    if row_val_num <= val_num:
                        filtered.append(row)
                elif op == "==":
                    if row_val_num == val_num:
                        filtered.append(row)
            except:
                # 字符串比较
                if op == "==":
                    if row_val == val:
                        filtered.append(row)
                elif op == "contains":
                    if val in row_val:
                        filtered.append(row)
        
        result = f"[FILTERED]\n{'='*50}\n"
        result += f"Original rows: {len(rows)}\n"
        result += f"Filtered rows: {len(filtered)}\n"
        result += f"Condition: {col} {op} {val}\n\n"
        
        if filtered:
            columns = list(filtered[0].keys())
            result += "[FIRST 10 RESULTS]\n"
            for i, row in enumerate(filtered[:10], 1):
                result += f"{i}. " + " | ".join([f"{k}={row[k]}" for k in columns[:4]]) + "\n"
        
        return result
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def merge_csv(file1: str, file2: str, output: str, how: str = "concat") -> str:
    """合并CSV文件
    how: concat (纵向合并) 或 join (横向连接)
    """
    try:
        # 读取file1
        with open(file1, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data1 = list(reader)
            cols1 = reader.fieldnames
        
        # 读取file2
        with open(file2, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data2 = list(reader)
            cols2 = reader.fieldnames
        
        if how == "concat":
            # 纵向合并
            combined = data1 + data2
            
            all_cols = list(set(cols1) | set(cols2))
            
            with open(output, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=all_cols)
                writer.writeheader()
                writer.writerows(combined)
            
            return f"[MERGED] Concat complete!\nFile: {output}\nRows: {len(data1)} + {len(data2)} = {len(combined)}\nColumns: {len(all_cols)}"
        
        else:
            return "[ERROR] join merge not yet supported. Use 'concat'"
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def csv_to_json(file_path: str, output: str) -> str:
    """CSV转JSON"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        
        return f"[OK] CSV to JSON done!\nInput: {file_path}\nOutput: {output}\nRows: {len(rows)}"
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def json_to_csv(json_file: str, output: str) -> str:
    """JSON转CSV"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data:
            return "[ERROR] JSON file is empty"
        
        columns = list(data[0].keys())
        
        with open(output, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(data)
        
        return f"[OK] JSON to CSV done!\nInput: {json_file}\nOutput: {output}\nRows: {len(data)}"
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def file_info(file_path: str) -> str:
    """获取文件信息"""
    try:
        stat = os.stat(file_path)
        
        result = f"[FILE INFO]\n{'='*50}\n"
        result += f"Name: {os.path.basename(file_path)}\n"
        result += f"Path: {file_path}\n"
        result += f"Size: {stat.st_size:,} bytes ({stat.st_size/1024:.1f} KB)\n"
        result += f"Modified: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}\n"
        result += f"Created: {datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')}\n"
        result += f"Extension: {os.path.splitext(file_path)[1]}\n"
        
        return result
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def create_backup(file_path: str) -> str:
    """创建文件备份"""
    try:
        import shutil
        
        base, ext = os.path.splitext(file_path)
        backup_path = f"{base}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        
        shutil.copy2(file_path, backup_path)
        
        return f"[OK] Backup created!\nOriginal: {file_path}\nBackup: {backup_path}"
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

if __name__ == "__main__":
    mcp.run()
