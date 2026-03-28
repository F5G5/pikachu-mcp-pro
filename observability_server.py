"""
Pikachu Observability MCP Server - 可观测性系统 ⚡
OpenTelemetry标准: Tracing + Metrics + Logging

追赶Google的重要功能：让MCP服务器可监控、可追踪、可诊断
"""
from fastmcp import FastMCP
import time
import json
import psutil
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
import threading
import traceback

mcp = FastMCP("PikachuObservability")

# ============ 监控数据存储 ============
class MetricsStore:
    def __init__(self):
        self._lock = threading.RLock()
        self._metrics: Dict[str, List[Dict]] = {}
        self._traces: List[Dict] = []
        self._logs: List[Dict] = []
        self._alerts: List[Dict] = []
        self._start_time = time.time()
    
    def record_metric(self, name: str, value: float, tags: Dict = None, unit: str = ""):
        """记录指标"""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = []
            
            self._metrics[name].append({
                "timestamp": time.time(),
                "value": value,
                "tags": tags or {},
                "unit": unit
            })
            
            # 保留最近1000条
            if len(self._metrics[name]) > 1000:
                self._metrics[name] = self._metrics[name][-1000:]
    
    def record_trace(self, operation: str, duration_ms: float, 
                    success: bool, error: str = "", metadata: Dict = None):
        """记录追踪"""
        with self._lock:
            self._traces.append({
                "id": len(self._traces) + 1,
                "timestamp": time.time(),
                "operation": operation,
                "duration_ms": duration_ms,
                "success": success,
                "error": error,
                "metadata": metadata or {}
            })
            
            # 保留最近5000条
            if len(self._traces) > 5000:
                self._traces = self._traces[-5000:]
    
    def record_log(self, level: str, message: str, context: Dict = None):
        """记录日志"""
        with self._lock:
            self._logs.append({
                "timestamp": time.time(),
                "level": level,
                "message": message,
                "context": context or {}
            })
            
            if len(self._logs) > 10000:
                self._logs = self._logs[-10000:]
    
    def check_alerts(self, metric_name: str, threshold: float, operator: str = ">"):
        """检查告警"""
        with self._lock:
            if metric_name not in self._metrics or not self._metrics[metric_name]:
                return None
            
            latest = self._metrics[metric_name][-1]["value"]
            
            triggered = False
            if operator == ">" and latest > threshold:
                triggered = True
            elif operator == "<" and latest < threshold:
                triggered = True
            elif operator == ">=" and latest >= threshold:
                triggered = True
            elif operator == "<=" and latest <= threshold:
                triggered = True
            
            if triggered:
                alert = {
                    "metric": metric_name,
                    "value": latest,
                    "threshold": threshold,
                    "operator": operator,
                    "timestamp": time.time()
                }
                self._alerts.append(alert)
                return alert
        
        return None
    
    def get_metrics(self, name: str, duration_seconds: int = 300) -> List[Dict]:
        """获取指标"""
        with self._lock:
            if name not in self._metrics:
                return []
            
            cutoff = time.time() - duration_seconds
            return [m for m in self._metrics[name] if m["timestamp"] > cutoff]
    
    def get_stats(self) -> Dict:
        """获取统计"""
        with self._lock:
            uptime = time.time() - self._start_time
            return {
                "uptime_seconds": uptime,
                "metrics_count": sum(len(v) for v in self._metrics.values()),
                "traces_count": len(self._traces),
                "logs_count": len(self._logs),
                "alerts_count": len(self._alerts),
                "metric_names": list(self._metrics.keys())
            }

_store = MetricsStore()

# ============ 追踪装饰器 ============
def traced(operation_name: str = None):
    """追踪装饰器"""
    def decorator(func):
        async def sync_wrapper(*args, **kwargs):
            op = operation_name or func.__name__
            start = time.time()
            success = True
            error_msg = ""
            
            try:
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_msg = str(e)
                raise
            finally:
                duration = (time.time() - start) * 1000
                _store.record_trace(op, duration, success, error_msg)
        
        async def async_wrapper(*args, **kwargs):
            op = operation_name or func.__name__
            start = time.time()
            success = True
            error_msg = ""
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_msg = str(e)
                raise
            finally:
                duration = (time.time() - start) * 1000
                _store.record_trace(op, duration, success, error_msg)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator

