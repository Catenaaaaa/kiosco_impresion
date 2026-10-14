import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Crear tabla de trabajos de impresión
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS print_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL,
            file_type TEXT NOT NULL,
            page_count INTEGER NOT NULL,
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
    print("✅ Base de datos creada con éxito.")

if __name__ == '__main__':
    init_db()

