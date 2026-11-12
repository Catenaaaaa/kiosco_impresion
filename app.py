import os
import io
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
            copies INTEGER DEFAULT 1,
            is_double_sided BOOLEAN DEFAULT 0,
            is_color BOOLEAN DEFAULT 0,
            total_price REAL DEFAULT 0.0,
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
            stream_bytes = file_stream.read()
            file_stream.seek(0)
            reader = PdfReader(io.BytesIO(stream_bytes))
            return len(reader.pages)
        except Exception as e:
            print(f"Error al leer PDF: {e}")
            return 1
    return 1

# ==========================================
# PROTECCIÓN Y AUTENTICACIÓN
# ==========================================
@app.before_request
def protect_admin_routes():
    if request.path.startswith('/admin') and not session.get('admin_logged_in'):
        return redirect('/login')

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

# ==========================================
# VISTAS PRINCIPALES
# ==========================================
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

# ==========================================
# API Y PROCESAMIENTO
# ==========================================
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

    try:
        copies = int(request.form.get('copies', 1))
        if copies < 1:
            copies = 1
    except (ValueError, TypeError):
        copies = 1

    double_sided = request.form.get('double_sided') == 'true'
    color = request.form.get('color') == 'true'
    range_mode = request.form.get('range_mode', 'all')

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)

    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    
    with open(file_path, 'rb') as f:
        total_pdf_pages = get_file_page_count(f, file.filename)

    if range_mode == 'custom' and ext == 'pdf':
        try:
            page_from = int(request.form.get('page_from', 1))
            page_to = int(request.form.get('page_to', total_pdf_pages))
            
            page_from = max(1, min(page_from, total_pdf_pages))
            page_to = max(page_from, min(page_to, total_pdf_pages))
        except (ValueError, TypeError):
            page_from, page_to = 1, total_pdf_pages
    else:
        page_from, page_to = 1, total_pdf_pages

    printed_pages = (page_to - page_from + 1)

    if double_sided and ext == 'pdf':
        sheets_per_copy = math.ceil(printed_pages / 2.0)
    else:
        sheets_per_copy = printed_pages

    total_sheets_count = sheets_per_copy * copies

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
            
            cursor.execute("UPDATE print_jobs SET status = 'paid' WHERE id = ?", (job_id,))
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
