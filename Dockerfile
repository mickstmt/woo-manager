# 1. Usamos una imagen oficial de Python como base
FROM python:3.10-slim

# 2. Establecemos el directorio de trabajo dentro del contenedor
WORKDIR /app

# 3. Copiamos e instalamos las dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copiamos el resto del código de la aplicación
COPY . .

# 5. Exponemos el puerto en el que correrá la aplicación
EXPOSE 8000

# 6. El comando para iniciar la aplicación usando Gunicorn
#    (Asegúrate de que tu archivo se llame 'run.py' y tu app 'app')
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "run:app"]