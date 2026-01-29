"""
Script para testar se os logs estão aparecendo durante a busca
"""
import sys
import logging

# Configurar logging ANTES de importar nfe_search
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Agora importar nfe_search
from nfe_search import run_single_cycle

if __name__ == "__main__":
    print("="*80)
    print("TESTE DE BUSCA COM LOGS")
    print("="*80)
    print("\nIniciando busca... Observe os logs abaixo:")
    print("-"*80)
    
    try:
        run_single_cycle()
        print("-"*80)
        print("\n✅ Busca concluída com sucesso!")
    except Exception as e:
        print("-"*80)
        print(f"\n❌ Erro durante a busca: {e}")
        import traceback
        traceback.print_exc()
