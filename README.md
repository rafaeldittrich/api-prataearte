# Integração LINX - BigQuery

Este projeto realiza a integração entre a API do e-commerce LINX e o Google BigQuery, extraindo dados de pedidos e armazenando-os em uma tabela estruturada.

## Requisitos

- Python 3.8+
- Credenciais do Google Cloud Platform (arquivo JSON)
- Acesso à API LINX

## Instalação

1. Clone o repositório:
```bash
git clone [URL_DO_REPOSITÓRIO]
cd api-prataearte
```

2. Crie um ambiente virtual e ative-o:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as credenciais do Google Cloud:
   - Baixe o arquivo JSON de credenciais do serviço
   - Defina a variável de ambiente GOOGLE_APPLICATION_CREDENTIALS:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="caminho/para/seu/arquivo-credenciais.json"
```

## Configuração

O arquivo `config/config.yaml` contém todas as configurações necessárias:

- Credenciais da API LINX
- Configurações do BigQuery
- Schema da tabela

## Uso

Para executar a integração:

```bash
python src/main.py
```

O script irá:
1. Buscar pedidos na fila da API LINX
2. Processar os dados de cada pedido
3. Inserir os dados no BigQuery
4. Remover os itens processados da fila

## Estrutura do Projeto

```
api-prataearte/
├── config/
│   └── config.yaml
├── credentials/
│   └── datalake-betminds.json
├── src/
│   ├── __init__.py
│   ├── linx_api.py
│   ├── bigquery_client.py
│   └── main.py
├── requirements.txt
└── README.md
```

## Agendamento

Para executar o script periodicamente, você pode usar o cron (Linux/Mac) ou o Agendador de Tarefas (Windows).

Exemplo de configuração do cron para execução a cada 5 minutos:
```bash
*/5 * * * * cd /caminho/para/api-prataearte && /caminho/para/venv/bin/python src/main.py
```

## Logs

Os logs são exibidos no console e incluem:
- Informações sobre pedidos processados
- Erros durante o processamento
- Status da inserção no BigQuery 