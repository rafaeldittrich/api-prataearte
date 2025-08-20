# 🚀 LINX Orders Importer - Cloud Run + GitHub

Sistema automatizado para importação de pedidos LINX para BigQuery usando Google Cloud Run e GitHub Actions.

## 📋 Visão Geral

Este projeto implementa a importação automática de pedidos LINX para BigQuery usando:
- **Google Cloud Run** - Container Docker escalável
- **GitHub Actions** - Deploy automático
- **Cloud Scheduler** - Execução a cada hora
- **BigQuery** - Armazenamento de dados

## 🎯 Funcionalidades

- ✅ **Importação automática** a cada hora
- ✅ **Comportamento `--only-new`** (sem duplicatas)
- ✅ **Escalabilidade automática** (0-10 instâncias)
- ✅ **Deploy automático** via GitHub
- ✅ **Health checks** e monitoramento
- ✅ **Logs estruturados** para debugging

## 🏗️ Arquitetura

```
GitHub Push → GitHub Actions → Build Docker → Deploy Cloud Run → Cloud Scheduler → HTTP POST → Importação
```

## 📁 Estrutura do Projeto

```
📁 api-prataearte/
├── 📁 src/
│   ├── main_cloud_run.py     # Entry point para Cloud Run
│   ├── import_historical_orders.py  # Lógica de importação
│   ├── bigquery_client.py    # Cliente BigQuery
│   └── linx_api.py          # Cliente API LINX
├── 📁 cloud-run/
│   └── Dockerfile           # Container Docker
├── 📁 .github/workflows/
│   └── deploy.yml           # GitHub Actions
├── 📁 config/
│   └── config.yaml          # Configurações
└── setup-cloud-scheduler.sh # Script de configuração
```

## 🚀 Deploy

### 1. Configurar GitHub Secrets

No seu repositório GitHub, configure os seguintes secrets:

```
GCP_SA_KEY          # Chave JSON da Service Account do Google Cloud
LINX_API_BASE_URL   # URL da API LINX
LINX_API_USERNAME   # Usuário da API LINX
LINX_API_PASSWORD   # Senha da API LINX
```

### 2. Fazer Push para GitHub

```bash
git add .
git commit -m "feat: implement Cloud Run deployment"
git push origin main
```

### 3. Verificar Deploy

O GitHub Actions irá:
1. Buildar a imagem Docker
2. Fazer push para Google Container Registry
3. Deployar no Cloud Run
4. Retornar a URL do serviço

### 4. Configurar Cloud Scheduler

```bash
chmod +x setup-cloud-scheduler.sh
./setup-cloud-scheduler.sh
```

## 🔧 Endpoints

### Health Check
```bash
GET /
# Retorna status do serviço
```

### Importação Completa
```bash
POST /import
# Equivale a: python3 src/import_historical_orders.py --only-new
```

### Importação de Teste
```bash
POST /import-test
{
  "max_orders": 5
}
# Importa máximo de 5 pedidos para teste
```

## ⏰ Agendamento

O Cloud Scheduler executa automaticamente:
- **Frequência**: A cada hora
- **Horários**: 00:00, 01:00, 02:00... 23:00
- **Fuso**: America/Sao_Paulo
- **Endpoint**: `/import`

## 📊 Monitoramento

### Logs do Cloud Run
```bash
gcloud run services logs read linx-orders-importer --region=us-central1
```

### Logs em tempo real
```bash
gcloud run services logs tail linx-orders-importer --region=us-central1
```

### Status do serviço
```bash
gcloud run services describe linx-orders-importer --region=us-central1
```

## 🔒 Segurança

- ✅ **Service Account** dedicada para Cloud Run
- ✅ **Variáveis de ambiente** para credenciais
- ✅ **Container não-root** para execução
- ✅ **HTTPS obrigatório** para comunicação

## 💰 Custos

### Cloud Run
- **Execução**: $0.00002400 por 100ms
- **CPU**: $0.00002400 por 100ms
- **Memória**: $0.00000250 por GB-100ms

### Cloud Scheduler
- **Jobs**: $0.10 por mês por job

### BigQuery
- **Storage**: $0.02 por GB por mês
- **Queries**: $5.00 por TB processado

## 🧪 Testes Locais

### Executar localmente
```bash
cd cloud-run
python3 ../src/main_cloud_run.py
```

### Testar endpoints
```bash
# Health check
curl http://localhost:8080/

# Importação de teste
curl -X POST http://localhost:8080/import-test \
  -H "Content-Type: application/json" \
  -d '{"max_orders": 3}'
```

## 🔄 Atualizações

Para atualizar o serviço:
1. Faça as mudanças no código
2. Commit e push para GitHub
3. GitHub Actions fará deploy automático
4. Serviço será atualizado sem downtime

## 🚨 Troubleshooting

### Erro de autenticação
- Verifique se `GCP_SA_KEY` está configurado
- Confirme se a Service Account tem permissões

### Erro de deploy
- Verifique os logs do GitHub Actions
- Confirme se o Dockerfile está correto

### Erro de execução
- Verifique os logs do Cloud Run
- Confirme se as variáveis de ambiente estão corretas

## 📞 Suporte

- **Logs**: Cloud Run Logs
- **Métricas**: Cloud Run Metrics
- **Deploy**: GitHub Actions
- **Agendamento**: Cloud Scheduler

## 📝 Licença

Este projeto é privado e confidencial.
# Trigger new deploy
