from flask import Flask, request, jsonify, session, redirect, url_for, render_template
from werkzeug.security import check_password_hash, generate_password_hash
import os

app = Flask(__name__)
app.secret_key = os.getenv('WEB_SECRET_KEY', 'this_should_be_changed')

WEB_USERNAME = os.getenv('WEB_USERNAME', 'admin')
WEB_PASSWORD = os.getenv('WEB_PASSWORD', 'admin_password')
WEB_PASSWORD_HASH = generate_password_hash(WEB_PASSWORD)

config_data = {
    "groups": {}
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
    if request.method == 'POST':
        try:
            new_config = request.json
            if not isinstance(new_config, dict):
                return jsonify({'error': '配置格式错误'}), 400
            global config_data
            config_data = new_config
            return jsonify({'status': 'ok'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify(config_data)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
