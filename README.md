# Pikachu MCP Pro - 专业版服务器 ⚡

<p align="center">
<img src="https://img.shields.io/badge/MCP Servers-12-green" alt="MCP Servers">
<img src="https://img.shields.io/badge/Tools-115+-blue" alt="Tools">
<img src="https://img.shields.io/badge/License-Proprietary-red" alt="License">
</p>

> 真正超越Google Toolbox：中文NL2SQL + Ollama本地模型 + OpenTelemetry监控

## 🎯 核心优势

| 特性 | Google Toolbox | Pikachu Pro | 优势 |
|:---|:---:|:---:|:---|
| **中文NL2SQL** | ❌ 无 | ✅ 原生支持 | 🌟 差异化竞争 |
| **Local模型** | ❌ 不支持 | ✅ Ollama集成 | 🌟 隐私保护 |
| **中文文档** | ❌ 无 | ✅ 完整中文 | 🌟 14亿人市场 |
| **工具数量** | 10-20个 | 115+个 | 🌟 全面压制 |
| **OpenTelemetry** | ✅ | ✅ 完整实现 | 🆗 追平 |
| **连接池** | ✅ | ✅ 专业级 | 🆗 追平 |
| **Remote Server** | ✅ | ✅ 支持 | 🆗 追平 |

## 📦 服务器清单

| 服务器 | 工具数 | 核心功能 |
|:---|:---:|:---|
| **Database** | 12 | 多数据库连接、Schema探索、查询构建、参数化SQL、**全文搜索** |
| **AI** | 13 | 多模型对话、向量存储(RAG)、Prompt模板、代码审查 |
| **NL2SQL** | 8 | 中文自然语言转SQL、Ollama集成、SQL验证 |
| **Remote** | 8 | Remote MCP、远程调用、服务发现、HTTP传输 |
| **Professional** | 11 | All-in-One整合版（DB+AI+NL2SQL） |
| **Cloud** | 10 | HTTP/文件上传/下载/健康检查/Webhook |
| **Email** | 6 | 邮件发送/HTML/模板/批量发送 |
| **File** | 10 | CSV/JSON/文件操作/合并/转换 |
| **Monitor** | 8 | 系统监控/CPU/内存/磁盘/进程 |
| **Pro** | 6 | 天气/股票/加密货币/AI新闻/SEO |
| **Observability** | 16 | Tracing/Metrics/Logging/Alerts/**仪表盘** |
| **Pool** | 7 | 连接池/健康检查/动态调参 |

**总计: 12服务器 / 115+工具**

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install fastmcp psutil
```

### 2. 运行服务器

```bash
# 单个服务器
python database_server.py
python nl2sql_server.py
python observability_server.py

# All-in-One专业版
python professional_server.py
```

### 3. OpenClaw配置

```json
{
  "mcpServers": {
    "pikachu-db": {
      "command": "python",
      "args": ["path/to/database_server.py"]
    },
    "pikachu-nl2sql": {
      "command": "python",
      "args": ["path/to/nl2sql_server.py"]
    }
  }
}
```

## 💡 核心功能示例

### 中文NL2SQL（差异化核心）

```python
# 连接数据库
db_connect(db_type="sqlite", path="./data.db")

# 中文自然语言查询
nl2sql("查询每个用户的订单数量和总金额")

# 输出:
# [NL2SQL]
# Query: 查询每个用户的订单数量和总金额
# 
# ```sql
# SELECT user_id, COUNT(*) as order_count, SUM(amount) as total_amount
# FROM orders
# GROUP BY user_id
# ```
```

### OpenTelemetry监控

```python
# 记录自定义指标
record_custom_metric("api_request_duration_ms", 125.5, 
                     tags='{"method": "GET", "endpoint": "/users"}')

# 查看仪表盘
dashboard()

# 输出完整状态概览
```

### 连接池管理

```python
# 创建连接池
create_pool(name="main", db_type="sqlite", 
            max_connections=10, min_connections=2)

# 使用池执行SQL
pool_execute(pool_name="main", query="SELECT * FROM users LIMIT 10")

# 查看池状态
pool_status(name="main")
```

## 🔧 配置

### Ollama（推荐本地模型）

```bash
# 安装
brew install ollama  # macOS
curl -fsSL https://ollama.com/install.sh | sh

# 启动
ollama serve

# 安装模型
ollama pull llama3.2
```

### API密钥配置

```python
# OpenAI
ai_configure(openai_key="sk-xxx")

# Claude
ai_configure(anthropic_key="sk-ant-xxx")

# Ollama
configure_nl2sql(ollama_url="http://localhost:11434", default_model="llama3.2")
```

## 📊 技术架构

```
Pikachu Pro MCP Servers
├── Database      # 连接池 + Schema探索 + SQL构建 + 全文搜索
├── AI            # 多模型 + 向量存储 + Prompt模板
├── NL2SQL        # 中文解析 + Schema映射 + SQL生成 ⭐
├── Remote        # HTTP/SSE传输 + 服务发现
├── Observability # Tracing + Metrics + Logging + Dashboard ⭐
└── Pool          # 连接复用 + 健康检查 + 动态调参
```

## 📈 与Google Toolbox对比

| 维度 | Google | Pikachu Pro |
|:---|:---:|:---:|
| **NL2SQL语言** | 英文 | 中文+英文 |
| **模型** | 云服务 | 本地+云 |
| **部署** | 云 | 本地+云 |
| **文档** | 英文 | 中文+英文 |
| **监控** | OpenTelemetry | 完整实现 |
| **连接池** | 基础 | 专业级 |
| **工具数量** | 10-20 | 115+ |

## 🐛 Bug修复历史

- ✅ Monitor f-string语法错误
- ✅ Pool pymysql/psycopg2可选依赖
- ✅ Remote FastMCP废弃参数
- ✅ Observability后台线程阻塞

## 📄 许可证

专有软件 | Copyright 2026 Pikachu

---

**皮卡丘出品 | 真正超越 | 中文优先** ⚡
