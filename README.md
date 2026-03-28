# Pikachu MCP Pro - 专业版服务器 ⚡

<p align="center">
<img src="https://img.shields.io/badge/MCP Servers-8+-green" alt="MCP Servers">
<img src="https://img.shields.io/badge/Tools-80+-blue" alt="Tools">
<img src="https://img.shields.io/badge/License-Proprietary-red" alt="License">
</p>

## 核心优势：真正超越Google Toolbox

| 特性 | Google Toolbox | Pikachu Pro | 优势 |
|:---|:---:|:---:|:---|
| **中文NL2SQL** | ❌ 无 | ✅ 原生支持 | 🌟 差异化竞争 |
| **Local模型** | ❌ 不支持 | ✅ Ollama集成 | 🌟 隐私保护 |
| **中文文档** | ❌ 无 | ✅ 完整中文 | 🌟 14亿人市场 |
| **工具数量** | 10-20个 | 80+个 | 🌟 全面压制 |
| **开箱即用** | 需配置 | ✅ 自带数据 | 🌟 零门槛 |
| **Remote Server** | ✅ 有 | ✅ 支持 | 追平 |
| **多数据库** | ✅ 有 | ✅ SQLite/MySQL/PG | 追平 |

## 为什么选择Pikachu Pro？

### 1. 中文NL2SQL - 真正超越的核心

Google Toolbox不做中文NL2SQL，这是我们的战略高地：

```python
# 使用中文自然语言查询数据库
nl2sql("查询每个用户的订单数量和总金额")
# -> 自动生成: SELECT user_id, COUNT(*), SUM(amount) FROM orders GROUP BY user_id

nl2sql("找出销售额最高的前10个产品类别")
# -> 自动生成: SELECT category, SUM(sales) as total FROM products GROUP BY category ORDER BY total DESC LIMIT 10
```

### 2. Local模型支持 - 隐私优先

```python
# 不需要API Key，使用本地Ollama
configure_nl2sql(ollama_url="http://localhost:11434", default_model="llama3.2")

# 完全离线可用
ai_chat(model="ollama", message="解释这段代码")
```

### 3. 专业级功能

| 服务器 | 工具数 | 核心功能 |
|:---|:---:|:---|
| **database_server** | 10 | 多数据库连接、Schema探索、查询构建、参数化SQL |
| **ai_server** | 13 | 多模型对话、向量存储( RAG)、Prompt模板、代码审查 |
| **nl2sql_server** | 8 | 中文NL2SQL、Ollama集成、SQL验证、执行预览 |
| **remote_server** | 9 | Remote MCP、远程调用、服务发现、HTTP传输 |
| **professional_server** | 10 | All-in-One整合版 |
| **cloud_server** | 8 | 云存储(S3/OSS)、文件管理 |
| **email_server** | 8 | 邮件发送/读取、SMTP配置 |
| **file_server** | 9 | 文件操作、批量处理、压缩解压 |
| **monitor_server** | 8 | 系统监控、性能指标 |

## 快速开始

### 方式一：单个服务器

```bash
# 安装依赖
pip install fastmcp

# 运行数据库服务器
python database_server.py

# 运行NL2SQL服务器（需要Ollama）
python nl2sql_server.py

# 运行专业版（整合所有功能）
python professional_server.py
```

### 方式二：OpenClaw配置

```json
{
  "mcpServers": {
    "pikachu-db": {
      "command": "python",
      "args": ["C:/path/to/database_server.py"]
    },
    "pikachu-nl2sql": {
      "command": "python", 
      "args": ["C:/path/to/nl2sql_server.py"]
    },
    "pikachu-pro": {
      "command": "python",
      "args": ["C:/path/to/professional_server.py"]
    }
  }
}
```

## 核心工具详解

### NL2SQL（中文自然语言转SQL）

```python
# 1. 连接数据库
db_connect(db_type="sqlite", path="./mydata.db")

# 2. 查看Schema
db_schema()

# 3. 中文查询（只生成SQL）
nl2sql("查询所有用户")

# 4. 中文查询（直接执行）
nl2sql_run("找出订单金额大于1000的用户")
```

### AI对话

```python
# 配置API
ai_configure(openai_key="sk-xxx")

# 对话
ai_chat(model="gpt-4", message="解释什么是MCP协议")

# 代码审查
ai_code_review(code="def foo():\n    pass", language="python")
```

### 向量存储（RAG）

```python
# 存储文档
vector_store(collection="docs", text="MCP协议文档内容", metadata='{"source": "official"}')

# 语义搜索
vector_search(collection="docs", query="MCP协议是什么", top_k=5)

# 列出集合
vector_list_collections()
```

### Remote Server（远程部署）

```bash
# 启动远程服务器
python remote_server.py --port 8080

# 客户端配置
{
  "mcpServers": {
    "remote-pikachu": {
      "url": "http://your-server:8080/mcp"
    }
  }
}
```

## 服务端AI配置

### Ollama（推荐，本地隐私）

```bash
# 安装Ollama
brew install ollama  # macOS
curl -fsSL https://ollama.com/install.sh | sh  # Linux

# 启动服务
ollama serve

# 安装模型
ollama pull llama3.2
```

### OpenAI

```python
ai_configure(openai_key="sk-your-key")
```

### Anthropic Claude

```python
ai_configure(anthropic_key="sk-ant-your-key")
```

## 技术架构

```
Pikachu Pro MCP Servers
├── database_server     # 数据库层
│   ├── ConnectionPool  # 连接池
│   ├── Schema Explorer # Schema发现
│   └── Query Builder   # SQL构建
├── ai_server          # AI层
│   ├── Multi-Model     # 多模型支持
│   ├── Vector Store    # 向量存储
│   └── Prompt Engine   # Prompt模板
├── nl2sql_server      # NL2SQL层（核心差异化）
│   ├── Chinese Parser  # 中文解析
│   ├── Schema Mapper   # Schema映射
│   └── SQL Generator   # SQL生成
├── remote_server       # 远程层
│   ├── HTTP/SSE       # 传输协议
│   └── Service Disc.  # 服务发现
└── professional_server # 整合层
```

## 与Google Toolbox对比

| 维度 | Google | Pikachu Pro | 说明 |
|:---|:---:|:---:|:---|
| **NL2SQL语言** | 英文 | 中文+英文 | 我们专注中文 |
| **模型** | 云服务 | 本地+云 | Ollama隐私优先 |
| **部署** | 云 | 本地+云 | 灵活部署 |
| **文档** | 英文 | 中文+英文 | 完整中文文档 |
| **支持** | 社区 | 社区+商业 | 响应更快 |

## 定价

| 方案 | 价格 | 功能 |
|:---|:---:|:---|
| **免费版** | $0 | 基础MCP服务器（8个） |
| **Pro版** | $9.9/月 | 全部8个专业服务器 + 80+工具 + 技术支持 |
| **企业版** | 定制 | 私有部署 + 定制开发 + SLA |

## 获取Pro版

访问 [Pikachu MCP Pro](https://github.com/F5G5/pikachu-mcp-pro) 获取更多信息。

---

**皮卡丘出品 | 真正超越 | 中文优先** ⚡
