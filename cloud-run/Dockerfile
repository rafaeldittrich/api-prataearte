# Dockerfile para Cloud Run - Importação LINX
FROM python:3.11-slim

# Define variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho
WORKDIR /app

# Copia os arquivos de dependências
COPY requirements.txt .

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY src/ ./src/
COPY config/ ./config/

# Define o usuário não-root para segurança
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Expõe a porta (Cloud Run usa PORT via variável de ambiente)
EXPOSE 8080

# Comando para executar a aplicação
CMD ["python", "src/main_cloud_run.py"]
