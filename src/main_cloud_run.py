#!/usr/bin/env python3
"""
Entry point para Cloud Run - Importação de pedidos LINX
Equivale a executar: python3 src/import_historical_orders.py --only-new
"""

import os
import logging
from flask import Flask, request, jsonify
from import_historical_orders import import_historical_orders

# Configuração de logging para Cloud Run
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cria a aplicação Flask
app = Flask(__name__)

@app.route('/', methods=['GET'])
def health_check():
    """Health check para Cloud Run"""
    return jsonify({
        'status': 'healthy',
        'service': 'linx-orders-importer',
        'version': '1.0.0'
    })

@app.route('/import', methods=['POST'])
def import_orders():
    """Endpoint para importar pedidos (equivalente ao --only-new)"""
    try:
        logger.info("🚀 Iniciando importação de pedidos LINX...")
        
        # Executa a importação (sempre com only_new=True)
        import_historical_orders(max_orders=None, only_new=True)
        
        logger.info("✅ Importação concluída com sucesso!")
        
        return jsonify({
            'status': 'success',
            'message': 'Importação de pedidos concluída com sucesso',
            'mode': 'only_new'
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Erro na importação: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/import-test', methods=['POST'])
def import_orders_test():
    """Endpoint para teste com limite de pedidos"""
    try:
        data = request.get_json() or {}
        max_orders = data.get('max_orders', 5)  # Padrão: 5 pedidos
        
        logger.info(f"🧪 Iniciando importação de teste (máx: {max_orders} pedidos)...")
        
        # Executa a importação com limite
        import_historical_orders(max_orders=max_orders, only_new=True)
        
        logger.info("✅ Importação de teste concluída com sucesso!")
        
        return jsonify({
            'status': 'success',
            'message': f'Importação de teste concluída (máx: {max_orders} pedidos)',
            'mode': 'test',
            'max_orders': max_orders
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Erro na importação de teste: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Cloud Run define a porta via variável de ambiente
    port = int(os.environ.get('PORT', 8080))
    
    logger.info(f"🚀 Iniciando servidor na porta {port}")
    logger.info("📝 Endpoints disponíveis:")
    logger.info("   - GET  / : Health check")
    logger.info("   - POST /import : Importação completa (--only-new)")
    logger.info("   - POST /import-test : Importação de teste")
    
    # Executa em modo de desenvolvimento se não for Cloud Run
    if os.environ.get('K_SERVICE'):
        # Modo Cloud Run
        app.run(host='0.0.0.0', port=port)
    else:
        # Modo local para testes
        logger.info("🔧 Modo local - use: python3 src/main_cloud_run.py")
        app.run(host='0.0.0.0', port=port, debug=True)
