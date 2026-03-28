"""
Pikachu MCP Servers - 通用工具库 ⚡
包含：日志、错误处理、性能追踪
"""
import time
import json
import traceback
from datetime import datetime
from typing import Any, Dict, Optional

# ============ 日志系统 ============
class Logger:
    def __init__(self, name: str = "Pikachu"):
        self.name = name
        self.logs: list = []
        self.max_logs = 1000
    
    def log(self, level: str, message: str, context: Dict = None):
        """记录日志"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "context": context or {}
        }
        self.logs.append(entry)
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]
        return entry
    
    def info(self, message: str, **kwargs):
        return self.log("INFO", message, kwargs)
    
    def warn(self, message: str, **kwargs):
        return self.log("WARN", message, kwargs)
    
    def error(self, message: str, **kwargs):
        return self.log("ERROR", message, kwargs)
    
    def debug(self, message: str, **kwargs):
        return self.log("DEBUG", message, kwargs)
    
    def get_logs(self, level: str = None, limit: int = 100) -> list:
        if level:
            return [l for l in self.logs if l["level"] == level][-limit:]
        return self.logs[-limit:]

# 全局日志
_logger = Logger()

# ============ 错误处理 ============
class MCPError(Exception):
    """MCP服务器专用错误"""
    def __init__(self, message: str, code: str = "UNKNOWN", details: Dict = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
    
    def to_dict(self) -> Dict:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details
            }
        }

def safe_execute(func):
    """安全执行装饰器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except MCPError as e:
            _logger.error(str(e), code=e.code)
            return f"[ERROR:{e.code}] {e.message}"
        except Exception as e:
            _logger.error(str(e), error_type=type(e).__name__)
            return f"[ERROR] {str(e)}"
    return wrapper

# ============ 性能追踪 ============
class PerformanceTracker:
    """性能追踪"""
    def __init__(self):
        self.records: Dict[str, list] = {}
    
    def track(self, operation: str, duration_ms: float, metadata: Dict = None):
        if operation not in self.records:
            self.records[operation] = []
        self.records[operation].append({
            "timestamp": time.time(),
            "duration_ms": duration_ms,
            "metadata": metadata or {}
        })
        # 保留最近1000条
        if len(self.records[operation]) > 1000:
            self.records[operation] = self.records[operation][-1000:]
    
    def get_stats(self, operation: str) -> Dict:
        if operation not in self.records:
            return {}
        
        records = self.records[operation]
        durations = [r["duration_ms"] for r in records]
        
        return {
            "count": len(durations),
            "min_ms": min(durations),
            "max_ms": max(durations),
            "avg_ms": sum(durations) / len(durations),
            "total_ms": sum(durations)
        }
    
    def get_all_stats(self) -> Dict:
        return {op: self.get_stats(op) for op in self.records}

# 全局追踪器
_tracker = PerformanceTracker()

# ============ 格式化工具 ============
def format_table(headers: list, rows: list, max_width: int = 20) -> str:
    """格式化表格"""
    if not rows:
        return "No data"
    
    # 计算列宽
    widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = min(max(widths[i], len(str(cell))), max_width)
    
    # 表头
    header = " | ".join(str(h)[:w].ljust(w) for h, w in zip(headers, widths))
    separator = "-+-".join("-" * w for w in widths)
    
    # 数据行
    data_lines = []
    for row in rows[:50]:  # 最多50行
        line = " | ".join(str(cell)[:w].ljust(w) for cell, w in zip(row, widths))
        data_lines.append(line)
    
    result = header + "\n" + separator + "\n" + "\n".join(data_lines)
    
    if len(rows) > 50:
        result += f"\n... and {len(rows) - 50} more rows"
    
    return result

def format_duration(seconds: float) -> str:
    """格式化时长"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"

def format_bytes(size: int) -> str:
    """格式化字节"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}PB"

def truncate(text: str, max_len: int = 100, suffix: str = "...") -> str:
    """截断文本"""
    if len(text) <= max_len:
        return text
    return text[:max_len - len(suffix)] + suffix

# ============ 验证工具 ============
def validate_sql(query: str, allowed_prefixes: tuple = ("SELECT",)) -> tuple:
    """验证SQL安全性"""
    query_upper = query.strip().upper()
    
    # 检查危险关键字
    dangerous = ["DROP", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE"]
    for kw in dangerous:
        if query_upper.startswith(kw):
            return False, f"Forbidden SQL command: {kw}"
    
    # 检查是否以允许的关键字开头
    if not any(query_upper.startswith(p) for p in allowed_prefixes):
        return False, f"SQL must start with: {', '.join(allowed_prefixes)}"
    
    return True, "OK"

def validate_json(data: str) -> tuple:
    """验证JSON"""
    try:
        json.loads(data)
        return True, "OK"
    except Exception as e:
        return False, f"Invalid JSON: {e}"

# ============ 健康检查 ============
class HealthCheck:
    def __init__(self):
        self.checks: Dict[str, callable] = {}
    
    def register(self, name: str, check_fn: callable):
        self.checks[name] = check_fn
    
    def run_all(self) -> Dict:
        results = {}
        for name, check_fn in self.checks.items():
            try:
                results[name] = {"status": "OK", "result": check_fn()}
            except Exception as e:
                results[name] = {"status": "FAIL", "error": str(e)}
        return results
    
    def is_healthy(self) -> bool:
        results = self.run_all()
        return all(r["status"] == "OK" for r in results.values())

# 全局健康检查
health = HealthCheck()

# 导出
__all__ = [
    'Logger', '_logger', 'MCPError', 'safe_execute',
    'PerformanceTracker', '_tracker',
    'format_table', 'format_duration', 'format_bytes', 'truncate',
    'validate_sql', 'validate_json',
    'HealthCheck', 'health'
]
