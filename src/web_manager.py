from flask import Flask, request, jsonify, session, redirect, url_for, render_template
from werkzeug.security import check_password_hash, generate_password_hash
import os
import storage  # 引入 storage

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.getenv('WEB_SECRET_KEY', 'change_this_secret')
WEB_USERNAME = os.getenv('WEB_USERNAME', 'admin')
WEB_PASSWORD = os.getenv('WEB_PASSWORD', 'admin123')
WEB_PASSWORD_HASH = generate_password_hash(WEB_PASSWORD)

def load_config():
    """从存储加载配置"""
    cfg = storage.load_data('config')
    # 如果存储中没有配置（例如新部署的数据库），返回默认结构，防止前端报错
    if not cfg:
        return {
            "notifiers": {
                "email": {},
                "bark": [],
                "pushplus": []
            },
            "groups": [],
            "scheduled_tasks": [],
            "scrape_channels": [],
            "auto_delete_rules": [],
            "forward_rules": []
        }
    return cfg

def dump_config(cfg):
    """保存配置到存储"""
    storage.save_data('config', cfg)

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
    return render_template('index.html', config=load_config())

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    if request.method == 'POST':
        new_config = request.json
        dump_config(new_config)
        return jsonify({'status': 'ok'})
    return jsonify(load_config())

@app.route('/api/notifiers', methods=['GET', 'POST'])
def api_notifiers():
    cfg = load_config()
    if request.method == 'POST':
        data = request.json
        cfg['notifiers'] = data
        dump_config(cfg)
        return jsonify({'status':'ok'})
    return jsonify(cfg['notifiers'])

if __name__ == "__main__":
    # Web 启动时也初始化存储
    storage.init_storage()
    app.run(host='0.0.0.0', port=5000)
