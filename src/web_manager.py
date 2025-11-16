from flask import Flask, request, jsonify, session, redirect, url_for, render_template
from werkzeug.security import check_password_hash, generate_password_hash
import os, json

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.getenv('WEB_SECRET_KEY', 'change_this_secret')
CONFIG_FILE = 'config.json'
WEB_USERNAME = os.getenv('WEB_USERNAME', 'admin')
WEB_PASSWORD = os.getenv('WEB_PASSWORD', 'admin123')
WEB_PASSWORD_HASH = generate_password_hash(WEB_PASSWORD)

def load_config():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)
def dump_config(cfg):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

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
    app.run(host='0.0.0.0', port=5000)
