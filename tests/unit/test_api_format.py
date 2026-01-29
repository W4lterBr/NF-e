"""
Testa o formato EXATO retornado pela API
"""
from nfse_search import NFSeDatabase
from modules.nfse_service import NFSeService
import json

db = NFSeDatabase()
certs = db.get_certificados()

for cert_row in certs:
    cnpj, caminho, senha, informante, cuf = cert_row
    configs = db.get_config_nfse(informante)
    if configs:
        break

print(f"Testando com CNPJ: {informante}")

servico = NFSeService(
    cert_path=caminho,
    senha=senha,
    informante=informante,
    cuf=cuf,
    ambiente='producao'
)

# Testar NSU 1 (que sabemos ter dados)
print("\n" + "="*80)
print("Testando NSU 1 (impar - deveria ter dados):")
print("="*80)

resultado = servico.consultar_nsu(1)

print(f"Tipo do resultado: {type(resultado)}")

if isinstance(resultado, dict):
    print(f"Keys no dict: {list(resultado.keys())}")
    print(f"\nConteudo completo (primeiros 500 chars):")
    print(json.dumps(resultado, indent=2, ensure_ascii=False)[:500])
    
    if 'ArquivoXml' in resultado:
        print(f"\nArquivoXml presente: {len(resultado['ArquivoXml'])} chars")
        print(f"Primeiros 100 chars: {resultado['ArquivoXml'][:100]}")
    else:
        print("\nArquivoXml NAO ENCONTRADO!")
        print(f"Campos disponiveis: {list(resultado.keys())}")
elif isinstance(resultado, bytes):
    print(f"Bytes recebidos: {len(resultado)} bytes")
    print(f"Primeiros 100 bytes: {resultado[:100]}")
elif resultado is None:
    print("Resultado = None (404 ou erro)")
else:
    print(f"Tipo inesperado: {type(resultado)}")
    print(f"Conteudo: {str(resultado)[:200]}")
