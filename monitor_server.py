"""
Pikachu Monitor MCP Server ⚡
系统监控、日志分析、告警
"""
from fastmcp import FastMCP
import urllib.request
import json
import psutil
import os
from datetime import datetime

mcp = FastMCP("PikachuMonitor")

@mcp.tool()
def system_info() -> str:
    """获取系统信息"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        
        return f"""[SYSTEM INFO]
{'='*50}

CPU:
  Usage: {cpu_percent}%
  Cores: {cpu_count}
  Per-core: {psutil.cpu_percent(interval=1, percpu=True)}

Memory:
  Total: {memory.total / (1024**3):.1f} GB
  Used: {memory.used / (1024**3):.1f} GB ({memory.percent}%)
  Available: {memory.available / (1024**3):.1f} GB

Disk:
  Total: {disk.total / (1024**3):.1f} GB
  Used: {disk.used / (1024**3):.1f} GB ({disk.percent}%)
  Free: {disk.free / (1024**3):.1f} GB

System:
  Boot time: {boot_time.strftime('%Y-%m-%d %H:%M:%S')}
  Uptime: {uptime.days}d {uptime.seconds//3600}h
  OS: {os.name}"""
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def cpu_info() -> str:
    """CPU详细信息"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
        cpu_freq = psutil.cpu_freq()
        
        result = f"""[CPU INFO]
{'='*50}

Overall Usage: {sum(cpu_percent)/len(cpu_percent):.1f}%

Per-Core Usage:"""
        for i, pct in enumerate(cpu_percent):
            bar = "█" * int(pct/5) + "░" * (20 - int(pct/5))
            result += f"\n  Core {i}: [{bar}] {pct:.1f}%"
        
        if cpu_freq:
            result += f"\n\nFrequency: {cpu_freq.current:.0f} MHz"
            result += f"\nMin/Max: {cpu_freq.min:.0f}/{cpu_freq.max:.0f} MHz"
        
        return result
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def memory_info() -> str:
    """内存详细信息"""
    try:
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        def format_bytes(b):
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if b < 1024:
                    return f"{b:.1f}{unit}"
                b /= 1024
            return f"{b:.1f}PB"
        
        result = f"""[MEMORY INFO]
{'='*50}

Physical Memory:
  Total: {format_bytes(vm.total)}
  Available: {format_bytes(vm.available)}
  Used: {format_bytes(vm.used)} ({vm.percent}%)
  
  Details:
  - Active: {format_bytes(vm.active)}
  - Inactive: {format_bytes(vm.inactive)}
  - Buffers: {format_bytes(getattr(vm, 'buffers', 0))}
  - Cached: {format_bytes(getattr(vm, 'cached', 0))}

Swap Memory:
  Total: {format_bytes(swap.total)}
  Used: {format_bytes(swap.used)} ({swap.percent}%)
  Free: {format_bytes(swap.free)}
  Sin/Sout: {format_bytes(swap.sin)}/{format_bytes(swap.sout)}"""
        
        return result
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def disk_info() -> str:
    """磁盘使用信息"""
    try:
        partitions = psutil.disk_partitions()
        
        result = f"""[DISK INFO]
{'='*50}"""
        
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                
                def format_bytes(b):
                    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                        if b < 1024:
                            return f"{b:.1f}{unit}"
                        b /= 1024
                    return f"{b:.1f}PB"
                
                result += f"\n\n{partition.device}"
                result += f"\n  Mount: {partition.mountpoint}"
                result += f"\n  Type: {partition.fstype}"
                result += f"\n  Total: {format_bytes(usage.total)}"
                result += f"\n  Used: {format_bytes(usage.used)} ({usage.percent}%)"
                result += f"\n  Free: {format_bytes(usage.free)}"
                
                # 进度条
                bar_len = 20
                filled = int(usage.percent / 5)
                bar = "█" * filled + "░" * (bar_len - filled)
                result += f"\n  Usage: [{bar}]"
                
            except PermissionError:
                continue
        
        return result
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def network_info() -> str:
    """网络连接信息"""
    try:
        net_io = psutil.net_io_counters()
        connections = len(psutil.net_connections())
        
        def format_bytes(b):
            for unit in ['', 'K', 'M', 'G', 'T']:
                if abs(b) < 1024:
                    return f"{b:.1f}{unit}B"
                b /= 1024
            return f"{b:.1f}PB"
        
        result = f"""[NETWORK INFO]
{'='*50}

Total Traffic:
  Sent: {format_bytes(net_io.bytes_sent)}
  Received: {format_bytes(net_io.bytes_recv)}
  Packets: {net_io.packets_sent:,}/{net_io.packets_recv:,}
  Errors: {net_io.errin}/{net_io.errout}
  Dropped: {net_io.dropin}/{net_io.dropout}

Connections:
  Total: {connections}
  TCP: {len([c for c in psutil.net_connections() if c.type == 1])}
  UDP: {len([c for c in psutil.net_connections() if c.type == 2])}"""
        
        return result
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def process_list(top: int = 10) -> str:
    """进程列表（按CPU/内存排序）"""
    try:
        processes = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
            try:
                info = p.info
                info['obj'] = p
                processes.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # 按CPU排序
        by_cpu = sorted(processes, key=lambda x: x.get('cpu_percent', 0), reverse=True)[:top]
        
        result = f"""[TOP {top} PROCESSES BY CPU]
{'='*50}
PID       Name                     CPU%    Mem%    Status
{'-'*60}"""
        
        for p in by_cpu:
            result += f"\n{p['pid']:<8} {p['name'][:24]:<24} {p.get('cpu_percent', 0):>5.1f}  {p.get('memory_percent', 0):>5.1f}  {p.get('status', '?')}"
        
        # 按内存排序
        by_mem = sorted(processes, key=lambda x: x.get('memory_percent', 0), reverse=True)[:top]
        
        result += f"\n\n[TOP {top} PROCESSES BY MEMORY]\n{'='*50}\nPID       Name                     CPU%    Mem%    Status\n{'-'*60}"
        
        for p in by_mem:
            result += f"\n{p['pid']:<8} {p['name'][:24]:<24} {p.get('cpu_percent', 0):>5.1f}  {p.get('memory_percent', 0):>5.1f}  {p.get('status', '?')}"
        
        return result
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def battery_info() -> str:
    """电池信息（如果有）"""
    try:
        battery = psutil.sensors_battery()
        
        if battery is None:
            return "[INFO] No battery detected (desktop PC)"
        
        percent = battery.percent
        plugged = battery.power_plugged
        time_left = battery.secsleft
        
        result = f"""[BATTERY INFO]
{'='*50}
Status: {'Plugged In' if plugged else 'On Battery'}
Charge: {percent}%"""
        
        if time_left != psutil.POWER_TIME_UNLIMITED:
            hours = time_left // 3600
            mins = (time_left % 3600) // 60
            result += f"\nTime left: {hours}h {mins}m"
        else:
            result += "\nTime left: Unlimited"
        
        # 进度条
        bar = "█" * int(percent/5) + "░" * (20 - int(percent/5))
        result += f"\n[{bar}]"
        
        return result
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def service_status(service_name: str) -> str:
    """检查服务状态"""
    try:
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'create_time']):
            try:
                if service_name.lower() in p.info['name'].lower():
                    info = p.info
                    uptime = datetime.now() - datetime.fromtimestamp(info['create_time'])
                    
                    return f"""[SERVICE FOUND]
Name: {info['name']}
PID: {info['pid']}
CPU: {info['cpu_percent']:.1f}%
Memory: {info['memory_percent']:.1f}%
Uptime: {uptime.days}d {uptime.seconds//3600}h
Status: Running"""
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return f"[NOT FOUND] No process matching '{service_name}'"
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

if __name__ == "__main__":
    mcp.run()
