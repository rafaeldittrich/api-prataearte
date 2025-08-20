from google.cloud import bigquery
import yaml
import os
import logging
import time

logger = logging.getLogger(__name__)

class BigQueryClient:
    def __init__(self, config=None):
        """Inicializa o cliente BigQuery com as configurações do arquivo YAML ou dicionário"""
        if isinstance(config, dict):
            self.project_id = config['bigquery']['project_id']
            self.dataset_id = config['bigquery']['dataset_id']
            self.table_id = config['bigquery']['table_id']
            self.table_schema = config['table_schema']
        else:
            config_path = config if config else 'config/config.yaml'
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
                self.project_id = config['bigquery']['project_id']
                self.dataset_id = config['bigquery']['dataset_id']
                self.table_id = config['bigquery']['table_id']
                self.table_schema = config['table_schema']
        
        self.client = bigquery.Client()
        self.table_ref = f"{self.project_id}.{self.dataset_id}.{self.table_id}"

    def create_table_if_not_exists(self):
        """Cria a tabela se ela não existir e aguarda até estar disponível"""
        try:
            # Verifica se a tabela existe
            try:
                table = self.client.get_table(self.table_ref)
                logger.info(f"Tabela {self.table_ref} já existe")
                return True
            except Exception:
                # Cria a tabela se não existir
                schema = []
                for field in self.table_schema:
                    if field.get('type') == 'RECORD':
                        # Processa campos RECORD
                        record_fields = []
                        for subfield in field.get('fields', []):
                            record_fields.append(
                                bigquery.SchemaField(
                                    name=subfield['name'],
                                    field_type=subfield['type'],
                                    mode=subfield.get('mode', 'NULLABLE'),
                                    description=subfield.get('description', '')
                                )
                            )
                        schema.append(
                            bigquery.SchemaField(
                                name=field['name'],
                                field_type=field['type'],
                                mode=field['mode'],
                                description=field.get('description', ''),
                                fields=record_fields
                            )
                        )
                    else:
                        # Processa campos normais
                        schema.append(
                            bigquery.SchemaField(
                                name=field['name'],
                                field_type=field['type'],
                                mode=field['mode'],
                                description=field.get('description', '')
                            )
                        )

                table = bigquery.Table(self.table_ref, schema=schema)
                table = self.client.create_table(table)
                logger.info(f"Tabela {self.table_ref} criada com sucesso")
                # Aguarda ativamente até a tabela estar disponível
                for i in range(30):  # até 30 segundos
                    try:
                        self.client.get_table(self.table_ref)
                        logger.info(f"Tabela {self.table_ref} disponível após {i+1} segundos.")
                        break
                    except Exception:
                        time.sleep(1)
                else:
                    logger.warning(f"Tabela {self.table_ref} pode não estar disponível após 30 segundos.")
                return True
        except Exception as e:
            logger.error(f"Erro ao criar tabela: {str(e)}")
            raise

    def insert_rows(self, rows):
        """Insere linhas na tabela"""
        try:
            # Garante que a tabela existe
            self.create_table_if_not_exists()
            
            errors = self.client.insert_rows_json(self.table_ref, rows)
            if errors:
                logger.error(f"Erro ao inserir linhas: {errors}")
                return False
            logger.info(f"{len(rows)} linhas inseridas com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao inserir linhas: {str(e)}")
            raise

    def check_order_exists(self, value, by_number=False):
        """Verifica se um pedido já existe na tabela por order_id ou order_number"""
        try:
            if by_number:
                query = f"""
                SELECT COUNT(*) as count
                FROM `{self.table_ref}`
                WHERE order_number = @value
                """
                param_type = "STRING"
            else:
                query = f"""
                SELECT COUNT(*) as count
                FROM `{self.table_ref}`
                WHERE order_id = @value
                """
                param_type = "STRING"
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("value", param_type, value)
                ]
            )
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            row = next(iter(results))
            return row.count > 0
        except Exception as e:
            logger.error(f"Erro ao verificar existência do pedido: {str(e)}")
            return False

    def get_last_order_date(self):
        """Retorna a data do último pedido importado"""
        try:
            # Garante que a tabela existe
            self.create_table_if_not_exists()
            
            query = f"""
            SELECT MAX(created_date) as last_date
            FROM `{self.table_ref}`
            WHERE created_date IS NOT NULL
            """
            query_job = self.client.query(query)
            results = query_job.result()
            row = next(iter(results))
            
            if row.last_date:
                logger.info(f"Último pedido na tabela: {row.last_date}")
                return row.last_date
            else:
                logger.info("Nenhum pedido encontrado na tabela")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao obter data do último pedido: {str(e)}")
            return None 