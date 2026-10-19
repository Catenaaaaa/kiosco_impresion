🖨️ Kiosco de Impresión

📌 Descripción

Kiosco de Impresión es una aplicación web desarrollada con Python y Flask que permite gestionar pedidos de impresión de documentos e imágenes. El sistema permite cargar archivos, seleccionar opciones de impresión y calcular el precio del servicio.

También cuenta con un panel de administración para gestionar los pedidos y modificar los precios.

🚀 Funcionalidades

- 📄 Carga de archivos PDF e imágenes.
- 🖨️ Configuración de opciones de impresión.
- 📑 Selección de páginas y cantidad de copias.
- 🎨 Impresión en blanco y negro o color.
- 📃 Opción de impresión doble faz.
- 💰 Cálculo automático del precio.
- 🔐 Inicio de sesión para el administrador.
- ⚙️ Panel de administración para modificar precios.
- 💳 Sistema de pago de demostración.
- 🗄️ Base de datos para guardar los pedidos y la configuración.

🛠️ Tecnologías utilizadas

- Python: lenguaje principal del proyecto.
- Flask: framework para desarrollar la aplicación web.
- SQLite: base de datos.
- HTML: estructura de las páginas.
- Requests: comunicación con servicios externos.
- pypdf: lectura y procesamiento de archivos PDF.

📂 Estructura del proyecto

kiosco_impresion/
├── app.py
├── init_db.py
├── database.db
├── templates/
│   ├── index.html
│   ├── admin.html
│   └── login.html
└── uploads/

- "app.py": contiene la lógica principal de la aplicación.
- "init_db.py": inicializa la base de datos.
- "database.db": almacena los datos del sistema.
- "templates/": contiene las páginas HTML.
- "uploads/": guarda los archivos cargados.

💻 Instalación y ejecución

1. Instalar Python en la computadora.
2. Descargar o clonar el repositorio.
3. Instalar las dependencias necesarias:

pip install flask requests pypdf

4. Iniciar la aplicación:

python app.py

5. Abrir el navegador y entrar a:

http://127.0.0.1:5000

🔒 Seguridad

Antes de publicar el proyecto o utilizarlo en producción, se recomienda cambiar las credenciales de administrador, proteger la clave secreta de Flask y configurar correctamente el sistema de pagos.

🎯 Objetivo del proyecto

El objetivo es facilitar la gestión de un kiosco de impresión mediante una plataforma web sencilla, práctica y organizada.

📌 Estado del proyecto

Proyecto en desarrollo con fines educativos y de práctica en programación web.

👨‍💻 Autor

grupo Proa
