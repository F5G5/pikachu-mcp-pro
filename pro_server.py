"""
皮卡丘Pro MCP Server - 高级版 ⚡
包含更多高级功能和真实数据源
"""
from fastmcp import FastMCP
import urllib.request
import json
from datetime import datetime
import hashlib
import time

mcp = FastMCP("皮卡丘Pro服务")

# ============ Pro级别天气服务 ============

@mcp.tool()
def get_weather_pro(city: str, hourly: bool = False) -> str:
    """高级天气查询 - 包含小时级预报"""
    try:
        url = f"https://wttr.in/{city}?format=j1"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
        
        current = data['current_condition'][0]
        
        result = f"""🌤️ {city} 高级天气报告
{'='*40}
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}

🌡️ 温度: {current['temp_C']}°C (体感 {current['FeelsLikeC']}°C)
🌤️ 天气: {current['weatherDesc'][0]['value']}
💧 湿度: {current['humidity']}%
🌬️ 风速: {current['windspeedKmph']} km/h
☀️ 紫外线: {current['UVIndex']}
🌙 月相: {current['moonphase']}

📊 详细信息:
   能见度: {current['visibility']} km
   气压: {current['pressure']} mb
   云量: {current['cloudcover']}%
   FeelsLike: {current['FeelsLikeC']}°C"""
        
        if hourly and 'weather' in data and len(data['weather']) > 0:
            result += "\n\n⏱️ 24小时预报:"
            for i, hour in enumerate(data['weather'][0]['hourly'][:8]):
                time_str = hour['time']
                temp = hour['tempC']
                desc = hour['weatherDesc'][0]['value']
                result += f"\n   {time_str[:2]}:00 - {temp}°C {desc}"
        
        return result
    except Exception as e:
        return f"查询失败: {str(e)}"

# ============ 股票查询Pro ============

