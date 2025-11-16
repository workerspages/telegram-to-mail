login_html = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>登录 - Telegram 管理系统</title>
  <link rel="stylesheet" type="text/css" href="{{ url_for('static', filename='style.css') }}">
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
