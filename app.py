cd ~/kiosco_impresion
mkdir -p templates

# 1. Crear templates/index.html
cat << 'EOF' > templates/index.html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kiosco de Impresión Autoservicio</title>
    <style>
        :root { --primary: #2563eb; --primary-hover: #1d4ed8; --bg: #f8fafc; --card: #ffffff; --text: #0f172a; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }
        .navbar { max-width: 500px; margin: 0 auto 15px auto; display: flex; justify-content: space-between; align-items: center; }
        .navbar h1 { font-size: 1.2rem; margin: 0; color: #334155; }
        .admin-link { color: var(--primary); text-decoration: none; font-size: 0.9rem; font-weight: 600; padding: 6px 12px; background: #eff6ff; border-radius: 6px; }
        .container { max-width: 500px; background: var(--card); margin: 0 auto; padding: 25px; border-radius: 16px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }
        .stock-badge { background: #f1f5f9; border: 1px solid #cbd5e1; color: #334155; padding: 8px 12px; border-radius: 8px; font-size: 0.85rem; font-weight: 600; text-align: center; margin-bottom: 15px; }
        .stock-warning { background: #fef2f2; border-color: #fecaca; color: #dc2626; }
        .header-title { text-align: center; margin-bottom: 20px; }
        .header-title h2 { margin: 0; color: #1e293b; font-size: 1.5rem; }
        .header-title p { color: #64748b; font-size: 0.9rem; margin-top: 5px; }
        label { font-weight: 600; display: block; margin-top: 15px; color: #334155; font-size: 0.9rem; }
        input, select, button { width: 100%; padding: 12px; margin-top: 6px; box-sizing: border-box; border-radius: 8px; border: 1px solid #cbd5e1; font-size: 0.95rem; background: #fff; }
        .file-info { background: #eff6ff; border: 1px solid #bfdbfe; color: #1e40af; padding: 10px 14px; border-radius: 8px; font-size: 0.85rem; font-weight: 600; margin-top: 8px; display: none; }
        .range-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        button.btn-primary { background: var(--primary); color: white; border: none; font-weight: 600; margin-top: 20px; cursor: pointer; }
        button.btn-primary:hover { background: var(--primary-hover); }
        .price-card { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 18px; border-radius: 10px; margin-top: 20px; text-align: center; }
        .price-card .amount { font-size: 1.8rem; font-weight: 800; color: #166534; }
        .price-card .details { font-size: 0.9rem; color: #15803d; margin-top: 6px; font-weight: 600; }
        button.btn-pay { background: #16a34a; color: white; border: none; font-weight: 700; margin-top: 12px; cursor: pointer; font-size: 1rem; }
        button.btn-pay:hover { background: #15803d; }
    </style>
</head>
<body>
    <div class="navbar">
        <h1>🖨️ Kiosco Digital</h1>
        <a href="/admin" class="admin-link">⚙️ Panel Admin</a>
    </div>
    
    <div class="container">
        <div class="stock-badge {% if paper_stock <= 50 %}stock-warning{% endif %}">
            📄 Stock de papel en bandeja: <strong>{{ paper_stock }}</strong> hojas disponibles
        </div>

        <div class="header-title">
            <h2>Imprime tus Documentos</h2>
            <p>Configura las páginas exactas que necesitas e imprime al instante.</p>
        </div>

        <form id="uploadForm">
            <label>Selecciona Archivo (PDF, JPG, PNG):</label>
            <input type="file" id="fileInput" accept=".pdf, .jpg, .jpeg, .png" required>
            
            <div id="fileInfoBox" class="file-info"></div>

            <label>Selección de Páginas:</label>
            <select id="rangeMode">
                <option value="all">Todas las páginas</option>
                <option value="custom">Rango Personalizado (Desde / Hasta)</option>
            </select>

            <div id="customRangeGroup" class="range-grid" style="display:none; margin-top: 10px;">
                <div>
                    <label style="margin-top:0;">Desde pág:</label>
                    <input type="number" id="pageFrom" value="1" min="1">
                </div>
                <div>
                    <label style="margin-top:0;">Hasta pág:</label>
                    <input type="number" id="pageTo" value="1" min="1">
                </div>
            </div>

            <label>Cantidad de Copias:</label>
            <input type="number" id="copies" value="1" min="1" required>

            <label>Tinta / Color:</label>
            <select id="color">
                <option value="false">Blanco y Negro (${{ bw_price }} / hoja física)</option>
                <option value="true">Color (${{ color_price }} / hoja física)</option>
            </select>

            <label>Formato de Impresión:</label>
            <select id="doubleSided">
                <option value="false">Simple Faz (1 pág por hoja)</option>
                <option value="true">Doble Faz (2 págs por hoja - Ahorra hojas)</option>
            </select>

            <button type="submit" class="btn-primary" {% if paper_stock <= 0 %}disabled style="background:#94a3b8; cursor:not-allowed;"{% endif %}>
                {% if paper_stock > 0 %}📊 Calcular Precio por Hojas{% else %}❌ Sin Papel Disponible{% endif %}
            </button>
        </form>

        <div id="resultSection" style="display:none;">
            <div class="price-card">
                <div class="amount" id="priceText">$0.00 ARS</div>
                <div class="details" id="detailsText"></div>
            </div>
            <button id="payBtn" class="btn-pay">💳 Ir a Pagar</button>
        </div>
    </div>

    <script>
        let currentJobId = null;
        let maxPagesDetected = 1;

        const pageFromInput = document.getElementById('pageFrom');
        const pageToInput = document.getElementById('pageTo');

        function validateRangeInputs() {
            let valFrom = intVal(pageFromInput.value, 1);
            let valTo = intVal(pageToInput.value, maxPagesDetected);

            if (valFrom < 1) valFrom = 1;
            if (valFrom > maxPagesDetected) valFrom = maxPagesDetected;

            if (valTo < valFrom) valTo = valFrom;
            if (valTo > maxPagesDetected) valTo = maxPagesDetected;

            pageFromInput.value = valFrom;
            pageToInput.value = valTo;
        }

        function intVal(val, fallback) {
            const parsed = parseInt(val, 10);
            return isNaN(parsed) ? fallback : parsed;
        }

        pageFromInput.addEventListener('input', validateRangeInputs);
        pageToInput.addEventListener('input', validateRangeInputs);

        document.getElementById('fileInput').addEventListener('change', async (e) => {
            const file = e.target.files[0];
            const infoBox = document.getElementById('fileInfoBox');
            if (!file) {
                infoBox.style.display = 'none';
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            infoBox.innerText = '🔍 Analizando total de páginas...';
            infoBox.style.display = 'block';

            try {
                const res = await fetch('/api/analyze-file', { method: 'POST', body: formData });
                const data = await res.json();

                if (data.pages) {
                    maxPagesDetected = data.pages;
                    infoBox.innerText = `📄 Documento detectado: ${maxPagesDetected} página(s) en total (Límite permitido: 1 - ${maxPagesDetected}).`;
                    
                    pageFromInput.min = 1;
                    pageFromInput.max = maxPagesDetected;
                    pageFromInput.value = 1;

                    pageToInput.min = 1;
                    pageToInput.max = maxPagesDetected;
                    pageToInput.value = maxPagesDetected;
                }
            } catch (err) {
                infoBox.innerText = '⚠️ No se pudo analizar el total de páginas automáticamente.';
            }
        });

        document.getElementById('rangeMode').addEventListener('change', (e) => {
            const customGroup = document.getElementById('customRangeGroup');
            customGroup.style.display = (e.target.value === 'custom') ? 'grid' : 'none';
        });

        document.getElementById('uploadForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const fileInput = document.getElementById('fileInput');
            if (!fileInput.files.length) return;

            validateRangeInputs();

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('range_mode', document.getElementById('rangeMode').value);
            formData.append('page_from', pageFromInput.value);
            formData.append('page_to', pageToInput.value);
            formData.append('copies', document.getElementById('copies').value);
            formData.append('color', document.getElementById('color').value);
            formData.append('double_sided', document.getElementById('doubleSided').value);

            const res = await fetch('/api/upload', { method: 'POST', body: formData });
            const data = await res.json();

            if (data.job_id) {
                currentJobId = data.job_id;
                document.getElementById('priceText').innerText = `$${data.total_price} ARS`;
                document.getElementById('detailsText').innerText = 
                    `📄 ${data.sheets_count} hoja(s) física(s) ocupada(s)\n(${data.printed_pages} págs impresas × ${document.getElementById('copies').value} copia/s)`;
                document.getElementById('resultSection').style.display = 'block';
            } else {
                alert(data.error || 'Error al procesar la selección');
            }
        });

        document.getElementById('payBtn').addEventListener('click', async () => {
            const res = await fetch(`/api/create-payment/${currentJobId}`, { method: 'POST' });
            const data = await res.json();
            if (data.checkout_url) {
                window.location.href = data.checkout_url;
            }
        });
    </script>
</body>
</html>
EOF

# 2. Crear templates/admin.html
cat << 'EOF' > templates/admin.html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Panel de Control - Kiosco Admin</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f1f5f9; color: #0f172a; margin: 0; padding: 20px; }
        .top-bar { max-width: 1000px; margin: 0 auto 20px auto; display: flex; justify-content: space-between; align-items: center; }
        .top-bar h2 { margin: 0; color: #1e293b; }
        .top-actions { display: flex; gap: 10px; }
        .btn-back { background: #0f172a; color: white; text-decoration: none; padding: 8px 16px; border-radius: 6px; font-size: 0.9rem; font-weight: 600; }
        .btn-logout { background: #ef4444; color: white; text-decoration: none; padding: 8px 16px; border-radius: 6px; font-size: 0.9rem; font-weight: 600; }
        .btn-logout:hover { background: #dc2626; }
        .container { max-width: 1000px; margin: 0 auto; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 25px; }
        .stat-card { background: white; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; }
        .stat-card .label { font-size: 0.85rem; color: #64748b; font-weight: 600; text-transform: uppercase; }
        .stat-card .value { font-size: 1.8rem; font-weight: 800; color: #0f172a; margin-top: 5px; }
        
        .settings-card { background: white; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 25px; }
        .settings-card h3 { margin-top: 0; margin-bottom: 15px; color: #1e293b; font-size: 1.1rem; }
        .settings-form { display: flex; gap: 15px; align-items: flex-end; flex-wrap: wrap; }
        .form-group { flex: 1; min-width: 150px; }
        .form-group label { display: block; font-size: 0.85rem; font-weight: 600; color: #475569; margin-bottom: 6px; }
        .form-group input { width: 100%; padding: 10px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 0.95rem; box-sizing: border-box; }
        .btn-save { background: #2563eb; color: white; border: none; padding: 11px 20px; border-radius: 8px; font-weight: 600; cursor: pointer; }
        .btn-save:hover { background: #1d4ed8; }

        .table-card { background: white; border-radius: 12px; border: 1px solid #e2e8f0; overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem; }
        th { background: #f8fafc; padding: 14px 16px; color: #475569; font-weight: 700; border-bottom: 1px solid #e2e8f0; }
        td { padding: 14px 16px; border-bottom: 1px solid #f1f5f9; }
        .badge { padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; display: inline-block; }
        .badge-paid { background: #dcfce7; color: #15803d; }
        .badge-pending { background: #fef3c7; color: #b45309; }
        .filename { font-family: monospace; font-size: 0.85rem; color: #334155; }
    </style>
</head>
<body>
    <div class="top-bar">
        <h2>📊 Panel de Administración</h2>
        <div class="top-actions">
            <a href="/" class="btn-back">⬅️ Kiosco</a>
            <a href="/logout" class="btn-logout">🚪 Salir</a>
        </div>
    </div>

    <div class="container">
        <div class="stats-grid">
            <div class="stat-card">
                <div class="label">Total Recaudado</div>
                <div class="value" style="color: #16a34a;">${{ "%.2f"|format(total_earned) }}</div>
            </div>
            <div class="stat-card">
                <div class="label">Stock de Hojas</div>
                <div class="value" style="color: {% if paper_stock <= 100 %}#dc2626{% else %}#2563eb{% endif %};">{{ paper_stock }}</div>
            </div>
            <div class="stat-card">
                <div class="label">Trabajos Pagados</div>
                <div class="value">{{ paid_jobs_count }}</div>
            </div>
            <div class="stat-card">
                <div class="label">Hojas Impresas</div>
                <div class="value">{{ total_sheets_printed }}</div>
            </div>
        </div>

        <div class="settings-card">
            <h3>⚙️ Tarifas y Recarga de Papel</h3>
            <form action="/admin/update-settings" method="POST" class="settings-form">
                <div class="form-group">
                    <label>Blanco y Negro ($ ARS):</label>
                    <input type="number" step="0.01" name="bw_price" value="{{ bw_price }}" required>
                </div>
                <div class="form-group">
                    <label>Color ($ ARS):</label>
                    <input type="number" step="0.01" name="color_price" value="{{ color_price }}" required>
                </div>
                <div class="form-group">
                    <label>Stock de Papel (Hojas):</label>
                    <input type="number" name="paper_stock" value="{{ paper_stock }}" min="0" required>
                </div>
                <button type="submit" class="btn-save">💾 Guardar Cambios</button>
            </form>
        </div>

        <div class="table-card">
            <table>
                <thead>
                    <tr>
                        <th># Orden</th>
                        <th>Archivo</th>
                        <th>Rango Págs</th>
                        <th>Hojas Físicas</th>
                        <th>Detalles</th>
                        <th>Monto</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody>
                    {% for job in jobs %}
                    <tr>
                        <td><strong>#{{ job[0] }}</strong></td>
                        <td class="filename">{{ job[1].replace('uploads/', '') }}</td>
                        <td>Págs {{ job[3] }} a {{ job[4] }}</td>
                        <td><strong>{{ job[5] }} hojas</strong> ({{ job[6] }} cop.)</td>
                        <td>
                            <small style="color:#64748b;">
                                {{ 'Color' if job[8] else 'B&N' }} | {{ 'Doble Faz' if job[7] else 'Simple Faz' }}
                            </small>
                        </td>
                        <td><strong>${{ "%.2f"|format(job[9]) }}</strong></td>
                        <td>
                            {% if job[10] == 'paid' %}
                                <span class="badge badge-paid">PAGADO</span>
                            {% else %}
                                <span class="badge badge-pending">PENDIENTE</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="7" style="text-align: center; color: #94a3b8; padding: 30px;">
                            No hay registros de impresiones aún.
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
EOF

# 3. Crear app.py
cat << 'EOF' > app.py
import os
import sqlite3
import uuid
import math
import requests
from flask import Flask, request, jsonify, render_template, redirect, session
from pypdf import PdfReader

app = Flask(__name__)
app.secret_key = 'kiosco_secret_key_thiago28'
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS print_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL,
            file_type TEXT NOT NULL,
            page_count INTEGER NOT NULL,
            page_from INTEGER DEFAULT 1,
            page_to INTEGER DEFAULT 1,
            sheets_count INTEGER DEFAULT 1,
            copies INTEGER NOT NULL,
            is_double_sided BOOLEAN NOT NULL,
            is_color BOOLEAN NOT NULL,
            total_price REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            payment_token TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value REAL NOT NULL
        )
    ''')

    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('bw_price', 50.0)")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('color_price', 100.0)")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('paper_stock', 50000.0)")

    conn.commit()
    conn.close()

def get_settings():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    rows = cursor.fetchall()
    conn.close()
    
    settings_dict = {row[0]: row[1] for row in rows}
    return (
        settings_dict.get('bw_price', 50.0),
        settings_dict.get('color_price', 100.0),
        int(settings_dict.get('paper_stock', 50000))
    )

def get_file_page_count(file_stream, filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext == 'pdf':
        try:
            reader = PdfReader(file_stream)
            return len(reader.pages)
        except Exception as e:
            print(f"Error al leer PDF: {e}")
            return 1
    return 1

# BLOQUEO Y PROTECCIÓN GLOBAL
@app.before_request
def protect_admin_routes():
    if request.path.startswith('/admin') and not session.get('admin_logged_in'):
        return redirect('/login')

# RUTAS DE AUTENTICACIÓN
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == 'admin' and password == 'Thiago28':
            session['admin_logged_in'] = True
            return redirect('/admin')
        else:
            error = 'Usuario o contraseña incorrectos'

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# RUTAS DE INTERFAZ (HTML)
@app.route('/')
def index():
    bw_price, color_price, paper_stock = get_settings()
    return render_template('index.html', bw_price=bw_price, color_price=color_price, paper_stock=paper_stock)

@app.route('/admin')
def admin_panel():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT SUM(total_price) FROM print_jobs WHERE status = 'paid'")
    total_earned = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT COUNT(*) FROM print_jobs WHERE status = 'paid'")
    paid_jobs_count = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM print_jobs WHERE status = 'pending'")
    pending_jobs_count = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(sheets_count) FROM print_jobs WHERE status = 'paid'")
    total_sheets_printed = cursor.fetchone()[0] or 0

    cursor.execute('''
        SELECT id, file_path, file_type, page_from, page_to, sheets_count, copies, is_double_sided, is_color, total_price, status, created_at
        FROM print_jobs ORDER BY id DESC
    ''')
    jobs = cursor.fetchall()
    conn.close()

    bw_price, color_price, paper_stock = get_settings()

    return render_template(
        'admin.html',
        total_earned=total_earned,
        paid_jobs_count=paid_jobs_count,
        pending_jobs_count=pending_jobs_count,
        total_sheets_printed=total_sheets_printed,
        jobs=jobs,
        bw_price=bw_price,
        color_price=color_price,
        paper_stock=paper_stock
    )

@app.route('/admin/update-settings', methods=['POST'])
def update_settings():
    try:
        new_bw = float(request.form.get('bw_price', 50.0))
        new_color = float(request.form.get('color_price', 100.0))
        new_stock = int(request.form.get('paper_stock', 50000))

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE settings SET value = ? WHERE key = 'bw_price'", (new_bw,))
        cursor.execute("UPDATE settings SET value = ? WHERE key = 'color_price'", (new_color,))
        cursor.execute("UPDATE settings SET value = ? WHERE key = 'paper_stock'", (new_stock,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error actualizando configuración: {e}")

    return redirect('/admin')

# API Y PROCESAMIENTO
@app.route('/api/analyze-file', methods=['POST'])
def analyze_file():
    if 'file' not in request.files:
        return jsonify({"error": "No hay archivo"}), 400

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({"error": "Formato no permitido"}), 400

    pages = get_file_page_count(file.stream, file.filename)
    return jsonify({"pages": pages})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No se seleccionó ningún archivo"}), 400

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({"error": "Formato no permitido (Usa PDF, JPG o PNG)"}), 400

    copies = int(request.form.get('copies', 1))
    double_sided = request.form.get('double_sided') == 'true'
    color = request.form.get('color') == 'true'
    range_mode = request.form.get('range_mode', 'all')

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)

    ext = file.filename.rsplit('.', 1)[1].lower()
    
    with open(file_path, 'rb') as f:
        total_pdf_pages = get_file_page_count(f, file.filename)

    if range_mode == 'custom' and ext == 'pdf':
        try:
            page_from = int(request.form.get('page_from', 1))
            page_to = int(request.form.get('page_to', total_pdf_pages))
            
            if page_from < 1 or page_to > total_pdf_pages or page_from > page_to:
                return jsonify({"error": f"El rango ingresado debe estar entre la página 1 y la {total_pdf_pages}"}), 400

        except ValueError:
            page_from, page_to = 1, total_pdf_pages
    else:
        page_from, page_to = 1, total_pdf_pages

    printed_pages = (page_to - page_from + 1)

    if double_sided and ext == 'pdf':
        sheets_per_copy = math.ceil(printed_pages / 2.0)
    else:
        sheets_per_copy = printed_pages

    total_sheets_count = sheets_per_copy * copies

    # VALIDACIÓN DE STOCK DE PAPEL
    bw_price, color_price, paper_stock = get_settings()

    if paper_stock <= 0:
        return jsonify({"error": "El kiosco se ha quedado sin papel. Por favor, avisa al personal para recargar."}), 400

    if total_sheets_count > paper_stock:
        return jsonify({
            "error": f"Stock de papel insuficiente. El kiosco dispone de {paper_stock} hoja(s) y tu pedido requiere {total_sheets_count} hoja(s)."
        }), 400

    price_per_sheet = color_price if color else bw_price
    total_price = total_sheets_count * price_per_sheet

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO print_jobs (file_path, file_type, page_count, page_from, page_to, sheets_count, copies, is_double_sided, is_color, total_price, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
    ''', (file_path, ext, printed_pages, page_from, page_to, total_sheets_count, copies, double_sided, color, total_price))

    job_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return jsonify({
        "job_id": job_id, 
        "total_price": round(total_price, 2), 
        "printed_pages": printed_pages,
        "sheets_count": total_sheets_count
    })

@app.route('/api/create-payment/<int:job_id>', methods=['POST'])
def create_payment(job_id):
    payment_token = str(uuid.uuid4())

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE print_jobs SET payment_token = ? WHERE id = ?", (payment_token, job_id))
    conn.commit()
    conn.close()

    return jsonify({"checkout_url": f"/mock-gateway/checkout/{payment_token}"})

@app.route('/mock-gateway/checkout/<payment_token>')
def mock_checkout(payment_token):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, total_price FROM print_jobs WHERE payment_token = ?", (payment_token,))
    job = cursor.fetchone()
    conn.close()

    if not job:
        return "Transacción no encontrada", 404

    job_id, total_price = job

    return f'''
        <div style="font-family:sans-serif; max-width:400px; margin:50px auto; padding:25px; border-radius:12px; box-shadow:0 4px 20px rgba(0,0,0,0.1); text-align:center;">
            <h3>💳 Pasarela de Pago</h3>
            <p>Orden #{job_id}</p>
            <h1 style="color:#16a34a;">${total_price:.2f} ARS</h1>
            <form action="/mock-gateway/process/{payment_token}" method="POST">
                <button type="submit" style="background:#2563eb; color:white; border:none; padding:14px; width:100%; font-size:16px; font-weight:bold; border-radius:8px; cursor:pointer;">Pagar Ahora</button>
            </form>
        </div>
    '''

@app.route('/mock-gateway/process/<payment_token>', methods=['POST'])
def process_mock_payment(payment_token):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, total_price FROM print_jobs WHERE payment_token = ?", (payment_token,))
    job = cursor.fetchone()
    conn.close()

    if not job:
        return "Error en el pago", 400

    job_id, total_price = job

    webhook_url = request.host_url.rstrip('/') + "/webhook/payment-notification"
    webhook_payload = {
        "event": "payment.approved",
        "job_id": job_id,
        "payment_token": payment_token,
        "amount": total_price,
        "status": "approved"
    }

    try:
        requests.post(webhook_url, json=webhook_payload, timeout=5)
    except Exception as e:
        print(f"Error en Webhook: {e}")

    return redirect(f"/success/{job_id}")

@app.route('/webhook/payment-notification', methods=['POST'])
def payment_webhook():
    data = request.json
    if data and data.get("event") == "payment.approved":
        job_id = data.get("job_id")
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT file_path, copies, total_price, page_from, page_to, sheets_count, status FROM print_jobs WHERE id = ?", (job_id,))
        job = cursor.fetchone()

        if job and job[6] != 'paid':
            file_path, copies, total_price, page_from, page_to, sheets_count, _ = job
            
            # Cambiar estado a PAGADO
            cursor.execute("UPDATE print_jobs SET status = 'paid' WHERE id = ?", (job_id,))
            
            # DESCONTAR HOJAS DEL STOCK GENERAL
            cursor.execute("UPDATE settings SET value = MAX(0, value - ?) WHERE key = 'paper_stock'", (sheets_count,))
            
            conn.commit()
            conn.close()

            print("\n" + "="*60)
            print("🔔 [WEBHOOK RECIBIDO] ¡Notificación oficial de pago!")
            print(f"✅ Estado: APROBADO | Orden #{job_id}")
            print(f"💰 Monto Acreditado: ${total_price} ARS")
            print(f"📄 Rango impreso: Páginas {page_from} a {page_to}")
            print(f"🖨️ [SIMULADOR DE IMPRESORA] Imprimiendo {sheets_count} hojas físicas de:")
            print(f"   --> Archivo: {file_path}")
            print("="*60 + "\n")

    return jsonify({"received": True}), 200

@app.route('/success/<int:job_id>')
def success_page(job_id):
    return f'''
        <div style="font-family:sans-serif; text-align:center; padding:50px;">
            <h1>¡Pago Confirmado! 🎉</h1>
            <p>Tu orden de impresión <strong>#{job_id}</strong> fue procesada.</p>
            <a href="/">Imprimir Otro Archivo</a> | <a href="/admin">Ir al Panel Admin</a>
        </div>
    '''

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
EOF
