"""
Teste de integração - Nuvem Fiscal no nfse_search.py
"""

import sys
from pathlib import Path

# Adiciona diretório ao path para importação
sys.path.insert(0, str(Path(__file__).parent))

from nfse_search import NFSeService

def testar_integracao():
    """Testa a integração Nuvem Fiscal."""
    
    print("\n" + "="*80)
    print("🧪 TESTE DE INTEGRAÇÃO - NUVEM FISCAL")
    print("="*80)
    
    # Simula certificado (não será usado para Nuvem Fiscal)
    certificado_path = "dummy.pfx"
    senha = "dummy"
    cnpj = "33251845000109"
    
    # Cria instância do serviço
    service = NFSeService(certificado_path, senha, cnpj)
    
    # Testa busca por Campo Grande (configurado como NUVEMFISCAL)
    print("\n1️⃣  Testando busca para Campo Grande/MS (NUVEMFISCAL):")
    print("-" * 80)
    
    resultado = service.buscar_ginfes(
        codigo_municipio="5002704",  # Campo Grande
        inscricao_municipal="",
        data_inicial="01/05/2025",
        data_final="18/12/2025"
    )
    
    if resultado:
        print(f"\n✅ Sucesso! Retornou {len(resultado) if isinstance(resultado, list) else 1} resultado(s)")
        print(f"   Tipo: {type(resultado)}")
        if isinstance(resultado, list) and resultado:
            print(f"\n📄 Primeira NFS-e:")
            primeiro = resultado[0]
            for chave, valor in primeiro.items():
                print(f"   {chave}: {valor}")
    else:
        print("\n⚠️  Nenhum resultado retornado (pode ser esperado se não houver NFS-e)")
    
    print("\n" + "="*80)
    print("✅ Teste concluído!")
    print("="*80)

if __name__ == "__main__":
    testar_integracao()
