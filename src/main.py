from linx_api import LinxAPI
from bigquery_client import BigQueryClient
import time
import logging

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    try:
        # Inicializa os clientes
        linx_api = LinxAPI()
        bq_client = BigQueryClient()

        # Cria a tabela se não existir
        bq_client.create_table_if_not_exists()

        # Busca itens na fila
        queue_response = linx_api.search_queue_items()
        
        if not queue_response.get('Result'):
            logger.info("Nenhum pedido encontrado na fila")
            return

        # Lista para armazenar os IDs dos itens processados
        processed_items = []
        # Lista para armazenar os dados processados
        processed_data = []

        # Processa cada item da fila
        for item in queue_response['Result']:
            try:
                # Obtém o número do pedido
                order_number = item.get('EntityKeyValue')
                if not order_number:
                    continue

                # Busca os detalhes do pedido
                order_data = linx_api.get_order_by_number(order_number)
                
                # Processa os dados do pedido
                processed_order = linx_api.process_order(order_data)
                processed_data.append(processed_order)
                
                # Adiciona o ID do item à lista de processados
                processed_items.append(item.get('QueueItemID'))
                
                logger.info(f"Pedido {order_number} processado com sucesso")

            except Exception as e:
                logger.error(f"Erro ao processar pedido {order_number}: {str(e)}")
                continue

        # Insere os dados no BigQuery
        if processed_data:
            success = bq_client.insert_rows(processed_data)
            if success:
                # Remove os itens processados da fila
                if processed_items:
                    linx_api.dequeue_queue_items(processed_items)
                logger.info(f"{len(processed_data)} pedidos inseridos com sucesso")
            else:
                logger.error("Erro ao inserir dados no BigQuery")

    except Exception as e:
        logger.error(f"Erro durante a execução: {str(e)}")

if __name__ == "__main__":
    main() 