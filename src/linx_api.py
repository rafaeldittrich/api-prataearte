import requests
import json
import datetime
import yaml
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def convert_linx_date(date_str): 
    """Converte o formato de data do LINX (/Date(timestamp-offset)/) para o formato do BigQuery"""
    if not date_str or not date_str.startswith('/Date('):
        return None
    
    try:
        # Extrai o timestamp e o offset
        timestamp_str = date_str.split('(')[1].split(')')[0]
        timestamp = int(timestamp_str.split('-')[0]) / 1000  # Converte de milissegundos para segundos
        
        # Converte para datetime
        dt = datetime.fromtimestamp(timestamp)
        
        # Retorna no formato do BigQuery
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logger.warning(f"Erro ao converter data {date_str}: {str(e)}")
        return None

class LinxAPI:
    def __init__(self, config_path='config/config.yaml'):
        """Inicializa a API com as configurações do arquivo YAML"""
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
            self.base_url = config['linx_api']['base_url']
            self.username = config['linx_api']['username']
            self.password = config['linx_api']['password']
        
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def search_queue_items(self, queue_id=31, page_size=10):
        """Busca itens na fila de pedidos"""
        url = f"{self.base_url}/v1/Queue/API.svc/web/SearchQueueItems"
        
        payload = {
            "QueueID": queue_id,
            "LockItems": True,
            "Page": {
                "PageIndex": 0,
                "PageSize": page_size
            }
        }
        
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def get_order_by_number(self, order_number):
        """Obtém detalhes de um pedido pelo número"""
        url = f"{self.base_url}/v1/Sales/API.svc/web/GetOrderByNumber"
        response = self.session.post(url, json=order_number)
        response.raise_for_status()
        return response.json()

    def dequeue_queue_items(self, queue_items):
        """Remove itens da fila após processamento"""
        url = f"{self.base_url}/v1/Queue/API.svc/web/DequeueQueueItems"
        
        payload = {
            "QueueItems": queue_items
        }
        
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def safe_convert(self, value, target_type, default=None):
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
                    'ProductID': item.get('ProductID'),
                    'ProductName': item.get('ProductName'),
                    'SKU': item.get('SKU'),
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
                    'PaymentMethodID': payment.get('PaymentMethodID'),
                    'Amount': float(payment.get('Amount', 0)),
                    'Status': payment.get('Status'),
                    'PaymentDate': convert_linx_date(payment.get('PaymentDate')),
                    'Installments': payment.get('Installments'),
                    'PaymentInfo': payment_info.get('Alias'),
                    'PaymentType': payment_info.get('PaymentType'),
                    'Provider': payment_info.get('Provider'),
                    'AuthorizationCode': payment_info.get('AuthorizationCode'),
                    'TransactionNumber': payment_info.get('TransactionNumber')
                })

            # Processa os métodos de entrega
            delivery_methods = []
            for prop in order_data.get('Properties', []):
                if prop.get('Type') == 'DeliveryMethod':
                    delivery_methods.append({
                        'DeliveryMethodAlias': prop.get('Reference'),
                        'ETA': prop.get('Message'),
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
                    shipment_status = None
                shipments.append({
                    'ShipmentNumber': shipment_number,
                    'ShipmentStatus': shipment_status
                })

            # Retorna os dados processados
            return {
                'order_id': order_data.get('OrderID'),
                'order_number': order_data.get('OrderNumber'),
                'created_date': convert_linx_date(order_data.get('CreatedDate')),
                'global_status': order_data.get('GlobalStatus'),
                'order_status_id': order_data.get('OrderStatusID'),
                'total': float(order_data.get('Total', 0)),
                'subtotal': float(order_data.get('SubTotal', 0)),
                'delivery_amount': float(order_data.get('DeliveryAmount', 0)),
                'discount_amount': float(order_data.get('DiscountAmount', 0)),
                'tax_amount': float(order_data.get('TaxAmount', 0)),
                
                # Informações do cliente
                'customer_id': order_data.get('CustomerID'),
                'customer_name': order_data.get('CustomerName'),
                'customer_email': order_data.get('CustomerEmail'),
                'customer_type': order_data.get('CustomerType'),
                'customer_cpf': order_data.get('CustomerCPF'),
                'customer_cnpj': order_data.get('CustomerCNPJ'),
                'customer_cell_phone': order_data.get('CustomerCellPhone'),
                'customer_phone': order_data.get('CustomerPhone'),
                'customer_gender': order_data.get('CustomerGender'),
                'customer_birth_date': convert_linx_date(order_data.get('CustomerBirthDate')),
                
                # Endereço de entrega
                'delivery_address_line': delivery_address.get('AddressLine') if delivery_address else None,
                'delivery_address_number': delivery_address.get('Number') if delivery_address else None,
                'delivery_neighbourhood': delivery_address.get('Neighbourhood') if delivery_address else None,
                'delivery_city': delivery_address.get('City') if delivery_address else None,
                'delivery_state': delivery_address.get('State') if delivery_address else None,
                'delivery_postal_code': delivery_address.get('PostalCode') if delivery_address else None,
                'delivery_contact_name': delivery_address.get('ContactName') if delivery_address else None,
                'delivery_contact_phone': delivery_address.get('ContactPhone') if delivery_address else None,
                
                # Arrays
                'items': items,
                'payment_methods': payment_methods,
                'delivery_methods': delivery_methods,
                'shipments': shipments,
                
                # Status do envio
                'shipment_status': order_data.get('ShipmentStatus'),
                
                # Informações do vendedor
                'seller_name': order_data.get('Seller', {}).get('Name'),
                'seller_email': order_data.get('Seller', {}).get('EMail'),
                'seller_phone': order_data.get('Seller', {}).get('Phone'),
                'seller_integration_id': order_data.get('Seller', {}).get('IntegrationID'),
                # Metadados
                'created_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            logger.error(f"Erro ao processar pedido: {str(e)}")
            raise 

    def search_orders(self, page_index: int = 1, page_size: int = 100, last_date: str = None) -> dict:
        """Busca pedidos na API LINX"""
        try:
            payload = {
                "Page": {
                    "Index": page_index,
                    "PageSize": page_size
                }
            }
            if last_date:
                payload["OrderDate"] = last_date
            response = self.session.post(f"{self.base_url}/v1/Sales/API.svc/web/SearchOrders", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Erro ao buscar pedidos: {str(e)}")
            raise 