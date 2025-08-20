# ⏰ Importação Horária - Google Cloud Functions

Este guia explica como implementar a execução automática do script `import_historical_orders.py --only-new` a cada hora na nuvem do Google Cloud.

## 🎯 O que esta solução faz

**Equivale a executar a cada hora:**
```bash
python3 src/import_historical_orders.py --only-new
```

**Mas rodando automaticamente na nuvem, sem precisar da sua máquina ligada!**

## 🏗️ Arquitetura

```
Cloud Scheduler (a cada hora)
         ↓
Cloud Function (import-linx-orders-hourly)
         ↓
    LINX API ←→ BigQuery
```

## 🚀 Implementação em 3 Passos

### Passo 1: Deploy da Cloud Function

```bash
# Torne o script executável
chmod +x deploy-hourly-import.sh

# Execute o deploy
./deploy-hourly-import.sh
```

**O que acontece:**
- Cria a Cloud Function `import-linx-orders-hourly`
- Configura memória (512MB) e timeout (9 minutos)
- Define variáveis de ambiente básicas

### Passo 2: Configurar Credenciais LINX

```bash
# Torne o script executável
chmod +x config-credentials-hourly.sh

# Execute a configuração
./config-credentials-hourly.sh
```

**O script solicitará:**
- URL da API LINX
- Usuário da API
- Senha da API

### Passo 3: Configurar Execução Automática

```bash
# Torne o script executável
chmod +x setup-hourly-scheduler.sh

# Execute a configuração
./setup-hourly-scheduler.sh
```

**O que acontece:**
- Cria um Cloud Scheduler job
- Configura execução a cada hora
- Define fuso horário de São Paulo

## 📁 Arquivos Criados

```
src/
├── cloud_function_import.py      # Código da Cloud Function (equivalente ao --only-new)
├── bigquery_client.py            # Cliente BigQuery (não usado na cloud)
└── import_historical_orders.py   # Script local original

deploy-hourly-import.sh           # Script de deploy
config-credentials-hourly.sh      # Configuração de credenciais
setup-hourly-scheduler.sh         # Configuração do agendador
requirements-cloud-function.txt    # Dependências Python
```

## 🔧 Como Funciona

### 1. **Comportamento --only-new**
- A função SEMPRE verifica a data do último pedido importado
- Busca apenas pedidos criados após essa data
- Evita duplicatas automaticamente
- Pula pedidos que já existem

### 2. **Execução Automática**
- **00:00** - Executa importação
- **01:00** - Executa importação
- **02:00** - Executa importação
- **...** - Continua a cada hora
- **23:00** - Última execução do dia

### 3. **Processamento Inteligente**
- Verifica se `order_id` já existe
- Verifica se `order_number` já existe
- Importa apenas pedidos novos
- Logs detalhados de cada execução

## 📊 Monitoramento

### Ver Logs da Execução

```bash
# Últimas 50 execuções
gcloud functions logs read import-linx-orders-hourly --region=us-central1 --limit=50

# Logs em tempo real
gcloud functions logs tail import-linx-orders-hourly --region=us-central1
```

### Ver Status do Agendador

```bash
# Listar todos os jobs
gcloud scheduler jobs list

# Detalhes do job horário
gcloud scheduler jobs describe import-linx-orders-hourly

# Executar manualmente (para testes)
gcloud scheduler jobs run import-linx-orders-hourly
```

## 🧪 Testando

### Teste Manual da Função

```bash
# Obter URL da função
FUNCTION_URL=$(gcloud functions describe import-linx-orders-hourly --region=us-central1 --format='value(httpsTrigger.url)')

# Testar com curl
curl -X POST $FUNCTION_URL
```

### Verificar BigQuery

```sql
-- Verificar últimos pedidos importados
SELECT 
    order_id,
    order_number,
    created_date,
    customer_name,
    total
FROM `datalake-betminds.prataearte.pedidos`
ORDER BY created_date DESC
LIMIT 10;
```

## 🔄 Manutenção

### Atualizar Código

```bash
# Fazer alterações no cloud_function_import.py
# Re-deploy automático
./deploy-hourly-import.sh
```

### Atualizar Credenciais

```bash
# Atualizar credenciais LINX
./config-credentials-hourly.sh
```

### Alterar Frequência

```bash
# Pausar o scheduler
gcloud scheduler jobs pause import-linx-orders-hourly

# Alterar para a cada 30 minutos
gcloud scheduler jobs update http import-linx-orders-hourly \
    --schedule="*/30 * * * *"

# Resumir o scheduler
gcloud scheduler jobs resume import-linx-orders-hourly
```

## 💰 Custos

### Cloud Functions (Tier Gratuito)
- **2 milhões de invocações/mês** gratuitas
- **400.000 GB-segundos** de computação gratuitos
- **5GB** de tráfego de rede gratuito

### Cloud Scheduler
- **3 jobs** gratuitos por mês
- **$0.10** por job adicional

### BigQuery
- **1TB** de consultas gratuitas por mês
- **10GB** de armazenamento gratuito

**Estimativa para uso típico: $0-5/mês**

## 🚨 Troubleshooting

### Erro: "Function execution failed"

```bash
# Ver logs detalhados
gcloud functions logs read import-linx-orders-hourly --region=us-central1 --limit=100
```

### Erro: "Permission denied"

```bash
# Verificar permissões da conta de serviço
gcloud projects get-iam-policy datalake-betminds
```

### Erro: "API not enabled"

```bash
# Habilitar APIs necessárias
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
```

## 🎯 Vantagens da Solução

✅ **Automática**: Executa a cada hora sem intervenção  
✅ **Econômica**: Custo mínimo ou zero  
✅ **Escalável**: Google Cloud gerencia recursos  
✅ **Monitorada**: Logs e métricas automáticos  
✅ **Segura**: Credenciais protegidas  
✅ **Confiável**: Sem dependência da sua máquina  
✅ **Equivalente**: Mesmo comportamento do `--only-new`  

## 📞 Suporte

Para problemas específicos:

1. **Logs da Cloud Function**: Verificar logs detalhados
2. **Permissões**: Verificar IAM do projeto
3. **APIs**: Confirmar que todas as APIs estão habilitadas
4. **Credenciais**: Verificar variáveis de ambiente

## 🔐 Segurança

- **Credenciais LINX**: Armazenadas como variáveis de ambiente
- **Acesso BigQuery**: Controlado via IAM do Google Cloud
- **HTTPS**: Todas as comunicações são criptografadas
- **Logs**: Monitoramento de todas as execuções

## 🎉 Resultado Final

Após implementar, você terá:

- **Importação automática a cada hora**
- **Apenas pedidos novos** (equivalente ao `--only-new`)
- **Sem duplicatas**
- **Logs detalhados**
- **Monitoramento automático**
- **Custo mínimo**

**Sua máquina pode ficar desligada que a importação continuará funcionando!** 🚀
