"""
Teste de integração da manifestação PyNFe na interface
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from modules.manifestacao_service import ManifestacaoService
from modules.database import DatabaseManager

def testar_manifestacao():
    print("=" * 80)
    print("TESTE DE INTEGRAÇÃO - MANIFESTAÇÃO PyNFe")
    print("=" * 80)
    
    # Carregar certificado
    db_path = BASE_DIR / "notas.db"
    db = DatabaseManager(db_path)
    certs = db.load_certificates()
    
    cert = None
    for c in certs:
        if c.get('informante') == '33251845000109':
            cert = c
            break
    
    if not cert:
        print("Certificado não encontrado!")
        return
    
    print(f"\nCertificado: {cert['razao_social']}")
    print(f"CNPJ: {cert['cnpj_cpf']}")
    
    # Criar serviço
    srv = ManifestacaoService(cert['caminho'], cert['senha'])
    
    # Testar com chave conhecida (já manifestada - deve retornar duplicidade)
    chave_teste = "50260176093731001324550010010308551127082446"
    
    print(f"\nTestando manifestação...")
    print(f"Chave: {chave_teste}")
    print(f"Tipo: 210210 (Ciência da Operação)")
    
    sucesso, protocolo, mensagem, xml = srv.enviar_manifestacao(
        chave=chave_teste,
        tipo_evento='210210',
        cnpj_destinatario=cert['cnpj_cpf']
    )
    
    print(f"\n{'=' * 80}")
    print("RESULTADO:")
    print(f"{'=' * 80}")
    print(f"Sucesso: {sucesso}")
    print(f"Protocolo: {protocolo}")
    print(f"Mensagem: {mensagem}")
    
    if sucesso:
        print("\n✓ MANIFESTAÇÃO FUNCIONANDO CORRETAMENTE!")
        if "Duplicidade" in mensagem:
            print("  (Nota já foi manifestada anteriormente - comportamento esperado)")
    else:
        print("\n✗ Erro na manifestação")
        print(f"  Detalhes: {mensagem}")

if __name__ == "__main__":
    testar_manifestacao()
