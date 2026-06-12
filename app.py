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

    # TABLA USUARIOS
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
            complemento_ci TEXT,
            celular TEXT,
            alergias TEXT,
            grupo_sanguineo TEXT,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ASEGURA COLUMNAS (por si la BD ya existe sin alguna columna)
    columnas = [
        "especialidad TEXT",
        "matricula TEXT",
        "fecha_nacimiento TEXT",
        "ci TEXT",
        "complemento_ci TEXT",
        "celular TEXT",
        "alergias TEXT",
        "grupo_sanguineo TEXT"
    ]
    for col in columnas:
        try:
            cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {col}")
        except:
            pass

    # TABLA CITAS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS citas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            doctor TEXT NOT NULL,
            especialidad TEXT NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,
            estado TEXT DEFAULT 'Pendiente confirmacion',
            calificacion INTEGER DEFAULT NULL,
            comentario TEXT DEFAULT NULL,
            diagnostico TEXT DEFAULT NULL,
            recomendaciones TEXT DEFAULT NULL,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    ''')

    # TABLA TRÁMITES
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
        nombre           = request.form['nombre']
        email            = request.form['email']
        password         = request.form['password']
        confirmar        = request.form['confirmar_password']
        tipo             = request.form.get('tipo_usuario', 'paciente')
        fecha_nacimiento = request.form.get('fecha_nacimiento')
        ci               = request.form.get('ci')
        complemento_ci   = request.form.get('complemento_ci', '').strip()
        celular          = request.form.get('celular')
        alergias         = request.form.get('alergias')
        grupo_sanguineo  = request.form.get('grupo_sanguineo')
        especialidad     = request.form.get('especialidad')
        matricula        = request.form.get('matricula')

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
                INSERT INTO usuarios (nombre, email, password, tipo, fecha_nacimiento,
                ci, complemento_ci, celular, alergias, grupo_sanguineo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nombre, email, password, tipo, fecha_nacimiento,
                  ci, complemento_ci, celular, alergias, grupo_sanguineo))

        conn.commit()
        conn.close()
        flash('✅ Registro exitoso', 'success')
        return redirect(url_for('login'))

    return render_template('registro.html')

# ==================== LOGIN ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        tipo     = request.form.get('tipo', 'paciente')
        password = request.form['password']
        conn     = get_db()
        cursor   = conn.cursor()

        if tipo == 'paciente':
            ci          = request.form.get('ci', '').strip()
            complemento = request.form.get('complemento', '').strip().upper()

            if not ci:
                flash('❌ Ingresá tu número de carnet', 'error')
                conn.close()
                return render_template('login.html')

            # Validación extra: CI solo debe contener números
            if not ci.isdigit():
                flash('❌ El número de carnet solo debe contener números', 'error')
                conn.close()
                return render_template('login.html')

            cursor.execute('''
                SELECT * FROM usuarios
                WHERE ci = ? AND password = ? AND tipo = 'paciente'
            ''', (ci, password))
            usuario = cursor.fetchone()

            if usuario:
                complemento_bd = (usuario['complemento_ci'] or '').strip().upper()
                if complemento and complemento != complemento_bd:
                    usuario = None
        else:
            email = request.form.get('email', '').strip()

            if not email:
                flash('❌ Ingresá tu email', 'error')
                conn.close()
                return render_template('login.html')

            cursor.execute('''
                SELECT * FROM usuarios
                WHERE email = ? AND password = ? AND tipo = 'medico'
            ''', (email, password))
            usuario = cursor.fetchone()

        conn.close()

        if usuario:
            session['usuario_id'] = usuario['id']
            session['nombre']     = usuario['nombre']
            session['tipo']       = usuario['tipo']
            flash(f'👋 Bienvenido {usuario["nombre"]}', 'success')
            return redirect(url_for('dashboard_medico' if usuario['tipo'] == 'medico' else 'dashboard'))
        else:
            flash('❌ Datos incorrectos.', 'error')

    return render_template('login.html')

# ==================== DASHBOARD PACIENTE ====================

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

# ==================== DASHBOARD MÉDICO ====================

@app.route('/dashboard_medico')
def dashboard_medico():
    if 'usuario_id' not in session or session.get('tipo') != 'medico':
        return redirect(url_for('login'))

    hoy        = datetime.now().strftime('%Y-%m-%d')
    mes_actual = datetime.now().strftime('%Y-%m')

    conn   = get_db()
    cursor = conn.cursor()

    # Info del médico logueado
    cursor.execute('SELECT * FROM usuarios WHERE id = ?', (session['usuario_id'],))
    medico = cursor.fetchone()

    # Citas de HOY confirmadas/atendidas para este médico
    cursor.execute('''
        SELECT citas.*, usuarios.nombre AS nombre_paciente
        FROM citas
        JOIN usuarios ON citas.usuario_id = usuarios.id
        WHERE citas.fecha = ?
          AND citas.doctor = ?
          AND citas.estado IN ('Programada', 'Atendida')
        ORDER BY citas.hora ASC
    ''', (hoy, medico['nombre']))
    citas_hoy = cursor.fetchall()

    # Citas pendientes de confirmación (cualquier fecha)
    cursor.execute('''
        SELECT citas.*, usuarios.nombre AS nombre_paciente
        FROM citas
        JOIN usuarios ON citas.usuario_id = usuarios.id
        WHERE citas.doctor = ?
          AND citas.estado = 'Pendiente confirmacion'
        ORDER BY citas.fecha ASC, citas.hora ASC
    ''', (medico['nombre'],))
    citas_pendientes = cursor.fetchall()

    # Estadísticas
    pendientes_count = len(citas_pendientes)
    atendidas        = sum(1 for c in citas_hoy if c['estado'] == 'Atendida')
    programadas      = sum(1 for c in citas_hoy if c['estado'] == 'Programada')

    cursor.execute('''
        SELECT COUNT(*) AS total FROM citas
        WHERE doctor = ? AND fecha LIKE ?
    ''', (medico['nombre'], mes_actual + '%'))
    total_mes = cursor.fetchone()['total']

    conn.close()

    return render_template('dashboard_medico.html',
        citas_hoy=citas_hoy,
        citas_pendientes=citas_pendientes,
        pendientes_count=pendientes_count,
        programadas=programadas,
        atendidas=atendidas,
        total_mes=total_mes,
        medico=medico,
        hoy=hoy
    )

# ==================== CONFIRMAR / RECHAZAR CITA ====================

@app.route('/confirmar_cita/<int:cita_id>', methods=['POST'])
def confirmar_cita(cita_id):
    if 'usuario_id' not in session or session.get('tipo') != 'medico':
        return redirect(url_for('login'))

    accion = request.form.get('accion')

    if accion == 'confirmar':
        nuevo_estado = 'Programada'
        motivo       = None
        msg          = '✅ Cita confirmada correctamente'
    else:
        nuevo_estado = 'Rechazada'
        # Guarda el motivo seleccionado por el médico en el campo comentario
        motivo = request.form.get('motivo_rechazo', 'Sin especificar')
        msg    = f'❌ Cita rechazada: {motivo}'

    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE citas SET estado = ?, comentario = ? WHERE id = ?',
        (nuevo_estado, motivo, cita_id)
    )
    conn.commit()
    conn.close()

    flash(msg, 'success')
    return redirect(url_for('dashboard_medico'))

# ==================== AGENDAR CITA ====================

@app.route('/agendar_cita', methods=['GET', 'POST'])
def agendar_cita():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    conn   = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        cursor.execute('''
            INSERT INTO citas (usuario_id, doctor, especialidad, fecha, hora, estado)
            VALUES (?, ?, ?, ?, ?, 'Pendiente confirmacion')
        ''', (
            session['usuario_id'],
            request.form['doctor'],
            request.form['especialidad'],
            request.form['fecha'],
            request.form['hora']
        ))
        conn.commit()
        conn.close()
        flash('✅ Solicitud enviada, esperá la confirmación del médico', 'success')
        return redirect(url_for('mis_citas'))

    # Traer médicos reales de la BD
    cursor.execute("SELECT id, nombre, especialidad FROM usuarios WHERE tipo = 'medico' ORDER BY nombre")
    medicos = cursor.fetchall()
    conn.close()

    hoy = datetime.now().strftime('%Y-%m-%d')
    return render_template('agendar_cita.html', medicos=medicos, hoy=hoy)

# ==================== MIS CITAS ====================

@app.route('/mis_citas')
def mis_citas():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM citas WHERE usuario_id = ? ORDER BY fecha DESC', (session['usuario_id'],))
    citas = cursor.fetchall()
    conn.close()

    return render_template('mis_citas.html', citas=citas)

# ==================== CONSULTA ====================

@app.route('/consulta/<int:cita_id>', methods=['GET', 'POST'])
def consulta(cita_id):
    if 'usuario_id' not in session or session.get('tipo') != 'medico':
        return redirect(url_for('login'))

    conn   = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        diagnostico     = request.form['diagnostico']
        recomendaciones = request.form['recomendaciones']

        cursor.execute('''
            UPDATE citas
            SET diagnostico = ?, recomendaciones = ?, estado = 'Atendida'
            WHERE id = ?
        ''', (diagnostico, recomendaciones, cita_id))
        conn.commit()
        conn.close()

        flash('✅ Consulta guardada correctamente', 'success')
        return redirect(url_for('dashboard_medico'))

    # GET: traer cita + datos del paciente
    cursor.execute('''
        SELECT citas.*, usuarios.nombre AS nombre_paciente,
               usuarios.fecha_nacimiento, usuarios.grupo_sanguineo,
               usuarios.alergias, usuarios.celular, usuarios.ci
        FROM citas
        JOIN usuarios ON citas.usuario_id = usuarios.id
        WHERE citas.id = ?
    ''', (cita_id,))
    cita = cursor.fetchone()
    conn.close()

    if not cita:
        flash('❌ Cita no encontrada', 'error')
        return redirect(url_for('dashboard_medico'))

    return render_template('consulta.html', cita=cita)

# ==================== CALIFICAR CITA ====================

@app.route('/calificar_cita/<int:cita_id>', methods=['GET', 'POST'])
def calificar_cita(cita_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    conn   = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        calificacion = request.form.get('calificacion')
        comentario   = request.form.get('comentario', '')

        cursor.execute('''
            UPDATE citas SET calificacion = ?, comentario = ?, estado = 'Calificada'
            WHERE id = ? AND usuario_id = ?
        ''', (calificacion, comentario, cita_id, session['usuario_id']))
        conn.commit()
        conn.close()

        flash('✅ Calificación enviada, ¡gracias!', 'success')
        return redirect(url_for('mis_citas'))

    cursor.execute('SELECT * FROM citas WHERE id = ? AND usuario_id = ?',
                   (cita_id, session['usuario_id']))
    cita = cursor.fetchone()
    conn.close()

    if not cita:
        flash('❌ Cita no encontrada', 'error')
        return redirect(url_for('mis_citas'))

    return render_template('calificar_cita.html', cita=cita)

# ==================== TRÁMITES ====================

@app.route('/tramites', methods=['GET', 'POST'])
def tramites():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    conn   = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        cursor.execute('INSERT INTO tramites (usuario_id, tipo) VALUES (?, ?)',
                       (session['usuario_id'], request.form['tipo_tramite']))
        conn.commit()

    cursor.execute('SELECT * FROM tramites WHERE usuario_id = ?', (session['usuario_id'],))
    tramites = cursor.fetchall()
    conn.close()

    return render_template('tramites.html', tramites=tramites)

# ==================== OTRAS RUTAS ====================

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

    conn   = get_db()
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