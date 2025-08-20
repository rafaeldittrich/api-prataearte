#!/bin/bash

# Script para configurar Cloud Scheduler para execução a cada hora
# Execute: chmod +x setup-cloud-scheduler.sh && ./setup-cloud-scheduler.sh

set -e

# Configurações
PROJECT_ID="datalake-betminds"
REGION="us-central1"
SERVICE_NAME="linx-orders-importer"
SCHEDULER_NAME="import-linx-orders-hourly"
SCHEDULE="0 * * * *"  # A cada hora (formato cron)
TIMEZONE="America/Sao_Paulo"

echo "⏰ Configurando Cloud Scheduler para execução a cada hora..."

# 1. Verifica se o gcloud está configurado
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Erro: Faça login no Google Cloud primeiro:"
    echo "   gcloud auth login"
    exit 1
fi

# 2. Define o projeto
echo "📋 Definindo projeto: $PROJECT_ID"
gcloud config set project $PROJECT_ID

# 3. Habilita a API do Cloud Scheduler
echo "🔧 Habilitando Cloud Scheduler API..."
gcloud services enable cloudscheduler.googleapis.com

# 4. Obtém a URL do Cloud Run
echo "🔍 Obtendo URL do Cloud Run..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")

if [ -z "$SERVICE_URL" ]; then
    echo "❌ Erro: Não foi possível obter a URL do Cloud Run"
    echo "   Certifique-se de que o serviço foi criado primeiro"
    exit 1
fi

echo "✅ URL do serviço: $SERVICE_URL"

# 5. Cria o Cloud Scheduler
echo "⏰ Criando Cloud Scheduler: $SCHEDULER_NAME"
gcloud scheduler jobs create http $SCHEDULER_NAME \
    --location=$REGION \
    --schedule="$SCHEDULE" \
    --uri="$SERVICE_URL/import" \
    --http-method=POST \
    --time-zone="$TIMEZONE" \
    --description="Executa importação de pedidos LINX a cada hora (equivalente ao --only-new)" \
    --headers="Content-Type=application/json" \
    --message-body='{"trigger": "scheduled", "mode": "only_new"}'

echo "✅ Cloud Scheduler criado com sucesso!"
echo ""
echo "📋 Configurações:"
echo "   - Nome: $SCHEDULER_NAME"
echo "   - Agendamento: $SCHEDULE (a cada hora)"
echo "   - Fuso horário: $TIMEZONE"
echo "   - URL: $SERVICE_URL/import"
echo "   - Modo: --only-new (apenas pedidos novos)"
echo ""
echo "🕐 Execução programada:"
echo "   - 00:00, 01:00, 02:00, 03:00, 04:00, 05:00"
echo "   - 06:00, 07:00, 08:00, 09:00, 10:00, 11:00"
echo "   - 12:00, 13:00, 14:00, 15:00, 16:00, 17:00"
echo "   - 18:00, 19:00, 20:00, 21:00, 22:00, 23:00"
echo ""
echo "🔧 Comandos úteis:"
echo "   - Listar jobs: gcloud scheduler jobs list --location=$REGION"
echo "   - Ver detalhes: gcloud scheduler jobs describe $SCHEDULER_NAME --location=$REGION"
echo "   - Executar manualmente: gcloud scheduler jobs run $SCHEDULER_NAME --location=$REGION"
echo "   - Pausar: gcloud scheduler jobs pause $SCHEDULER_NAME --location=$REGION"
echo "   - Resumir: gcloud scheduler jobs resume $SCHEDULER_NAME --location=$REGION"
echo "   - Deletar: gcloud scheduler jobs delete $SCHEDULER_NAME --location=$REGION"
echo ""
echo "🎯 Esta configuração é equivalente a executar:"
echo "   python3 src/import_historical_orders.py --only-new"
echo "   A cada hora, automaticamente na nuvem!"
echo ""
echo "🚀 Sua máquina pode ficar desligada que a importação continuará funcionando!"
