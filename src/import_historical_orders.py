import os
import time
import logging
import yaml
import requests
from datetime import datetime, UTC
from dotenv import load_dotenv
from bigquery_client import BigQueryClient
from tqdm import tqdm

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente
load_dotenv()

def convert_linx_date(date_str):
    """Converte o formato de data do LINX (/Date(timestamp-offset)/) para o formato do BigQuery"""
    if not date_str or not isinstance(date_str, str) or not date_str.startswith('/Date('):
        return None
    
    try:
        # Extrai o timestamp e o offset
        timestamp_str = date_str.split('(')[1].split(')')[0]
        if not timestamp_str:
            logger.warning(f"Timestamp vazio: {date_str}")
            return None
            
        # Separa o timestamp e o offset (considerando que o timestamp pode ser negativo)
        if '-' in timestamp_str[1:]:  # Procura o segundo hífen (após o primeiro dígito)
            timestamp_ms, offset = timestamp_str.split('-', 1)
        else:
            timestamp_ms = timestamp_str
            offset = None
            
        if not timestamp_ms:
            logger.warning(f"Timestamp vazio: {date_str}")
            return None
            
        # Converte o timestamp para segundos
        timestamp = int(timestamp_ms) / 1000
        
        # Converte para datetime
        dt = datetime.fromtimestamp(timestamp)
        
        # Retorna no formato do BigQuery
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logger.warning(f"Erro ao converter data {date_str}: {str(e)}")
        return None

def safe_convert(value, target_type, default=None):
    """Converte valores de forma segura para o tipo desejado"""
    if value is None:
        return default
    
    try:
        if target_type == int:
            return int(float(str(value)))
        elif target_type == float:
            return float(str(value))
        elif target_type == str:
            return str(value)
        else:
            return value
    except (ValueError, TypeError):
        logger.warning(f"Não foi possível converter o valor '{value}' para {target_type.__name__}")
        return default

# Carrega configurações do YAML
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "config.yaml")
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

# Configura credenciais do Google Cloud (apenas se não estiver no Cloud Run)
if not os.environ.get('K_SERVICE'):  # Se não estiver no Cloud Run
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials", "datalake-betminds.json")