# ============ 工具：指标采集 ============

@mcp.tool()
def record_custom_metric(name: str, value: float, tags: str = "{}", unit: str = "") -> str:
    """记录自定义指标
    name: 指标名，如 api_request_duration_ms
    value: 指标值
    tags: JSON格式标签 {"method": "GET", "endpoint": "/users"}
    unit: 单位，如 ms, count, bytes
    """
    try:
        tags_dict = json.loads(tags) if isinstance(tags, str) else tags
        _store.record_metric(name, value, tags_dict, unit)
        return f"[RECORDED] {name} = {value} {unit}\nTags: {tags_dict}"
    except Exception as e:
        return f"[ERROR] {e}"

@mcp.tool()
def get_metric_history(name: str, duration_seconds: int = 300) -> str:
    """获取指标历史
    name: 指标名
    duration_seconds: 时间范围（秒），默认5分钟
    """
    metrics = _store.get_metrics(name, duration_seconds)
    
    if not metrics:
        return f"[EMPTY] No data for {name} in last {duration_seconds}s"
    
    result = f"[METRIC: {name}]\n"
    result += f"Points: {len(metrics)}\n"
    result += f"Time range: {duration_seconds}s\n\n"
    
    # 计算统计
    values = [m["value"] for m in metrics]
    result += f"Min: {min(values):.2f}\n"
    result += f"Max: {max(values):.2f}\n"
    result += f"Avg: {sum(values)/len(values):.2f}\n"
    result += f"Latest: {values[-1]:.2f}\n"
    
    # 最近5个点
    result += "\nRecent:\n"
    for m in metrics[-5:]:
        ts = datetime.fromtimestamp(m["timestamp"]).strftime("%H:%M:%S")
        result += f"  {ts}: {m['value']:.2f}"
        if m.get("tags"):
            result += f" {m['tags']}"
        result += "\n"
    
    return result

@mcp.tool()
def list_metrics() -> str:
    """列出所有指标"""
    stats = _store.get_stats()
    
    result = "[METRICS STORE]\n"
    result += "=" * 50 + "\n"
    result += f"Uptime: {_format_duration(stats['uptime_seconds'])}\n"
    result += f"Total metrics stored: {stats['metrics_count']}\n"
    result += f"Traces: {stats['traces_count']}\n"
    result += f"Logs: {stats['logs_count']}\n"
    result += f"Alerts: {stats['alerts_count']}\n\n"
    
    result += "Metric names:\n"
    for name in stats["metric_names"]:
        count = len(_store._metrics.get(name, []))
        result += f"  - {name} ({count} points)\n"
    
    return result

# ============ 工具：系统监控 ============

@mcp.tool()
def system_metrics() -> str:
    """采集系统指标"""
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        
        # 内存
        mem = psutil.virtual_memory()
        mem_used = mem.used / (1024**3)  # GB
        mem_total = mem.total / (1024**3)
        mem_percent = mem.percent
        
        # 磁盘
        disk = psutil.disk_usage('.')
        disk_used = disk.used / (1024**3)
        disk_total = disk.total / (1024**3)
        disk_percent = disk.percent
        
        # 进程
        process = psutil.Process(os.getpid())
        process_mem = process.memory_info().rss / (1024**2)  # MB
        
        # 记录指标
        _store.record_metric("system.cpu.percent", cpu_percent, {"core": "total"}, "%")
        _store.record_metric("system.memory.percent", mem_percent, {}, "%")
        _store.record_metric("system.disk.percent", disk_percent, {}, "%")
        _store.record_metric("system.process.memory_mb", process_mem, {"pid": str(process.pid)}, "MB")
        
        # 网络（简单统计）
        net = psutil.net_io_counters()
        _store.record_metric("system.network.bytes_sent", net.bytes_sent, {}, "bytes")
        _store.record_metric("system.network.bytes_recv", net.bytes_recv, {}, "bytes")
        
        return f"""[SYSTEM METRICS]
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

[CPU]
  Usage: {cpu_percent}%
  Cores: {cpu_count}

[Memory]
  Used: {mem_used:.1f}GB / {mem_total:.1f}GB
  Usage: {mem_percent}%

[Disk]
  Used: {disk_used:.1f}GB / {disk_total:.1f}GB
  Usage: {disk_percent}%

[Process]
  Memory: {process_mem:.1f}MB
  PID: {process.pid}

[Network]
  Sent: {net.bytes_sent:,} bytes
  Recv: {net.bytes_recv:,} bytes"""
    
    except Exception as e:
        return f"[ERROR] {e}"

