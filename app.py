from flask import Flask
from config import SECRET_KEY
from database import init_db
from routes.auth import auth_bp
from routes.alumno import alumno_bp
from routes.admin import admin_bp

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['SESSION_TYPE'] = 'filesystem'

app.register_blueprint(auth_bp)
app.register_blueprint(alumno_bp)
app.register_blueprint(admin_bp)

init_db()

if __name__ == '__main__':
    print("=" * 55)
    print("  APP DE INCIDENCIAS ESCOLARES")
    print("=" * 55)
    print("  Padres  →  http://127.0.0.1:5000")
    print("  Maestra →  http://127.0.0.1:5000/admin")
    print("=" * 55)
    app.run(debug=True, host='0.0.0.0')