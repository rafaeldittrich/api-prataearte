import logging
from linx_api import LinxAPI
from bigquery_client import BigQueryClient

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_linx_connection():
    """Testa a conexão com a API da LINX"""
    try:
        logger.info("Testando conexão com a API da LINX...")
        api = LinxAPI()
        
        # Testa a busca de itens na fila
        queue_items = api.search_queue_items(page_size=1)
        logger.info(f"Conexão com a API da LINX bem sucedida!")
        logger.info(f"Encontrados {len(queue_items.get('Items', []))} itens na fila")
        
        # Se houver itens, testa a busca de um pedido
        if queue_items.get('Items'):
            order_number = queue_items['Items'][0]['Data']
            order = api.get_order_by_number(order_number)
            logger.info(f"Pedido {order_number} encontrado com sucesso!")
            
        return True
    except Exception as e:
        logger.error(f"Erro ao conectar com a API da LINX: {str(e)}")
        return False

def test_bigquery_connection():
    """Testa a conexão com o BigQuery"""
    try:
        logger.info("Testando conexão com o BigQuery...")
        bq_client = BigQueryClient()
        
        # Tenta criar a tabela (se não existir)
        bq_client.create_table_if_not_exists()
        logger.info("Conexão com o BigQuery bem sucedida!")
        logger.info("Tabela verificada/criada com sucesso!")
        
        return True
    except Exception as e:
        logger.error(f"Erro ao conectar com o BigQuery: {str(e)}")
        return False

def main():
    """Função principal para testar as conexões"""
    logger.info("Iniciando testes de conexão...")
    
    # Testa conexão com a LINX
    linx_ok = test_linx_connection()
    
    # Testa conexão com o BigQuery
    bq_ok = test_bigquery_connection()
    
    # Resumo dos testes
    logger.info("\nResumo dos testes:")
    logger.info(f"API da LINX: {'OK' if linx_ok else 'FALHA'}")
    logger.info(f"BigQuery: {'OK' if bq_ok else 'FALHA'}")
    
    if linx_ok and bq_ok:
        logger.info("Todas as conexões estão funcionando corretamente!")
    else:
        logger.error("Algumas conexões falharam. Verifique os logs acima para mais detalhes.")

if __name__ == "__main__":
    main() 