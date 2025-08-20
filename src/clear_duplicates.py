import logging
import os
from bigquery_client import BigQueryClient
from google.cloud import bigquery

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configura credenciais do Google Cloud
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials", "datalake-betminds.json")

def clear_duplicates():
    """Remove registros duplicados do BigQuery, mantendo apenas o mais recente de cada pedido"""
    try:
        # Inicializa o cliente BigQuery
        bq_client = BigQueryClient()
        
        # Query para identificar duplicatas
        query = f"""
        WITH DuplicateOrders AS (
            SELECT 
                order_id,
                COUNT(*) as count,
                MAX(created_date) as max_date
            FROM `{bq_client.table_ref}`
            GROUP BY order_id
            HAVING COUNT(*) > 1
        ),
        OrdersToDelete AS (
            SELECT t.*
            FROM `{bq_client.table_ref}` t
            INNER JOIN DuplicateOrders d
            ON t.order_id = d.order_id
            AND t.created_date < d.max_date
        )
        SELECT COUNT(*) as total_duplicates
        FROM OrdersToDelete
        """
        
        # Executa a query para contar duplicatas
        query_job = bq_client.client.query(query)
        results = query_job.result()
        row = next(iter(results))
        total_duplicates = row.total_duplicates
        
        if total_duplicates == 0:
            logger.info("Nenhum registro duplicado encontrado.")
            return
        
        logger.info(f"Encontrados {total_duplicates} registros duplicados.")
        
        # Query para deletar duplicatas
        delete_query = f"""
        DELETE FROM `{bq_client.table_ref}`
        WHERE (order_id, created_date) IN (
            SELECT order_id, created_date
            FROM (
                SELECT 
                    order_id,
                    created_date,
                    ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY created_date DESC) as rn
                FROM `{bq_client.table_ref}`
            )
            WHERE rn > 1
        )
        """
        
        # Executa a query de deleção
        query_job = bq_client.client.query(delete_query)
        query_job.result()  # Aguarda a conclusão
        
        logger.info(f"Registros duplicados removidos com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro ao remover duplicatas: {str(e)}")
        raise

if __name__ == "__main__":
    clear_duplicates() 