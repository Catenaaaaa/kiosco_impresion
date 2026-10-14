import os
import sqlite3
import uuid
import math
import requests
from flask import Flask, request, jsonify, render_template, redirect
from pypdf import PdfReader

app = Flask(__name__)
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
    conn.commit()
    conn.close()

def get_file_page_count(file_path):
    ext = file_path.rsplit('.', 1)[1].lower()
    if ext == 'pdf':
        try:
            reader = PdfReader(file_path)
            return len(reader.pages)
        except Exception as e:
            print(f"Error al leer PDF: {e}")
            return 1
    return 1

# ==========================================
# RUTAS DE INTERFAZ (HTML)
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')

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

    return render_template(
        'admin.html',
        total_earned=total_earned,
        paid_jobs_count=paid_jobs_count,
        pending_jobs_count=pending_jobs_count,
        total_sheets_printed=total_sheets_printed,
        jobs=jobs
    )

# ==========================================
# API Y PROCESAMIENTO
# ==========================================
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
    total_pdf_pages = get_file_page_count(file_path)

    if range_mode == 'custom' and ext == 'pdf':
        try:
            page_from = int(request.form.get('page_from', 1))
            page_to = int(request.form.get('page_to', total_pdf_pages))
            page_from = max(1, min(page_from, total_pdf_pages))
            page_to = max(page_from, min(page_to, total_pdf_pages))
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

    price_per_sheet = 100 if color else 50
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
