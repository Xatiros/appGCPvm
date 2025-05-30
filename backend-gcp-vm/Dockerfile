# Usa una imagen base de Python más estable
FROM python:3.10-slim-buster
# O podrías intentar: FROM python:3.9-slim-buster

# Establece el directorio de trabajo en /app
WORKDIR /app

# Copia los archivos de requerimientos y Python
COPY requirements.txt .
COPY main.py .

# Instala las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Cloud Run inyecta la variable de entorno PORT. Uvicorn debe escuchar en ella.
ENV PORT 8080
EXPOSE 8080

# Comando para iniciar la aplicación usando Uvicorn
CMD uvicorn main:app --host 0.0.0.0 --port $PORT