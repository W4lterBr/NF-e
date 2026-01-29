#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para executar testes no ambiente de homologação

⚠️ ATENÇÃO ⚠️
Este script usa o ambiente de HOMOLOGAÇÃO (tpAmb=2) da SEFAZ.
Os documentos consultados são apenas para teste e não têm validade fiscal.

REQUISITOS:
- Certificado digital válido (mesmo da produção pode ser usado)
- Certificado configurado no banco de dados
- Conexão com internet

O QUE FAZ:
1. Conecta aos servidores de homologação da SEFAZ
2. Busca documentos de teste (NF-e e CT-e)
3. Salva em pasta separada: xmls_test/
4. Usa banco de dados separado: notas_test.db
5. Exibe logs detalhados HTTP
"""

import sys
import logging
from pathlib import Path

# Força UTF-8 no console Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_run.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Executa teste no ambiente de homologação"""
    
    print("=" * 80)
    print("🧪 EXECUTANDO TESTE - PRODUÇÃO COM DADOS ISOLADOS (tpAmb=1)")
    print("=" * 80)
    print()
    print("📋 Configuração:")
    print("   • Ambiente: PRODUÇÃO (documentos REAIS)")
    print("   • Banco de dados: notas_test.db (separado)")
    print("   • Pasta XMLs: xmls_test/ (separada)")
    print("   • Logs: test_run.log")
    print()
    print("🔄 Iniciando busca...")
    print()
    
    try:
        # Importa a versão de teste
        import nfe_search_test
        
        # Executa um ciclo de busca
        logger.info("=" * 80)
        logger.info("TESTE INICIADO - Produção com Dados Isolados")
        logger.info("=" * 80)
        
        nfe_search_test.run_single_cycle()
        
        logger.info("=" * 80)
        logger.info("TESTE CONCLUÍDO COM SUCESSO")
        logger.info("=" * 80)
        
        print()
        print("=" * 80)
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        print("=" * 80)
        print()
        print("📂 Resultados:")
        print(f"   • Banco de dados: notas_test.db")
        print(f"   • XMLs baixados: xmls_test/")
        print(f"   • Log detalhado: test_run.log")
        print()
        print("💡 Dicas:")
        print("   • Revise test_run.log para ver logs HTTP detalhados")
        print("   • Compare os XMLs de teste com os de produção")
        print("   • Use um visualizador SQLite para ver notas_test.db")
        print()
        
    except Exception as e:
        logger.exception("❌ ERRO durante teste")
        print()
        print("=" * 80)
        print("❌ ERRO DURANTE TESTE")
        print("=" * 80)
        print()
        print(f"Erro: {e}")
        print()
        print("Verifique test_run.log para detalhes completos")
        print()
        sys.exit(1)

if __name__ == "__main__":
    main()
