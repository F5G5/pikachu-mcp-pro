"""
Pikachu Connection Pool Server - 专业级连接池 ⚡
追赶Google Toolbox：完整的连接池管理、连接复用、健康检查

这才是企业级的数据库访问！
"""
from fastmcp import FastMCP
import sqlite3
import threading
import queue
import time
import json
from datetime import datetime
from contextlib import contextmanager
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

# 可选依赖
try:
    import pymysql
    HAS_PYMYSQL = True
except ImportError:
    pymysql = None
    HAS_PYMYSQL = False

try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    psycopg2 = None
    HAS_PSYCOPG2 = False

mcp = FastMCP("PikachuPool")

# ============ 连接池实现 ============
@dataclass
class PoolConfig:
    """连接池配置"""
    max_connections: int = 10
    min_connections: int = 2
    max_idle_seconds: int = 300
    checkout_timeout_seconds: float = 30.0
    health_check_interval_seconds: int = 60

@dataclass  
class Connection:
    """连接包装"""
    id: str
    conn: Any
    db_type: str
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    in_use: bool = False
    checkouts: int = 0
    errors: int = 0

class ConnectionPool:
    """专业级连接池"""
    
    def __init__(self, name: str, db_type: str, config: PoolConfig, **kwargs):
        self.name = name
        self.db_type = db_type
        self.config = config
        self.kwargs = kwargs
        
        self._lock = threading.RLock()
        self._available: queue.Queue = queue.Queue()
        self._connections: Dict[str, Connection] = {}
        self._stats = {
            "checkouts": 0,
            "checkins": 0,
            "timeouts": 0,
            "errors": 0,
            "created": 0,
            "destroyed": 0
        }
        
        # 初始化连接
        self._init_connections()
    
    def _init_connections(self):
        """初始化最小连接数"""
        with self._lock:
            for i in range(self.config.min_connections):
                conn = self._create_connection()
                if conn:
                    conn_id = f"{self.name}-{i}"
                    self._connections[conn_id] = conn
                    self._available.put(conn_id)
                    self._stats["created"] += 1
    
    def _create_connection(self) -> Optional[Connection]:
        """创建新连接"""
        try:
            if self.db_type == "sqlite":
                path = self.kwargs.get("path", ":memory:")
                conn = sqlite3.connect(path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
            elif self.db_type == "mysql":
                if not HAS_PYMYSQL:
                    return None
                conn = pymysql.connect(
                    host=self.kwargs.get("host", "localhost"),
                    port=self.kwargs.get("port", 3306),
                    user=self.kwargs.get("user", "root"),
                    password=self.kwargs.get("password", ""),
                    database=self.kwargs.get("database", ""),
                    charset=self.kwargs.get("charset", "utf8mb4")
                )
            elif self.db_type == "postgresql":
                if not HAS_PSYCOPG2:
                    return None
                conn = psycopg2.connect(
                    host=self.kwargs.get("host", "localhost"),
                    port=self.kwargs.get("port", 5432),
                    user=self.kwargs.get("user", "postgres"),
                    password=self.kwargs.get("password", ""),
                    database=self.kwargs.get("database", ""),
                    connect_timeout=10
                )
            else:
                return None
            
            return Connection(
                id=f"conn-{time.time()}-{id(conn)}",
                conn=conn,
                db_type=self.db_type
            )
        except Exception as e:
            return None
    
    def acquire(self, timeout: float = None) -> Optional[Connection]:
        """获取连接"""
        timeout = timeout or self.config.checkout_timeout_seconds
        
        try:
            conn_id = self._available.get(timeout=timeout)
        except queue.Empty:
            with self._lock:
                self._stats["timeouts"] += 1
            
            # 尝试创建新连接
            if len(self._connections) < self.config.max_connections:
                new_conn = self._create_connection()
                if new_conn:
                    with self._lock:
                        self._connections[new_conn.id] = new_conn
                        self._stats["created"] += 1
                    return new_conn
            
            return None
        
        with self._lock:
            conn = self._connections.get(conn_id)
            if conn:
                conn.in_use = True
                conn.last_used = time.time()
                conn.checkouts += 1
                self._stats["checkouts"] += 1
        
        # 验证连接
        if not self._is_healthy(conn):
            self._remove_connection(conn)
            return self.acquire(timeout)
        
        return conn
    
    def release(self, conn: Connection):
        """归还连接"""
        if not conn:
            return
        
        with self._lock:
            conn.in_use = False
            self._stats["checkins"] += 1
        
        # 检查是否超过最大空闲时间
        idle_time = time.time() - conn.last_used
        if idle_time > self.config.max_idle_seconds:
            self._remove_connection(conn)
            return
        
        # 放回池中
        self._available.put(conn.id)
    
    def _is_healthy(self, conn: Connection) -> bool:
        """检查连接健康"""
        try:
            if conn.db_type == "sqlite":
                conn.conn.execute("SELECT 1")
            elif conn.db_type == "mysql":
                conn.conn.ping(reconnect=True)
            elif conn.db_type == "postgresql":
                conn.conn.cursor().execute("SELECT 1")
            return True
        except:
            return False
    
    def _remove_connection(self, conn: Connection):
        """移除连接"""
        with self._lock:
            try:
                conn.conn.close()
            except:
                pass
            if conn.id in self._connections:
                del self._connections[conn.id]
            self._stats["destroyed"] += 1
    
    def close(self):
        """关闭池"""
        with self._lock:
            for conn in list(self._connections.values()):
                try:
                    conn.conn.close()
                except:
                    pass
            self._connections.clear()
    
    def get_stats(self) -> Dict:
        """获取统计"""
        with self._lock:
            return {
                **self._stats,
                "total_connections": len(self._connections),
                "available": self._available.qsize(),
                "in_use": len(self._connections) - self._available.qsize()
            }

# ============ 全局池存储 ============
_pools: Dict[str, ConnectionPool] = {}
_pool_lock = threading.RLock()

def get_pool(name: str) -> Optional[ConnectionPool]:
    with _pool_lock:
        return _pools.get(name)

# ============ 工具 ============

@mcp.tool()
def create_pool(name: str, db_type: str, max_connections: int = 10,
               min_connections: int = 2, path: str = ":memory:",
               host: str = "localhost", port: int = 3306,
               user: str = "root", password: str = "",
               database: str = "") -> str:
    """创建连接池
    name: 池名称
    db_type: sqlite, mysql, postgresql
    max_connections: 最大连接数
    min_connections: 最小连接数
    """
    if name in _pools:
        return f"[ERROR] Pool '{name}' already exists"
    
    config = PoolConfig(
        max_connections=max_connections,
        min_connections=min_connections
    )
    
    kwargs = {"path": path, "host": host, "port": port, 
              "user": user, "password": password, "database": database}
    
    pool = ConnectionPool(name, db_type, config, **kwargs)
    
    with _pool_lock:
        _pools[name] = pool
    
    stats = pool.get_stats()
    return f"""[POOL CREATED]
Name: {name}
Type: {db_type}
Config:
  Max connections: {max_connections}
  Min connections: {min_connections}
  Checkout timeout: {config.checkout_timeout_seconds}s

Status:
  Total: {stats['total_connections']}
  Available: {stats['available']}
  In use: {stats['in_use']}"""

@mcp.tool()
def list_pools() -> str:
    """列出所有连接池"""
    with _pool_lock:
        if not _pools:
            return "[EMPTY] No connection pools"
        
        result = f"[POOLS] ({len(_pools)})\n"
        result += "=" * 70 + "\n"
        
        for name, pool in _pools.items():
            stats = pool.get_stats()
            result += f"\n{name}:\n"
            result += f"  Type: {pool.db_type}\n"
            result += f"  Total: {stats['total_connections']}\n"
            result += f"  Available: {stats['available']}\n"
            result += f"  In use: {stats['in_use']}\n"
            result += f"  Checkouts: {stats['checkouts']}\n"
            result += f"  Timeouts: {stats['timeouts']}\n"
        
        return result

@mcp.tool()
def pool_status(name: str) -> str:
    """连接池状态"""
    pool = get_pool(name)
    if not pool:
        return f"[ERROR] Pool '{name}' not found"
    
    stats = pool.get_stats()
    
    return f"""[POOL: {name}]
Type: {pool.db_type}

[Connections]
  Total: {stats['total_connections']}
  Available: {stats['available']}
  In use: {stats['in_use']}

[Stats]
  Checkouts: {stats['checkouts']}
  Checkins: {stats['checkins']}
  Timeouts: {stats['timeouts']}
  Errors: {stats['errors']}
  Created: {stats['created']}
  Destroyed: {stats['destroyed']}

[Config]
  Max: {pool.config.max_connections}
  Min: {pool.config.min_connections}
  Max idle: {pool.config.max_idle_seconds}s
  Checkout timeout: {pool.config.checkout_timeout_seconds}s"""

@mcp.tool()
def pool_execute(pool_name: str, query: str, params: str = "{}") -> str:
    """使用连接池执行SQL
    pool_name: 连接池名称
    query: SQL语句
    params: JSON格式参数
    """
    pool = get_pool(pool_name)
    if not pool:
        return f"[ERROR] Pool '{pool_name}' not found"
    
    conn = pool.acquire()
    if not conn:
        return "[ERROR] Failed to acquire connection (timeout or pool exhausted)"
    
    try:
        params_dict = json.loads(params) if isinstance(params, str) else params
        param_tuple = tuple(params_dict.values()) if params_dict else ()
        
        cursor = conn.conn.cursor()
        cursor.execute(query, param_tuple)
        
        if query.strip().upper().startswith("SELECT"):
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            if not rows:
                return f"[EMPTY] Query returned no rows\n\nSQL: {query}"
            
            result = f"[RESULTS] ({len(rows)} rows)\n"
            result += f"Pool: {pool_name}\n\n"
            result += " | ".join(f"{c:<20}" for c in columns[:8]) + "\n"
            result += "-" * 60 * 2 + "\n"
            
            for row in rows[:50]:
                result += " | ".join(f"{str(row[i]):<20}" for i in range(min(len(columns), 8))) + "\n"
            
            if len(rows) > 50:
                result += f"\n... and {len(rows) - 50} more rows"
            
            return result
        else:
            conn.conn.commit()
            return f"[OK] {cursor.rowcount} rows affected\n\nSQL: {query}"
    
    except Exception as e:
        conn.errors += 1
        return f"[ERROR] {str(e)}\n\nSQL: {query}"
    
    finally:
        pool.release(conn)

@mcp.tool()
def destroy_pool(name: str) -> str:
    """销毁连接池"""
    pool = get_pool(name)
    if not pool:
        return f"[ERROR] Pool '{name}' not found"
    
    pool.close()
    
    with _pool_lock:
        del _pools[name]
    
    return f"[DESTROYED] Pool '{name}' closed"

@mcp.tool()
def pool_health(name: str) -> str:
    """连接池健康检查"""
    pool = get_pool(name)
    if not pool:
        return f"[ERROR] Pool '{name}' not found"
    
    # 获取一个连接测试
    conn = pool.acquire(timeout=5)
    if not conn:
        return f"[UNHEALTHY] Cannot acquire connection from pool '{name}'"
    
    healthy = pool._is_healthy(conn)
    pool.release(conn)
    
    stats = pool.get_stats()
    
    utilization = (stats['in_use'] / stats['total_connections'] * 100) if stats['total_connections'] > 0 else 0
    
    status = "HEALTHY" if healthy and utilization < 90 else "DEGRADED"
    
    return f"""[POOL HEALTH: {status}]
Name: {name}
Connection: {"OK" if healthy else "FAILED"}
Utilization: {utilization:.1f}% ({stats['in_use']}/{stats['total_connections']})
Timeouts: {stats['timeouts']}
Errors: {stats['errors']}"""

@mcp.tool()
def pool_tune(name: str, max_connections: int = None,
            min_connections: int = None,
            max_idle_seconds: int = None) -> str:
    """调整连接池参数"""
    pool = get_pool(name)
    if not pool:
        return f"[ERROR] Pool '{name}' not found"
    
    changes = []
    
    if max_connections is not None:
        pool.config.max_connections = max_connections
        changes.append(f"max_connections: {max_connections}")
    
    if min_connections is not None:
        pool.config.min_connections = min_connections
        changes.append(f"min_connections: {min_connections}")
    
    if max_idle_seconds is not None:
        pool.config.max_idle_seconds = max_idle_seconds
        changes.append(f"max_idle_seconds: {max_idle_seconds}")
    
    if not changes:
        return "[NO CHANGES] No parameters specified"
    
    return f"""[POOL TUNED]
Name: {name}
Changes:
""" + "\n".join(f"  - {c}" for c in changes)

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║     Pikachu Connection Pool Server ⚡                       ║
║     Enterprise-grade connection pooling                      ║
╚══════════════════════════════════════════════════════════════╝
    """)
    mcp.run()