class LinxAPI:
    def __init__(self, config):
        """Inicializa a API com as configurações do arquivo YAML"""
        self.base_url = config['linx_api']['base_url']
        self.username = config['linx_api']['username']
        self.password = config['linx_api']['password']
        
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def search_orders(self, page_index, page_size, start_date=None):
        """Busca pedidos na API usando o formato correto da LINX"""
        url = f"{self.base_url}/v1/Sales/API.svc/web/SearchOrders"
        
        payload = {
            "Page": {
                "PageIndex": page_index,
                "PageSize": page_size
            }
        }
        
        # Adiciona filtro por data se fornecido usando o formato correto da LINX
        if start_date:
            # Converte o formato LINX para string de data
            if start_date.startswith('/Date('):
                try:
                    # Extrai o timestamp
                    timestamp_str = start_date.split('(')[1].split(')')[0]
                    timestamp_ms = int(timestamp_str.split('-')[0])
                    timestamp = timestamp_ms / 1000
                    
                    # Converte para datetime e depois para string
                    from datetime import datetime
                    dt = datetime.fromtimestamp(timestamp)
                    date_string = dt.strftime('%Y-%m-%d %H:%M:%S')
                    
                    payload["Where"] = f'CreatedDate > "{date_string}"'
                    logger.info(f"Filtro aplicado: CreatedDate > \"{date_string}\"")
                except Exception as e:
                    logger.warning(f"Erro ao converter data LINX {start_date}: {str(e)}")
                    # Se não conseguir converter, não aplica filtro
            else:
                # Se já for string, usa diretamente
                payload["Where"] = f'CreatedDate > "{start_date}"'
                logger.info(f"Filtro aplicado: CreatedDate > \"{start_date}\"")
        
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def get_order_by_number(self, order_number):
        """Obtém detalhes de um pedido pelo número"""
        url = f"{self.base_url}/v1/Sales/API.svc/web/GetOrderByNumber"
        response = self.session.post(url, json=order_number)
        response.raise_for_status()
        return response.json()

    def process_order(self, order_data):
        """Processa os dados do pedido para o formato do BigQuery"""
        try:
            # Extrai o endereço de entrega
            delivery_address = None
            for address in order_data.get('Addresses', []):
                if address.get('AddressType') == 68:  # Tipo 68 é endereço de entrega
                    delivery_address = address
                    break

            # Processa os itens do pedido
            items = []
            for item in order_data.get('Items', []):
                items.append({
                    'ProductID': str(item.get('ProductID', '')),
                    'ProductName': str(item.get('ProductName', '')),
                    'SKU': str(item.get('SKU', '')),
                    'Qty': float(item.get('Qty', 0)),
                    'Price': float(item.get('Price', 0)),
                    'Total': float(item.get('Total', 0)),
                    'Weight': float(item.get('Weight', 0)),
                    'Width': float(item.get('Width', 0)),
                    'Height': float(item.get('Height', 0)),
                    'Depth': float(item.get('Depth', 0))
                })

            # Processa os métodos de pagamento
            payment_methods = []
            for payment in order_data.get('PaymentMethods', []):
                payment_info = payment.get('PaymentInfo', {})
                payment_methods.append({
                    'PaymentMethodID': str(payment.get('PaymentMethodID', '')),
                    'Amount': float(payment.get('Amount', 0)),
                    'Status': str(payment.get('Status', '')),
                    'PaymentDate': convert_linx_date(payment.get('PaymentDate')),
                    'Installments': int(payment.get('Installments', 1)),
                    'PaymentInfo': str(payment_info.get('Alias', '')),
                    'PaymentType': str(payment_info.get('PaymentType', '')),
                    'Provider': str(payment_info.get('Provider', '')),
                    'AuthorizationCode': str(payment_info.get('AuthorizationCode', '')),
                    'TransactionNumber': str(payment_info.get('TransactionNumber', ''))
                })

            # Processa os métodos de entrega
            delivery_methods = []
            for prop in order_data.get('Properties', []):
                if prop.get('Type') == 'DeliveryMethod':
                    delivery_methods.append({
                        'DeliveryMethodAlias': str(prop.get('Reference', '')),
                        'ETA': str(prop.get('Message', '')),
                        'Amount': float(prop.get('Amount', 0)),
                        'CarrierName': 'Personalizado'  # Valor padrão
                    })

            # Processa os envios
            shipments = []
            for shipment in order_data.get('Shipments', []):
                shipment_number = str(shipment.get('ShipmentNumber', ''))
                shipment_status = shipment.get('ShipmentStatus')
                try:
                    shipment_status = int(shipment_status)
                except (ValueError, TypeError):
                    shipment_status = 0  # Valor padrão
                shipments.append({
                    'ShipmentNumber': shipment_number,
                    'ShipmentStatus': shipment_status
                })

            # Garante que campos obrigatórios não sejam nulos
            order_id = str(order_data.get('OrderID', ''))
            if not order_id:
                raise ValueError("OrderID é obrigatório e não pode ser nulo")

            order_number = str(order_data.get('OrderNumber', ''))
            if not order_number:
                raise ValueError("OrderNumber é obrigatório e não pode ser nulo")

            created_date = convert_linx_date(order_data.get('CreatedDate'))
            if not created_date:
                raise ValueError("CreatedDate é obrigatório e não pode ser nulo")

            global_status = int(order_data.get('GlobalStatus', 0))
            order_status_id = int(order_data.get('OrderStatusID', 0))

            # Retorna os dados processados
            return {
                'order_id': order_id,
                'order_number': order_number,
                'created_date': created_date,
                'acquired_date': convert_linx_date(order_data.get('AcquiredDate')),
                'cancelled_date': convert_linx_date(order_data.get('CancelledDate')),
                'global_status': global_status,
                'order_status_id': order_status_id,
                'total': float(order_data.get('Total', 0)),
                'subtotal': float(order_data.get('SubTotal', 0)),
                'delivery_amount': float(order_data.get('DeliveryAmount', 0)),
                'discount_amount': float(order_data.get('DiscountAmount', 0)),
                'tax_amount': float(order_data.get('TaxAmount', 0)),
                
                # Informações do cliente
                'customer_id': int(order_data.get('CustomerID', 0)),
                'customer_name': str(order_data.get('CustomerName', '')),
                'customer_email': str(order_data.get('CustomerEmail', '')),
                'customer_type': str(order_data.get('CustomerType', 'P')),  # P como padrão
                'customer_cpf': str(order_data.get('CustomerCPF', '')),
                'customer_cnpj': str(order_data.get('CustomerCNPJ', '')),
                'customer_cell_phone': str(order_data.get('CustomerCellPhone', '')),
                'customer_phone': str(order_data.get('CustomerPhone', '')),
                'customer_gender': str(order_data.get('CustomerGender', '')),
                'customer_birth_date': convert_linx_date(order_data.get('CustomerBirthDate')),
                
                # Endereço de entrega
                'delivery_address_line': str(delivery_address.get('AddressLine', '')) if delivery_address else '',
                'delivery_address_number': str(delivery_address.get('Number', '')) if delivery_address else '',
                'delivery_neighbourhood': str(delivery_address.get('Neighbourhood', '')) if delivery_address else '',
                'delivery_city': str(delivery_address.get('City', '')) if delivery_address else '',
                'delivery_state': str(delivery_address.get('State', '')) if delivery_address else '',
                'delivery_postal_code': str(delivery_address.get('PostalCode', '')) if delivery_address else '',
                'delivery_contact_name': str(delivery_address.get('ContactName', '')) if delivery_address else '',
                'delivery_contact_phone': str(delivery_address.get('ContactPhone', '')) if delivery_address else '',
                
                # Arrays
                'items': items,
                'payment_methods': payment_methods,
                'delivery_methods': delivery_methods,
                'shipments': shipments,
                
                # Status do envio
                'shipment_status': int(order_data.get('ShipmentStatus', 0)),
                
                # Informações do vendedor
                'seller_name': str(order_data.get('Seller', {}).get('Name', '')),
                'seller_email': str(order_data.get('Seller', {}).get('EMail', '')),
                'seller_phone': str(order_data.get('Seller', {}).get('Phone', '')),
                'seller_integration_id': str(order_data.get('Seller', {}).get('IntegrationID', '')),
                
                # Metadados
                'created_at': datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            logger.error(f"Erro ao processar pedido: {str(e)}")
            raise

def convert_to_linx_date(dt):
    """Converte datetime para o formato da API LINX (/Date(timestamp)/)"""
    if not dt:
        return None
    timestamp = int(dt.timestamp() * 1000)
    return f"/Date({timestamp})/"

def import_historical_orders(max_orders: int = None, only_new: bool = True):
    """Importa pedidos históricos para o BigQuery"""
    try:
        # Carrega configurações
        config = load_config()
        
        # Inicializa clientes
        linx_api = LinxAPI(config)
        bq_client = BigQueryClient()
        
        # Sempre obtém a data do último pedido importado para continuar de onde parou
        last_date = bq_client.get_last_order_date()
        if last_date:
            # Se for string, converte para datetime
            if isinstance(last_date, str):
                try:
                    last_date = datetime.strptime(last_date, '%Y-%m-%d %H:%M:%S')
                except Exception:
                    last_date = datetime.fromisoformat(last_date)
            
            # Converte para o formato da API LINX
            linx_last_date = convert_to_linx_date(last_date)
            logger.info(f"Último pedido importado em: {last_date}")
            logger.info(f"Continuando importação após: {linx_last_date}")
        else:
            linx_last_date = None
            logger.info("Nenhum pedido encontrado na tabela. Importando todos os pedidos.")
        
        # Busca pedidos
        page_index = 0  # Começa do índice 0 conforme especificação da LINX
        page_size = 100
        total_imported = 0
        total_skipped = 0
        total_processed = 0
        
        while True:
            try:
                # Busca pedidos na API
                logger.info(f"Buscando página {page_index + 1} com {page_size} pedidos...")
                response = linx_api.search_orders(page_index, page_size, linx_last_date)
                orders = response.get('Result', [])
                
                if not orders:
                    logger.info("Nenhum pedido encontrado nesta página. Finalizando importação.")
                    break
                
                logger.info(f"Encontrados {len(orders)} pedidos na página {page_index + 1}")
                
                # Processa cada pedido
                for order in tqdm(orders, desc=f"Página {page_index + 1}"):
                    total_processed += 1
                    
                    try:
                        order_id = str(order.get('OrderID', ''))
                        order_number = str(order.get('OrderNumber', ''))
                        
                        if not order_id:
                            logger.warning(f"Pedido sem OrderID na página {page_index + 1}. Pulando...")
                            continue
                        
                        # Verifica se o pedido já existe por order_id
                        if bq_client.check_order_exists(order_id):
                            logger.debug(f"Pedido {order_id} (OrderNumber: {order_number}) já existe. Pulando...")
                            total_skipped += 1
                            continue
                        
                        # Verifica também por order_number para garantir
                        if bq_client.check_order_exists(order_number, by_number=True):
                            logger.debug(f"Pedido com OrderNumber {order_number} já existe. Pulando...")
                            total_skipped += 1
                            continue
                        
                        # Obtém detalhes completos do pedido
                        logger.debug(f"Obtendo detalhes do pedido {order_number}...")
                        order_details = linx_api.get_order_by_number(order_number)
                        processed_order = linx_api.process_order(order_details)
                        
                        # Insere no BigQuery
                        if bq_client.insert_rows([processed_order]):
                            total_imported += 1
                            logger.info(f"✅ Pedido {order_id} (OrderNumber: {order_number}) importado com sucesso")
                        else:
                            logger.error(f"❌ Falha ao inserir pedido {order_id} (OrderNumber: {order_number})")
                        
                        # Verifica se atingiu o limite de pedidos
                        if max_orders and total_imported >= max_orders:
                            logger.info(f"Limite de {max_orders} pedidos atingido")
                            break
                    
                    except Exception as e:
                        logger.error(f"Erro ao processar pedido {order.get('OrderNumber', 'N/A')}: {str(e)}")
                        continue
                
                # Se atingiu o limite, sai do loop
                if max_orders and total_imported >= max_orders:
                    break
                
                # Incrementa página
                page_index += 1
                
                # Pausa entre páginas para não sobrecarregar a API
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Erro ao buscar pedidos na página {page_index + 1}: {str(e)}")
                break
        
        logger.info(f"🎉 Importação concluída!")
        logger.info(f"📊 Resumo:")
        logger.info(f"   - Total processado: {total_processed}")
        logger.info(f"   - Total importado: {total_imported}")
        logger.info(f"   - Total pulado (já existia): {total_skipped}")
        
        if total_imported > 0:
            logger.info(f"✅ {total_imported} novos pedidos foram importados com sucesso!")
        else:
            logger.info("ℹ️  Nenhum novo pedido foi importado.")
            
    except Exception as e:
        logger.error(f"Erro na importação: {str(e)}")
        raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Importa pedidos do LINX para o BigQuery')
    parser.add_argument('--max-orders', type=int, help='Número máximo de pedidos a importar')
    parser.add_argument('--only-new', action='store_true', help='Importa apenas pedidos novos')
    args = parser.parse_args()
    
    import_historical_orders(args.max_orders, args.only_new) 