"""
Script para testar ranges de NSU e ver quais retornam dados
"""
import sys
from nfse_search import NFSeDatabase
from modules.nfse_service import NFSeService

def testar_range_nsu():
    db = NFSeDatabase()
    
    # Buscar certificado configurado
    certs = db.get_certificados()
    cert_config = None
    
    for cert_row in certs:
        cnpj, caminho, senha, informante, cuf = cert_row
        configs = db.get_config_nfse(informante)
        if configs:
            cert_config = (cert_row, configs[0])
            break
    
    if not cert_config:
        print("❌ Nenhum certificado configurado encontrado")
        return
    
    cert_row, config_row = cert_config
    cnpj, caminho, senha, informante, cuf = cert_row
    provedor, codigo_municipio, inscricao, url_custom = config_row
    
    print(f"Testando certificado: {informante}")
    print(f"   Municipio: {codigo_municipio}")
    
    # Inicializar servico
    servico = NFSeService(
        cert_path=caminho,
        senha=senha,
        informante=informante,
        cuf=cuf,
        ambiente='producao'
    )
    
    # Testar ranges diferentes
    ranges = [
        (1, 10),      # Inicio
        (50, 60),     # Meio
        (100, 110),   # Mais alto
        (500, 510),   # Ainda mais alto
    ]
    
    for inicio, fim in ranges:
        print(f"\nTestando NSUs {inicio} a {fim}:")
        encontrados = 0
        
        for nsu in range(inicio, fim + 1):
            resultado = servico.consultar_nsu(nsu)
            if resultado:
                encontrados += 1
                print(f"   OK NSU {nsu}: DADOS ENCONTRADOS")
            else:
                print(f"   -- NSU {nsu}: vazio")
        
        print(f"   Total encontrado: {encontrados}/{fim - inicio + 1}")

if __name__ == "__main__":
    testar_range_nsu()
