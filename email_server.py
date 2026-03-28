"""
Pikachu Email MCP Server ⚡
发送邮件、读取邮件
"""
from fastmcp import FastMCP
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

mcp = FastMCP("PikachuEmail")

# 配置存储
_email_config = {
    "smtp_host": "",
    "smtp_port": 587,
    "smtp_user": "",
    "smtp_password": "",
    "from_name": "Pikachu Bot"
}

@mcp.tool()
def configure_email(host: str, port: int, username: str, password: str, from_name: str = "Pikachu") -> str:
    """配置SMTP邮件服务器"""
    _email_config["smtp_host"] = host
    _email_config["smtp_port"] = port
    _email_config["smtp_user"] = username
    _email_config["smtp_password"] = password
    _email_config["from_name"] = from_name
    
    return f"""[EMAIL CONFIGURED]
Host: {host}:{port}
User: {username}
From Name: {from_name}

Note: Use send_email to send messages!
Supported: QQ邮箱, 163邮箱, Gmail, 企业邮箱等

Example for QQ邮箱:
- Host: smtp.qq.com
- Port: 587
- User: your@qq.com
- Password: 授权码（非QQ密码）
"""

@mcp.tool()
def send_email(to: str, subject: str, body: str, body_type: str = "plain") -> str:
    """发送邮件
    body_type: plain (纯文本) 或 html (HTML格式)
    """
    try:
        if not _email_config["smtp_host"]:
            return "[ERROR] Email not configured. Use configure_email first!"
        
        msg = MIMEMultipart()
        msg['From'] = f"{_email_config['from_name']} <{_email_config['smtp_user']}>"
        msg['To'] = to
        msg['Subject'] = subject
        msg['Date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 添加正文
        if body_type == "html":
            msg.attach(MIMEText(body, 'html', 'utf-8'))
        else:
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 发送
        server = smtplib.SMTP(_email_config["smtp_host"], _email_config["smtp_port"])
        server.starttls()
        server.login(_email_config["smtp_user"], _email_config["smtp_password"])
        server.send_message(msg)
        server.quit()
        
        return f"""[EMAIL SENT]
To: {to}
Subject: {subject}
Status: Success!

Email delivered at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
    except Exception as e:
        return f"[ERROR] {str(e)}\n\n常见问题:\n1. 检查SMTP配置是否正确\n2. QQ邮箱需要授权码，不是QQ密码\n3. 163邮箱也需要授权码"

@mcp.tool()
def send_html_email(to: str, subject: str, html_content: str) -> str:
    """发送HTML格式邮件"""
    return send_email(to, subject, html_content, "html")

@mcp.tool()
def send_email_template(to: str, template: str, data: str) -> str:
    """使用模板发送邮件
    template: welcome, notification, reminder, report
    data: JSON格式的模板变量
    """
    templates = {
        "welcome": {
            "subject": "Welcome to {{service}}!",
            "body": """Dear {{name}},

Welcome to {{service}}!

We're excited to have you on board. Here are some quick links to get started:

- Documentation: {{docs_url}}
- Support: {{support_email}}
- Your Dashboard: {{dashboard_url}}

Best regards,
The {{service}} Team"""
        },
        "notification": {
            "subject": "[Notification] {{title}}",
            "body": """Hi {{name}},

{{title}}

{{message}}

Time: {{time}}
Link: {{link}}

This is an automated notification from {{service}}."""
        },
        "reminder": {
            "subject": "[Reminder] {{title}}",
            "body": """Reminder for {{name}}:

{{title}}

{{description}}

Due: {{due_date}}
Priority: {{priority}}

{{action_required}}"""
        },
        "report": {
            "subject": "{{report_title}} - Report {{date}}",
            "body": """{{report_title}}
Generated: {{date}}

Summary:
{{summary}}

Details:
{{details}}

---
Sent by Pikachu Email Bot"""
        }
    }
    
    try:
        if template not in templates:
            return f"[ERROR] Unknown template: {template}\n\nAvailable: {', '.join(templates.keys())}"
        
        data_dict = json.loads(data) if isinstance(data, str) else data
        tmpl = templates[template]
        
        # 替换变量
        subject = tmpl["subject"]
        body = tmpl["body"]
        
        for key, value in data_dict.items():
            subject = subject.replace(f"{{{{{key}}}}}", str(value))
            body = body.replace(f"{{{{{key}}}}}", str(value))
        
        return send_email(to, subject, body)
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def batch_send_email(recipients: str, subject: str, body: str) -> str:
    """批量发送邮件
    recipients: JSON数组格式 ["email1@test.com", "email2@test.com"]
    """
    try:
        recipient_list = json.loads(recipients) if isinstance(recipients, str) else recipients
        
        if not isinstance(recipient_list, list):
            return "[ERROR] recipients must be a list"
        
        success = 0
        failed = 0
        errors = []
        
        for to in recipient_list:
            result = send_email(to, subject, body)
            if result.startswith("[ERROR]"):
                failed += 1
                errors.append(f"{to}: {result}")
            else:
                success += 1
        
        report = f"""[BATCH SEND COMPLETE]
Total: {len(recipient_list)}
Success: {success}
Failed: {failed}"""
        
        if errors:
            report += "\n\n[ERRORS]\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                report += f"\n... and {len(errors) - 5} more"
        
        return report
        
    except Exception as e:
        return f"[ERROR] {str(e)}"

@mcp.tool()
def email_status() -> str:
    """检查邮件配置状态"""
    if _email_config["smtp_host"]:
        return f"""[EMAIL STATUS]
Host: {_email_config['smtp_host']}
Port: {_email_config['smtp_port']}
User: {_email_config['smtp_user']}
From: {_email_config['from_name']}
Status: Configured and ready"""
    else:
        return """[EMAIL STATUS]
Status: Not configured

Use configure_email to set up SMTP server:
- QQ邮箱: smtp.qq.com:587
- 163邮箱: smtp.163.com:465
- Gmail: smtp.gmail.com:587"""

if __name__ == "__main__":
    mcp.run()
