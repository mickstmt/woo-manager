# WooCommerce Flask API

API personalizada para interactuar directamente con la base de datos de WooCommerce, evitando los tiempos de espera de la REST API.

## Requisitos
- Python 3.8+
- MySQL/MariaDB (base de datos de WooCommerce)

## Configuración
1. Crea un archivo `.env` basado en `.env.example`
2. Instala dependencias: `pip install -r requirements.txt`
3. Ejecuta: `python app.py`

## Variables de entorno
- `PORT`: puerto (por defecto 5000)
- `DB_HOST`: host de la base de datos
- `DB_USER`: usuario de la base de datos
- `DB_PASS`: contraseña
- `DB_NAME`: nombre de la base de datos