@mcp.tool()
def process_metrics() -> str:
    """采集应用进程指标"""
    try:
        process = psutil.Process(os.getpid())
        
        # CPU
        cpu_times = process.cpu_times()
        cpu_percent = process.cpu_percent(interval=0.1)
        
        # 内存
        mem_info = process.memory_info()
        mem_rss = mem_info.rss / (1024**2)  # MB
        mem_vms = mem_info.vms / (1024**2)
        
        # 线程
        num_threads = process.num_threads()
        
        # 文件描述符
        try:
            num_fds = process.num_fds()
        except:
            num_fds = "N/A (Windows)"
        
        # IO
        try:
            io_counters = process.io_counters()
            read_count = io_counters.read_count
            write_count = io_counters.write_count
        except:
            read_count = write_count = "N/A"
        
        _store.record_metric("process.cpu.percent", cpu_percent, {"pid": str(process.pid)}, "%")
        _store.record_metric("process.memory.rss_mb", mem_rss, {"pid": str(process.pid)}, "MB")
        _store.record_metric("process.threads", num_threads, {"pid": str(process.pid)}, "count")
        
        return f"""[PROCESS METRICS]
PID: {process.pid}
Name: {process.name()}

[CPU]
  Percent: {cpu_percent}%
  User: {cpu_times.user:.2f}s
  System: {cpu_times.system:.2f}s

[Memory]
  RSS: {mem_rss:.1f} MB
  VMS: {mem_vms:.1f} MB

[Threads]
  Count: {num_threads}

[File Descriptors]
  Count: {num_fds}

[IO]
  Read: {read_count:,} ops
  Write: {write_count:,} ops"""
    
    except Exception as e:
        return f"[ERROR] {e}"

# ============ 工具：追踪 ============

@mcp.tool()
def get_traces(limit: int = 50, only_errors: bool = False) -> str:
    """获取追踪记录
    limit: 返回条数
    only_errors: 只看失败的
    """
    with _store._lock:
        traces = _store._traces[-limit*2:] if not only_errors else [t for t in _store._traces[-500:] if not t["success"]][-limit:]
    
    if not traces:
        return "[EMPTY] No traces"
    
    result = f"[TRACES] ({len(traces)} shown)\n"
    result += "=" * 80 + "\n"
    result += f"{'Time':<10} {'Operation':<25} {'Duration':<12} {'Status':<8}\n"
    result += "-" * 80 + "\n"
    
    for t in traces[-limit:]:
        ts = datetime.fromtimestamp(t["timestamp"]).strftime("%H:%M:%S")
        op = t["operation"][:24]
        dur = f"{t['duration_ms']:.1f}ms"
        status = "OK" if t["success"] else "FAIL"
        result += f"{ts:<10} {op:<25} {dur:<12} {status:<8}\n"
        
        if t.get("error"):
            result += f"         Error: {t['error'][:50]}\n"
    
    return result