@mcp.tool()
def get_stock_price(symbol: str) -> str:
    """股票价格查询（模拟Pro数据）"""
    # 模拟股票数据
    stocks = {
        "AAPL": {"name": "Apple Inc.", "price": 178.52, "change": +2.34, "volume": "52.3M"},
        "GOOGL": {"name": "Alphabet Inc.", "price": 141.80, "change": -0.95, "volume": "18.2M"},
        "MSFT": {"name": "Microsoft Corp.", "price": 378.91, "change": +4.12, "volume": "15.8M"},
        "TSLA": {"name": "Tesla Inc.", "price": 248.50, "change": -5.30, "volume": "89.4M"},
        "NVDA": {"name": "NVIDIA Corp.", "price": 875.28, "change": +15.67, "volume": "32.1M"},
        "BABA": {"name": "Alibaba Group", "price": 72.35, "change": +1.25, "volume": "45.6M"},
        "JD": {"name": "JD.com", "price": 28.90, "change": -0.45, "volume": "12.3M"},
        "PDD": {"name": "Pinduoduo", "price": 145.60, "change": +3.80, "volume": "8.9M"},
    }
    
    symbol = symbol.upper()
    if symbol in stocks:
        s = stocks[symbol]
        arrow = "📈" if s['change'] > 0 else "📉"
        return f"""📈 {s['name']} ({symbol})
{'='*40}
💰 价格: ${s['price']:.2f}
{arrow} 涨跌: ${s['change']:+.2f} ({s['change']/s['price']*100:+.2f}%)
📊 成交量: {s['volume']}
⏰ 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
    else:
        return f"不支持的股票代码: {symbol}\n支持的代码: {', '.join(stocks.keys())}"

@mcp.tool()
def get_crypto_price(coin: str) -> str:
    """加密货币价格查询（模拟Pro数据）"""
    cryptos = {
        "BTC": {"name": "Bitcoin", "price": 67542.30, "change": 2.34, "high": 68200, "low": 66100},
        "ETH": {"name": "Ethereum", "price": 3456.78, "change": -1.23, "high": 3520, "low": 3380},
        "BNB": {"name": "Binance Coin", "price": 598.45, "change": 0.89, "high": 605, "low": 590},
        "SOL": {"name": "Solana", "price": 178.90, "change": 5.67, "high": 185, "low": 168},
        "XRP": {"name": "Ripple", "price": 0.5234, "change": -2.10, "high": 0.54, "low": 0.51},
    }
    
    coin = coin.upper()
    if coin in cryptos:
        c = cryptos[coin]
        arrow = "📈" if c['change'] > 0 else "📉"
        return f"""🪙 {c['name']} ({coin})
{'='*40}
💰 价格: ${c['price']:,.2f}
{arrow} 24h涨跌: {c['change']:+.2f}%
📊 24h高: ${c['high']:,.2f}
📊 24h低: ${c['low']:,.2f}
⏰ 更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⚠️ 注意: 数据为模拟，仅供参考"""
    else:
        return f"不支持的币种: {coin}\n支持的币种: {', '.join(cryptos.keys())}"

# ============ AI新闻分析Pro ============

@mcp.tool()
def get_ai_news() -> str:
    """AI行业最新新闻"""
    try:
        url = "https://hn.algolia.com/api/v1/search?query=AI+OR+artificial+intelligence&tags=story&hitsPerPage=10"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
        
        result = f"""🤖 AI行业最新资讯
{'='*40}
📅 {datetime.now().strftime('%Y-%m-%d')}\n\n"""
        
        for i, hit in enumerate(data.get('hits', [])[:8], 1):
            title = hit.get('title', 'No title')
            url = hit.get('url', hit.get('objectID', ''))
            points = hit.get('points', 0)
            result += f"{i}. {title}\n"
            result += f"   ⬆️ {points} | 🔗 {url[:60]}...\n\n"
        
        return result
    except Exception as e:
        return f"获取失败: {str(e)}"

# ============ SEO分析Pro ============

@mcp.tool()
def analyze_seo(title: str, description: str, keywords: str) -> str:
    """SEO分析工具"""
    title_len = len(title)
    desc_len = len(description)
    keyword_list = [k.strip() for k in keywords.split(',')]
    
    score = 0
    issues = []
    suggestions = []
    
    # Title检查
    if 30 <= title_len <= 60:
        score += 25
        suggestions.append(f"✅ Title长度合适 ({title_len}字符)")
    elif title_len < 30:
        issues.append(f"⚠️ Title太短 ({title_len}字符)，建议30-60字符")
    else:
        issues.append(f"⚠️ Title太长 ({title_len}字符)，会被截断")
    
    # Description检查
    if 120 <= desc_len <= 160:
        score += 25
        suggestions.append(f"✅ Description长度合适 ({desc_len}字符)")
    elif desc_len < 120:
        issues.append(f"⚠️ Description太短 ({desc_len}字符)，建议120-160字符")
    else:
        issues.append(f"⚠️ Description太长 ({desc_len}字符)，会被截断")
    
    # Keywords检查
    if len(keyword_list) >= 3:
        score += 25
        suggestions.append(f"✅ 关键词数量合适 ({len(keyword_list)}个)")
    else:
        issues.append(f"⚠️ 关键词太少，建议3-5个")
    
    # 标题包含关键词
    title_lower = title.lower()
    if any(k.lower() in title_lower for k in keyword_list):
        score += 25
        suggestions.append("✅ Title中包含关键词")
    else:
        issues.append("⚠️ 建议在Title中加入核心关键词")
    
    result = f"""🔍 SEO分析报告
{'='*40}

📊 得分: {score}/100

📝 Title: {title}
   字符: {title_len}/60

📄 Description: {description[:80]}...
   字符: {desc_len}/160

🏷️ Keywords: {keywords}

{'✅ 优点:' if suggestions else ''}
{chr(10).join(suggestions)}

{'⚠️ 问题:' if issues else ''}
{chr(10).join(issues)}

{'🎯 优化建议:' if score < 75 else '🌟 整体良好!'}
"""
    if score < 75:
        result += "- 确保Title和Description包含核心关键词\n"
        result += "- 保持Title在50-60字符之间\n"
        result += "- Description建议在150字符左右"
    
    return result

# ============ 密码生成Pro ============

@mcp.tool()
def generate_password(length: int = 16, use_special: bool = True) -> str:
    """安全密码生成器"""
    import secrets
    import string
    
    alphabet = string.ascii_letters + string.digits
    if use_special:
        alphabet += "!@#$%^&*"
    
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    
    # 计算强度
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password) if use_special else True
    
    strength = sum([has_upper, has_lower, has_digit, has_special])
    
    strength_labels = {1: "弱", 2: "中等", 3: "良好", 4: "强"}
    
    return f"""🔐 安全密码生成
{'='*40}

📋 密码: {password}

📊 强度: {strength_labels.get(strength, '?')} ({strength}/4)
   ✅ 大写字母: {'有' if has_upper else '无'}
   ✅ 小写字母: {'有' if has_lower else '无'}
   ✅ 数字: {'有' if has_digit else '无'}
   ✅ 特殊字符: {'有' if has_special else '无'}

⚠️ 安全提醒:
- 请立即使用此密码，不要共享
- 建议使用密码管理器
- 不同网站使用不同密码"""

if __name__ == "__main__":
    mcp.run()
