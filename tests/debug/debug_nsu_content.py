"""
Teste para ver o conteudo exato retornado pela API
"""
import sys
from nfse_search import NFSeDatabase
from modules.nfse_service import NFSeService
import json

def debug_nsu_content():
    db = NFSeDatabase()
    certs = db.get_certificados()
    
    for cert_row in certs:
        cnpj, caminho, senha, informante, cuf = cert_row
        configs = db.get_config_nfse(informante)
        if configs:
            break
    
    if not configs:
        print("Nenhum certificado configurado")
        return
    
    print(f"Testando CNPJ: {informante}")
    
    servico = NFSeService(
        cert_path=caminho,
        senha=senha,
        informante=informante,
        cuf=cuf,
        ambiente='producao'
    )
    
    # Testar NSU 1 (ímpar - tem dados) e NSU 2 (par - vazio)
    for nsu in [1, 2, 3]:
        print(f"\n{'='*60}")
        print(f"NSU {nsu}:")
        print('='*60)
        
        resultado = servico.consultar_nsu(nsu)
        
        if resultado is None:
            print("  -> Retornou None")
        elif isinstance(resultado, dict):
            print("  -> Tipo: dict (JSON)")
            print(f"  -> Keys: {list(resultado.keys())}")
            print(f"  -> Content:\n{json.dumps(resultado, indent=2, ensure_ascii=False)}")
        elif isinstance(resultado, bytes):
            print(f"  -> Tipo: bytes")
            print(f"  -> Tamanho: {len(resultado)} bytes")
            print(f"  -> Primeiros 500 chars:")
            try:
                print(resultado[:500].decode('utf-8'))
            except:
                print(resultado[:500])
        else:
            print(f"  -> Tipo: {type(resultado)}")
            print(f"  -> Content: {resultado}")

if __name__ == "__main__":
    debug_nsu_content()
