"""Teste de busca NFS-e para CNPJ específico."""
import sys
from pathlib import Path

# Adiciona diretório ao path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from nfse_search import NFSeDatabase, NFSeService, URLS_MUNICIPIOS

# CNPJ para testar
cnpj_teste = '49068153000160'

print("=" * 70)
print(f"TESTE DE BUSCA NFS-e - CNPJ: {cnpj_teste}")
print("=" * 70)

# 1. Verificar configuração
db = NFSeDatabase()
configs = db.get_config_nfse(cnpj_teste)

if not configs:
    print(f"\n❌ Sem configuração NFS-e!")
    sys.exit(1)

print(f"\n✅ Configuração encontrada:")
for cfg in configs:
    provedor, cod_municipio, inscricao, url = cfg
    print(f"   Provedor: {provedor}")
    print(f"   Município: {cod_municipio}")

# 2. Buscar certificado
certificados = db.main_db.get_certificados()
cert_info = None
for cert in certificados:
    if cert[0] == cnpj_teste:  # cnpj_cpf
        cert_info = cert
        break

if not cert_info:
    print(f"\n❌ Certificado não encontrado!")
    sys.exit(1)

cnpj, caminho_cert, senha, informante, cuf = cert_info
print(f"\n✅ Certificado: {caminho_cert}")

# 3. Tentar busca
print(f"\n🔍 Iniciando busca NFS-e...")
print(f"   Endpoint: Ambiente Nacional (ADN)")
print(f"   NSU inicial: 000000000000000")

try:
    service = NFSeService(
        certificado_path=caminho_cert,
        certificado_senha=senha,
        cnpj=cnpj
    )
    
    # Busca com NSU zero (primeira busca)
    resultado = service.buscar_nfse_distribuicao(
        nsu='000000000000000',
        max_docs=50
    )
    
    print(f"\n📊 Resultado:")
    if resultado and 'documentos' in resultado:
        total = len(resultado['documentos'])
        print(f"   ✅ Documentos encontrados: {total}")
        
        if total > 0:
            print(f"\n   Primeiros documentos:")
            for i, doc in enumerate(resultado['documentos'][:5], 1):
                print(f"      {i}. NSU: {doc.get('nsu', 'N/A')}")
        else:
            print(f"   ⚠️  Nenhum documento retornado")
            print(f"   💡 Isso pode significar:")
            print(f"      • Empresa não emite NFS-e")
            print(f"      • Empresa não está ativa no município")
            print(f"      • API sem dados para essa empresa")
    else:
        print(f"   ⚠️  Resposta vazia ou inválida")
        print(f"   Resposta recebida: {resultado}")
        
except Exception as e:
    print(f"\n❌ Erro na busca: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
