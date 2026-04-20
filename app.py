from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'salud-friendly-2026-unifranz'

# ==================== BASE DE DATOS ====================

def get_db():
    conn = sqlite3.connect('salud.db')
    conn.row_factory = sqlite3.Row
    return conn

def crear_tablas():
    conn = get_db()
    cursor = conn.cursor()
    
    #  TABLA USUARIOS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            tipo TEXT DEFAULT 'paciente',
            especialidad TEXT,
            matricula TEXT,
            fecha_nacimiento TEXT,
            ci TEXT,
            celular TEXT,
            alergias TEXT,
            grupo_sanguineo TEXT,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ASEGURA COLUMNAS
    columnas = [
        "especialidad TEXT",
        "matricula TEXT",
        "fecha_nacimiento TEXT",
        "ci TEXT",
        "celular TEXT",
        "alergias TEXT",
        "grupo_sanguineo TEXT"
    ]

    for col in columnas:
        try:
            cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {col}")
        except:
            pass

    # ==================== CITAS ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS citas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            doctor TEXT NOT NULL,
            especialidad TEXT NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,
            estado TEXT DEFAULT 'Programada',
            calificacion INTEGER DEFAULT NULL,
            comentario TEXT DEFAULT NULL,
            diagnostico TEXT DEFAULT NULL,
            recomendaciones TEXT DEFAULT NULL,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    ''')

    # ==================== TRÁMITES ====================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tramites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            estado TEXT DEFAULT 'Pendiente',
            fecha_solicitud TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    ''')

    conn.commit()
    conn.close()
    print('✅ Base de datos lista')

# ==================== RUTAS ====================

@app.route('/')
def index():
    return render_template('index.html')

# ==================== REGISTRO ====================

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        confirmar = request.form['confirmar_password']

        tipo = request.form.get('tipo_usuario', 'paciente')

        # PACIENTE
        fecha_nacimiento = request.form.get('fecha_nacimiento')
        ci = request.form.get('ci')
        celular = request.form.get('celular')
        alergias = request.form.get('alergias')
        grupo_sanguineo = request.form.get('grupo_sanguineo')

        # MÉDICO
        especialidad = request.form.get('especialidad')
        matricula = request.form.get('matricula')

        if password != confirmar:
            flash('❌ Las contraseñas no coinciden', 'error')
            return redirect(url_for('registro'))

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM usuarios WHERE email = ?', (email,))
        if cursor.fetchone():
            conn.close()
            flash('❌ El email ya está registrado', 'error')
            return redirect(url_for('registro'))

        if tipo == 'medico':
            cursor.execute('''
                INSERT INTO usuarios (nombre, email, password, tipo, especialidad, matricula)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (nombre, email, password, tipo, especialidad, matricula))
        else:
            cursor.execute('''
                INSERT INTO usuarios (nombre, email, password, tipo, fecha_nacimiento, ci, celular, alergias, grupo_sanguineo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nombre, email, password, tipo, fecha_nacimiento, ci, celular, alergias, grupo_sanguineo))

        conn.commit()
        conn.close()

        flash('✅ Registro exitoso', 'success')
        return redirect(url_for('login'))

    return render_template('registro.html')

# ==================== LOGIN ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        tipo = request.form.get('tipo', 'paciente')

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM usuarios 
            WHERE email = ? AND password = ? AND tipo = ?
        ''', (email, password, tipo))

        usuario = cursor.fetchone()
        conn.close()

        if usuario:
            session['usuario_id'] = usuario['id']
            session['nombre'] = usuario['nombre']
            session['tipo'] = usuario['tipo']

            flash(f'👋 Bienvenido {usuario["nombre"]}', 'success')

            return redirect(url_for('dashboard_medico' if usuario['tipo']=='medico' else 'dashboard'))
        else:
            flash('❌ Datos incorrectos', 'error')

    return render_template('login.html')

# ==================== DASHBOARD ====================

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    if session.get('tipo') == 'medico':
        return redirect(url_for('dashboard_medico'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM citas WHERE usuario_id = ?', (session['usuario_id'],))
    citas_count = cursor.fetchone()['count']
    conn.close()

    return render_template('dashboard.html', citas_count=citas_count)

@app.route('/dashboard_medico')
def dashboard_medico():
    if 'usuario_id' not in session or session.get('tipo') != 'medico':
        return redirect(url_for('login'))

    hoy = datetime.now().strftime('%Y-%m-%d')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM citas WHERE fecha = ? ORDER BY hora ASC', (hoy,))
    citas = cursor.fetchall()
    conn.close()

    return render_template('dashboard_medico.html', citas=citas)

# ==================== CITAS ====================

@app.route('/agendar_cita', methods=['GET','POST'])
def agendar_cita():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO citas (usuario_id, doctor, especialidad, fecha, hora)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            session['usuario_id'],
            request.form['doctor'],
            request.form['especialidad'],
            request.form['fecha'],
            request.form['hora']
        ))
        conn.commit()
        conn.close()

        flash('✅ Cita agendada', 'success')
        return redirect(url_for('mis_citas'))

    return render_template('agendar_cita.html')

@app.route('/mis_citas')
def mis_citas():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM citas WHERE usuario_id = ?', (session['usuario_id'],))
    citas = cursor.fetchall()
    conn.close()

    return render_template('mis_citas.html', citas=citas)

# ==================== OTRAS ====================

@app.route('/tramites', methods=['GET','POST'])
def tramites():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        cursor.execute('INSERT INTO tramites (usuario_id, tipo) VALUES (?, ?)',
                       (session['usuario_id'], request.form['tipo_tramite']))
        conn.commit()

    cursor.execute('SELECT * FROM tramites WHERE usuario_id = ?', (session['usuario_id'],))
    tramites = cursor.fetchall()
    conn.close()

    return render_template('tramites.html', tramites=tramites)

@app.route('/atencion')
def atencion():
    return render_template('atencion.html')

@app.route('/doctores')
def doctores():
    return render_template('doctores.html')

@app.route('/resultados')
def resultados():
    return render_template('resultados.html')

@app.route('/contacto')
def contacto():
    return render_template('contacto.html')

@app.route('/perfil')
def perfil():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT fecha_registro FROM usuarios WHERE id = ?', (session['usuario_id'],))
    usuario = cursor.fetchone()
    conn.close()

    return render_template('perfil.html', fecha_registro=usuario['fecha_registro'][:10])

@app.route('/historial')
def historial():
    return render_template('historial.html')

# ==================== LOGOUT ====================

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ==================== INICIO ====================

if __name__ == '__main__':
    crear_tablas()
    
    print('\n' + '='*60)
    print('🏥  SALUD FRIENDLY - Servidor Iniciado')
    print('='*60)
    print('📊 Base de datos: salud.db')
    print('🌐 URL: http://localhost:5000')
    print('='*60 + '\n')
    
    app.run(debug=True)