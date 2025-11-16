from flask import Flask, request, jsonify, session, redirect, url_for, render_template
from werkzeug.security import check_password_hash, generate_password_hash
import os

app = Flask(__name__)
app.secret_key = os.getenv('WEB_SECRET_KEY', 'this_should_be_changed')

# 账号密码环境变量（明文）
WEB_USERNAME = os.getenv('WEB_USERNAME', 'admin')
WEB_PASSWORD = os.getenv('WEB_PASSWORD', 'admin_password')

# 密码哈希用于比对
WEB_PASSWORD_HASH = generate_password_hash(WEB_PASSWORD)

# 配置存储结构
config_data = {
    "groups": {
        # 示例格式
        # "10000": {
        #     "bark_tokens": ["your_bark_token_1"],
        #     "pushplus_tokens": ["your_pushplus_token_1"],
        #     "keywords": {
        #         "你好": "bark",
        #         "中国": "pushplus"
        #     }
        # }
    }
}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username') or ''
        password = request.form.get('password') or ''
        if username == WEB_USERNAME and check_password_hash(WEB_PASSWORD_HASH, password):
            session['logged_in'] = True
            return redirect(url_for('index'))
        return render_template('login.html', error="用户名或密码错误")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('index.html', config=config_data)

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    if not session.get('logged_in'):
        return jsonify({'error': '未授权'}), 403
    if request.method == 'POST':
        try:
            new_config = request.json
            if not isinstance(new_config, dict):
                return jsonify({'error': '配置格式错误'}), 400
            global config_data
            config_data = new_config
            # 这里可以写入文件实现持久化
            return jsonify({'status': 'ok'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify(config_data)

# 基本登录页面模板，放在 src/templates/login.html
login_html = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>登录 - Telegram 管理系统</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 50px; }
    form { max-width: 300px; margin: auto; }
    input { width: 100%; padding: 10px; margin: 5px 0; }
    .error { color: red; }
  </style>
</head>
<body>
  <h2>登录到管理系统</h2>
  {% if error %}<p class="error">{{ error }}</p>{% endif %}
  <form method="post">
    <input name="username" placeholder="用户名" required autofocus>
    <input name="password" type="password" placeholder="密码" required>
    <button type="submit">登录</button>
  </form>
</body>
</html>
"""

# 管理首页简单模板 src/templates/index.html
index_html = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>群组配置管理 - Telegram 管理系统</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 8px; }
    th { background: #f2f2f2; }
    textarea { width: 100%; height: 60px; }
    input[type=text] { width: 100%; }
    button { margin-top: 10px; padding: 8px 12px; }
    .logout { float:right; }
  </style>
</head>
<body>
  <h1>群组配置管理</h1>
  <a class="logout" href="/logout">退出登录</a>
  
  <form id="configForm">
    <textarea id="configData" spellcheck="false">{{ config | tojson }}</textarea><br/>
    <button type="submit">保存配置</button>
  </form>
  <pre id="result"></pre>

  <script>
  document.getElementById('configForm').onsubmit = async function(e) {
    e.preventDefault();
    let data = document.getElementById('configData').value;
    try {
      let json = JSON.parse(data);
      let resp = await fetch('/api/config', {
        method: 'POST', 
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(json)
      });
      let text = await resp.text();
      document.getElementById('result').textContent = text;
    } catch(e) {
      document.getElementById('result').textContent = 'JSON 格式错误';
    }
  }
  </script>
</body>
</html>
"""

from flask import render_template_string

@app.route('/login.html')
def login_html_route():
    return render_template_string(login_html, error=None)

@app.route('/index.html')
def index_html_route():
    return render_template_string(index_html, config=config_data)

# 使用 render_template_string 代替文件模板，确保代码完整自运行

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