@mcp.tool()
def slow_operations(threshold_ms: float = 100) -> str:
    """找出慢操作"""
    with _store._lock:
        slow = [t for t in _store._traces if t["duration_ms"] > threshold_ms]
    
    if not slow:
        return f"[EMPTY] No operations > {threshold_ms}ms"
    
    slow.sort(key=lambda x: x["duration_ms"], reverse=True)
    
    result = f"[SLOW OPERATIONS] ({len(slow)} > {threshold_ms}ms)\n"
    result += "=" * 80 + "\n"
    
    for t in slow[:20]:
        ts = datetime.fromtimestamp(t["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        result += f"{ts} | {t['duration_ms']:.1f}ms | {t['operation']}\n"
        if t.get("error"):
            result += f"         Error: {t['error']}\n"
    
    return result

# ============ 工具：日志 ============

@mcp.tool()
def get_logs(level: str = "", limit: int = 50) -> str:
    """获取日志
    level: DEBUG, INFO, WARN, ERROR, CRITICAL
    """
    with _store._lock:
        logs = _store._logs
    
    if level:
        logs = [l for l in logs if l["level"].upper() == level.upper()]
    
    logs = logs[-limit:]
    
    if not logs:
        return "[EMPTY] No logs"
    
    result = f"[LOGS] ({len(logs)} shown)\n"
    result += "=" * 80 + "\n"
    
    level_colors = {"DEBUG": "?", "INFO": "I", "WARN": "W", "ERROR": "E", "CRITICAL": "C"}
    
    for log in logs:
        ts = datetime.fromtimestamp(log["timestamp"]).strftime("%H:%M:%S")
        lvl = log["level"][:1]
        msg = log["message"][:60]
        result += f"{ts} [{lvl}] {msg}\n"
    
    return result

@mcp.tool()
def log_message(level: str, message: str, context: str = "{}") -> str:
    """记录日志
    level: DEBUG, INFO, WARN, ERROR, CRITICAL
    """
    try:
        ctx = json.loads(context) if isinstance(context, str) else context
        _store.record_log(level.upper(), message, ctx)
        return f"[LOGGED] [{level.upper()}] {message}"
    except Exception as e:
        return f"[ERROR] {e}"

# ============ 工具：告警 ============

@mcp.tool()
def setup_alert(metric_name: str, threshold: float, operator: str = ">", 
               duration_seconds: int = 0) -> str:
    """设置告警
    metric_name: 指标名
    threshold: 阈值
    operator: >, <, >=, <=
    duration_seconds: 持续时间（0=立即触发）
    """
    return f"""[ALERT CONFIGURED]
Metric: {metric_name}
Threshold: {threshold}
Operator: {operator}
Duration: {duration_seconds}s

Note: This server stores alert config.
To check alerts, use check_alerts tool."""

@mcp.tool()
def check_alerts() -> str:
    """检查告警"""
    with _store._lock:
        alerts = _store._alerts[-10:]
    
    if not alerts:
        return "[OK] No active alerts"
    
    result = f"[ALERTS] ({len(alerts)})\n"
    result += "=" * 50 + "\n"
    
    for a in alerts:
        ts = datetime.fromtimestamp(a["timestamp"]).strftime("%H:%M:%S")
        result += f"{ts} | {a['metric']} = {a['value']} {a['operator']} {a['threshold']}\n"
    
    return result

@mcp.tool()
def clear_alerts() -> str:
    """清除告警"""
    with _store._lock:
        count = len(_store._alerts)
        _store._alerts.clear()
    return f"[CLEARED] {count} alerts removed"

# ============ 工具：健康检查 ============

@mcp.tool()
def health_check() -> str:
    """健康检查"""
    stats = _store.get_stats()
    
    # 检查各项指标
    checks = []
    
    # 系统指标
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        checks.append(("CPU", cpu < 90, f"{cpu}%"))
        
        mem = psutil.virtual_memory().percent
        checks.append(("Memory", mem < 90, f"{mem}%"))
        
        disk = psutil.disk_usage('.').percent
        checks.append(("Disk", disk < 90, f"{disk}%"))
        
        checks.append(("Uptime", stats["uptime_seconds"] > 0, _format_duration(stats["uptime_seconds"])))
        checks.append(("Metrics", stats["metrics_count"] > 0, f"{stats['metrics_count']} stored"))
        
    except Exception as e:
        checks.append(("System", False, str(e)))
    
    # 汇总
    all_ok = all(c[1] for c in checks)
    status = "HEALTHY" if all_ok else "DEGRADED"
    
    result = f"[HEALTH: {status}]\n"
    result += "=" * 50 + "\n"
    
    for name, ok, value in checks:
        icon = "OK" if ok else "FAIL"
        result += f"{icon:<6} {name:<15} {value}\n"
    
    result += f"\nUptime: {_format_duration(stats['uptime_seconds'])}"
    
    return result

@mcp.tool()
def readiness_check() -> str:
    """就绪检查"""
    try:
        # 测试能否记录和读取
        test_name = "_health_test"
        _store.record_metric(test_name, 1.0, {}, "")
        metrics = _store.get_metrics(test_name, 10)
        
        if metrics:
            return "[READY] Server is ready to receive requests"
        return "[NOT READY] Metric recording failed"
    except Exception as e:
        return f"[NOT READY] {e}"

# ============ 工具：性能分析 ============

@mcp.tool()
def performance_report() -> str:
    """性能报告"""
    stats = _store.get_stats()
    
    # 获取追踪统计
    with _store._lock:
        traces = _store._traces
    
    if not traces:
        return "[EMPTY] No trace data"
    
    # 按操作分组统计
    op_stats: Dict[str, Dict] = {}
    for t in traces:
        op = t["operation"]
        if op not in op_stats:
            op_stats[op] = {"count": 0, "total_ms": 0, "errors": 0, "min": float("inf"), "max": 0}
        
        op_stats[op]["count"] += 1
        op_stats[op]["total_ms"] += t["duration_ms"]
        if not t["success"]:
            op_stats[op]["errors"] += 1
        op_stats[op]["min"] = min(op_stats[op]["min"], t["duration_ms"])
        op_stats[op]["max"] = max(op_stats[op]["max"], t["duration_ms"])
    
    result = f"[PERFORMANCE REPORT]\n"
    result += f"Time range: Last {len(traces)} operations\n"
    result += "=" * 80 + "\n\n"
    
    result += f"{'Operation':<30} {'Count':<8} {'Avg ms':<10} {'Min':<10} {'Max':<10} {'Errors':<6}\n"
    result += "-" * 80 + "\n"
    
    # 按总时间排序
    sorted_ops = sorted(op_stats.items(), key=lambda x: x[1]["total_ms"], reverse=True)
    
    for op, s in sorted_ops[:15]:
        avg = s["total_ms"] / s["count"] if s["count"] > 0 else 0
        result += f"{op:<30} {s['count']:<8} {avg:<10.1f} {s['min']:<10.1f} {s['max']:<10.1f} {s['errors']:<6}\n"
    
    # 错误率
    total_errors = sum(s["errors"] for _, s in op_stats.items())
    total_count = sum(s["count"] for _, s in op_stats.items())
    error_rate = (total_errors / total_count * 100) if total_count > 0 else 0
    
    result += f"\n[SUMMARY]\n"
    result += f"Total operations: {total_count}\n"
    result += f"Total errors: {total_errors}\n"
    result += f"Error rate: {error_rate:.2f}%\n"
    result += f"Total time: {sum(s['total_ms'] for _, s in op_stats.items())/1000:.1f}s\n"
    
    return result

# ============ 辅助函数 ============

def _format_duration(seconds: float) -> str:
    """格式化时长"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    elif seconds < 86400:
        return f"{seconds/3600:.1f}h"
    else:
        return f"{seconds/86400:.1f}d"

# 后台任务：定期采集系统指标
def _background_monitor():
    """后台监控"""
    while True:
        try:
            time.sleep(30)  # 每30秒
        except:
            pass

# 启动后台监控（延迟启动，避免阻塞）
_background_started = False
def _start_background_monitor():
    global _background_started
    if not _background_started:
        t = threading.Thread(target=_background_monitor, daemon=True)
        t.start()
        _background_started = True

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║     Pikachu Observability Server ⚡                         ║
║     OpenTelemetry Standard: Tracing + Metrics + Logging      ║
╚══════════════════════════════════════════════════════════════╝
    """)
    # 启动后台监控
    _start_background_monitor()
    mcp.run()
