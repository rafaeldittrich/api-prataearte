import logging
import json
import datetime
from linx_api import LinxAPI
from bigquery_client import BigQueryClient
import time

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_section(title):
    """Imprime uma seção formatada"""
    logger.info(f"\n{title}")
    logger.info("=" * 50)

def print_field(name, value):
    """Imprime um campo formatado"""
    if isinstance(value, (int, float)):
        logger.info(f"{name}: {value}")
    elif isinstance(value, str):
        logger.info(f"{name}: {value}")
    elif value is None:
        logger.info(f"{name}: None")
    else:
        logger.info(f"{name}: {json.dumps(value, indent=2, ensure_ascii=False)}")

def test_order_extraction(order_number):
    """Testa a extração e processamento de um pedido específico"""
    try:
        # Inicializa a API e o cliente BigQuery
        api = LinxAPI()
        bq_client = BigQueryClient()
        
        # Cria a tabela se não existir
        logger.info("Verificando/criando tabela no BigQuery...")
        bq_client.create_table_if_not_exists()
        
        # Busca o pedido
        logger.info(f"Buscando pedido {order_number}...")
        order_data = api.get_order_by_number(order_number)
        
        # Exibe os dados brutos do pedido
        print_section("Dados Brutos do Pedido")
        print_field("Order Data", order_data)
        
        # Processa o pedido
        logger.info("\nProcessando dados do pedido...")
        processed_data = api.process_order(order_data)
        
        # Exibe os dados processados de forma organizada
        print_section("Dados Processados")
        
        # Informações Básicas
        print_section("Informações Básicas")
        print_field("Order ID", processed_data['order_id'])
        print_field("Order Number", processed_data['order_number'])
        print_field("Created Date", processed_data['created_date'])
        print_field("Global Status", processed_data['global_status'])
        print_field("Order Status ID", processed_data['order_status_id'])
        print_field("Total", f"R$ {processed_data['total']:.2f}")
        print_field("Subtotal", f"R$ {processed_data['subtotal']:.2f}")
        print_field("Delivery Amount", f"R$ {processed_data['delivery_amount']:.2f}")
        print_field("Discount Amount", f"R$ {processed_data['discount_amount']:.2f}")
        print_field("Tax Amount", f"R$ {processed_data['tax_amount']:.2f}")
        
        # Informações do Cliente
        print_section("Informações do Cliente")
        print_field("Customer ID", processed_data['customer_id'])
        print_field("Name", processed_data['customer_name'])
        print_field("Email", processed_data['customer_email'])
        print_field("Type", processed_data['customer_type'])
        print_field("CPF", processed_data['customer_cpf'])
        print_field("CNPJ", processed_data['customer_cnpj'])
        print_field("Cell Phone", processed_data['customer_cell_phone'])
        print_field("Phone", processed_data['customer_phone'])
        print_field("Gender", processed_data['customer_gender'])
        print_field("Birth Date", processed_data['customer_birth_date'])
        
        # Endereço de Entrega
        print_section("Endereço de Entrega")
        print_field("Address Line", processed_data['delivery_address_line'])
        print_field("Number", processed_data['delivery_address_number'])
        print_field("Neighbourhood", processed_data['delivery_neighbourhood'])
        print_field("City", processed_data['delivery_city'])
        print_field("State", processed_data['delivery_state'])
        print_field("Postal Code", processed_data['delivery_postal_code'])
        print_field("Contact Name", processed_data['delivery_contact_name'])
        print_field("Contact Phone", processed_data['delivery_contact_phone'])
        
        # Itens do Pedido
        print_section("Itens do Pedido")
        for item in processed_data['items']:
            logger.info(f"\nProduto: {item['ProductName']}")
            print_field("  Product ID", item['ProductID'])
            print_field("  SKU", item['SKU'])
            print_field("  Quantidade", item['Qty'])
            print_field("  Preço", f"R$ {item['Price']:.2f}")
            print_field("  Total", f"R$ {item['Total']:.2f}")
            print_field("  Dimensões", f"{item['Width']}x{item['Height']}x{item['Depth']} (Peso: {item['Weight']})")
        
        # Métodos de Pagamento
        print_section("Métodos de Pagamento")
        for payment in processed_data['payment_methods']:
            logger.info(f"\nMétodo: {payment['PaymentType']}")
            print_field("  ID", payment['PaymentMethodID'])
            print_field("  Valor", f"R$ {payment['Amount']:.2f}")
            print_field("  Status", payment['Status'])
            print_field("  Data", payment['PaymentDate'])
            print_field("  Parcelas", payment['Installments'])
            print_field("  Provedor", payment['Provider'])
            print_field("  Código de Autorização", payment['AuthorizationCode'])
            print_field("  Número da Transação", payment['TransactionNumber'])
        
        # Métodos de Entrega
        print_section("Métodos de Entrega")
        for delivery in processed_data['delivery_methods']:
            logger.info(f"\nTransportadora: {delivery['CarrierName']}")
            print_field("  Método", delivery['DeliveryMethodAlias'])
            print_field("  ETA", delivery['ETA'])
            print_field("  Valor", f"R$ {delivery['Amount']:.2f}")
        
        # Status do Envio
        print_section("Status do Envio")
        print_field("Status", processed_data['shipment_status'])
        for shipment in processed_data['shipments']:
            logger.info(f"\nEnvio: {shipment['ShipmentNumber']}")
            print_field("  Status", shipment['ShipmentStatus'])
        
        # Informações do Vendedor
        print_section("Informações do Vendedor")
        print_field("Name", processed_data['seller_name'])
        print_field("Email", processed_data['seller_email'])
        print_field("Phone", processed_data['seller_phone'])
        print_field("Integration ID", processed_data['seller_integration_id'])
        
        # Log do campo shipments
        logger.info(f"Conteúdo de shipments: {processed_data['shipments']}")
        # Log do campo delivery_methods
        logger.info(f"Conteúdo de delivery_methods: {processed_data['delivery_methods']}")
        # Log do campo payment_methods
        logger.info(f"Conteúdo de payment_methods: {processed_data['payment_methods']}")
        
        # Adiciona o campo created_at
        # Insere os dados no BigQuery
        logger.info("\nInserindo dados no BigQuery...")
        if bq_client.insert_rows([processed_data]):
            logger.info("Dados inseridos com sucesso no BigQuery!")
        else:
            logger.error("Erro ao inserir dados no BigQuery")
            return False
        
        logger.info("\n" + "=" * 50)
        logger.info("Processamento concluído com sucesso!")
        
        return True
    except Exception as e:
        logger.error(f"Erro ao processar o pedido: {str(e)}")
        return False

