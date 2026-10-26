from __future__ import annotations
import hmac, os, re, secrets, sqlite3
from pathlib import Path
from flask import Flask, abort, g, redirect, render_template, request, session, url_for

BASE = Path(__file__).resolve().parent
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-only-change-me')
app.config.update(
    DATABASE=os.environ.get('DATABASE', str(BASE / 'tutor.db')),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE', '').lower() == 'true',
    MAX_CONTENT_LENGTH=16 * 1024,
)

COURSE = {
    'title': 'Fundamentos de APIs REST',
    'lessons': [
        {'id': 1, 'title': 'Métodos HTTP: GET y POST', 'content': 'Una API REST permite que aplicaciones intercambien datos mediante HTTP. GET se usa para consultar o recuperar un recurso y normalmente no modifica el estado del servidor. POST se usa para enviar datos al servidor, por ejemplo para crear un recurso o iniciar un procesamiento. El cuerpo de una petición POST suele contener los datos enviados. Las respuestas HTTP incluyen un código de estado, como 200 (éxito), 201 (creado) o 404 (no encontrado).'},
        {'id': 2, 'title': 'Rutas, recursos y códigos', 'content': 'En REST, una ruta identifica un recurso, por ejemplo /api/usuarios. Los recursos suelen representarse como sustantivos y pueden tener identificadores, como /api/usuarios/42. PUT reemplaza un recurso, PATCH actualiza parte de él y DELETE solicita eliminarlo. Los códigos 2xx indican éxito, 4xx un problema en la solicitud del cliente y 5xx un error del servidor.'}
    ]
}
USERS = {'ana': {'name':'Ana', 'password':'ana123', 'allowed':True}, 'luis': {'name':'Luis (sin acceso)', 'password':'luis123', 'allowed':False}}

def db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute('CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, username TEXT NOT NULL, lesson_id INTEGER NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    return g.db

@app.teardown_appcontext
def close_db(_=None):
    conn = g.pop('db', None)
    if conn: conn.close()

def current_user(): return USERS.get(session.get('username'))

@app.before_request
def ensure_csrf_token():
    session.setdefault('csrf_token', secrets.token_urlsafe(32))

def valid_csrf_token():
    supplied = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token', '')
    expected = session.get('csrf_token', '')
    return bool(expected and supplied and hmac.compare_digest(expected, supplied))

@app.context_processor
def inject_csrf_token():
    return {'csrf_token': session.get('csrf_token', '')}
def require_course():
    user = current_user()
    if not user: return redirect(url_for('login'))
    if not user['allowed']: abort(403, 'Tu cuenta no tiene acceso a este curso.')
    return None

def tutor_answer(question, lesson):
    # Lightweight extractive tutor: only answers when lesson text shares meaningful terms.
    words = {w.lower() for w in re.findall(r'[a-záéíóúñ]{3,}', question, re.IGNORECASE) if w.lower() not in {'para','como','qué','que','una','del','las','los','por','sirve','hace','dime','explica'}}
    sentences = re.split(r'(?<=[.!?])\s+', lesson['content'])
    ranked = sorted(((sum(1 for w in words if w in s.lower()), s) for s in sentences), reverse=True)
    if not words or not ranked or ranked[0][0] == 0:
        return 'No encuentro información suficiente sobre eso en esta lección. Prueba preguntando por los métodos, rutas o códigos HTTP que aparecen en el material.'
    best = [s for score, s in ranked if score >= max(1, ranked[0][0] - 1)][:3]
    return ' '.join(best)

@app.route('/')
def index(): return redirect(url_for('login') if not current_user() else url_for('course'))
@app.route('/login', methods=['GET','POST'])
def login():
    error = None
    if request.method == 'POST':
        if not valid_csrf_token(): abort(400)
        name, password = request.form.get('username',''), request.form.get('password','')
        user = USERS.get(name.strip().lower())
        if user and hmac.compare_digest(user['password'], password):
            session.clear(); session['username'] = name.strip().lower()
            session['csrf_token'] = secrets.token_urlsafe(32)
            return redirect(url_for('course'))
        error = 'Usuario o contraseña incorrectos.'
    return render_template('login.html', error=error)
@app.route('/logout', methods=['POST'])
def logout():
    if not valid_csrf_token(): abort(400)
    session.clear()
    return redirect(url_for('login'))
@app.route('/course')
def course():
    denied = require_course()
    if denied: return denied
    return render_template('course.html', user=current_user(), course=COURSE)
@app.route('/lesson/<int:lesson_id>')
def lesson(lesson_id):
    denied = require_course()
    if denied: return denied
    item = next((x for x in COURSE['lessons'] if x['id'] == lesson_id), None)
    if not item: abort(404)
    rows = db().execute('SELECT role,content,created_at FROM messages WHERE username=? AND lesson_id=? ORDER BY id', (session['username'], lesson_id)).fetchall()
    return render_template('lesson.html', user=current_user(), course=COURSE, lesson=item, messages=rows)
@app.route('/api/lesson/<int:lesson_id>/ask', methods=['POST'])
def ask(lesson_id):
    if not valid_csrf_token(): abort(400)
    denied = require_course()
    if denied: return denied
    item = next((x for x in COURSE['lessons'] if x['id'] == lesson_id), None)
    if not item: abort(404)
    payload = request.get_json(silent=True) if request.is_json else request.form
    question = payload.get('question', '').strip() if payload else ''
    if not question or len(question) > 1000: return {'error':'Escribe una pregunta de hasta 1000 caracteres.'}, 400
    answer = tutor_answer(question, item)
    conn = db()
    conn.executemany('INSERT INTO messages(username,lesson_id,role,content) VALUES(?,?,?,?)', [(session['username'],lesson_id,'user',question),(session['username'],lesson_id,'assistant',answer)])
    conn.commit()
    return {'question':question,'answer':answer}

@app.errorhandler(403)
def forbidden(e): return render_template('error.html', code=403, message=e.description), 403
if __name__ == '__main__': app.run(debug=False, port=int(os.environ.get('PORT', 5000)))