def test_specific_order(order_number):
    try:
        # Inicializa os clientes
        linx_api = LinxAPI()
        bq_client = BigQueryClient()

        # Busca os detalhes do pedido
        logger.info(f"Buscando pedido {order_number}...")
        order_data = linx_api.get_order_by_number(order_number)
        
        # Processa os dados do pedido
        logger.info("Processando dados do pedido...")
        processed_order = linx_api.process_order(order_data)
        
        # Log do campo shipments
        logger.info(f"Conteúdo de shipments: {processed_order['shipments']}")
        # Log do campo delivery_methods
        logger.info(f"Conteúdo de delivery_methods: {processed_order['delivery_methods']}")
        # Log do campo payment_methods
        logger.info(f"Conteúdo de payment_methods: {processed_order['payment_methods']}")
        
        # Insere os dados no BigQuery
        logger.info("Inserindo dados no BigQuery...")
        success = bq_client.insert_rows([processed_order])
        
        if success:
            logger.info(f"Pedido {order_number} inserido com sucesso!")
        else:
            logger.error("Erro ao inserir dados no BigQuery")

    except Exception as e:
        logger.error(f"Erro durante o teste: {str(e)}")

def aguardar_pedido_na_fila(intervalo=60):
    """Fica consultando a fila até encontrar um pedido, processa e insere no BigQuery."""
    linx_api = LinxAPI()
    bq_client = BigQueryClient()
    logger.info("Aguardando pedido na fila...")
    while True:
        try:
            queue_response = linx_api.search_queue_items()
            if queue_response.get('Result'):
                for item in queue_response['Result']:
                    order_number = item.get('EntityKeyValue')
                    if not order_number:
                        continue
                    logger.info(f"Pedido encontrado na fila: {order_number}")
                    order_data = linx_api.get_order_by_number(order_number)
                    processed_order = linx_api.process_order(order_data)
                    processed_order['created_at'] = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                    logger.info("Inserindo pedido no BigQuery...")
                    if bq_client.insert_rows([processed_order]):
                        logger.info(f"Pedido {order_number} inserido com sucesso!")
                        linx_api.dequeue_queue_items([item.get('QueueItemID')])
                        logger.info(f"Pedido {order_number} removido da fila.")
                    else:
                        logger.error(f"Erro ao inserir pedido {order_number} no BigQuery.")
                break  # Sai do loop após processar pedidos encontrados
            else:
                logger.info(f"Nenhum pedido na fila. Aguardando {intervalo} segundos...")
                time.sleep(intervalo)
        except Exception as e:
            logger.error(f"Erro ao consultar/processar fila: {str(e)}")
            time.sleep(intervalo)

# Para testar a fila, descomente a linha abaixo:
# aguardar_pedido_na_fila(10)

if __name__ == "__main__":
    # test_specific_order("60094")
    aguardar_pedido_na_fila(60) 