"""
Teste de consulta via Distribuição DFe por chave específica
Útil para XMLs antigos (>180 dias) que não estão mais no ConsultaProtocolo
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from nfe_search import NFeService, DatabaseManager, setup_logger

# Configura logger
logger = setup_logger()

def test_dist_por_chave():
    """Testa consulta por chave via Distribuição DFe"""
    
    print("\n" + "="*60)
    print("🧪 TESTE: Distribuição DFe por Chave")
    print("="*60 + "\n")
    
    # Conecta ao banco
    db = DatabaseManager(BASE_DIR / "notas.db")
    
    # Busca certificados
    certificados = db.get_certificados()
    if not certificados:
        print("❌ Nenhum certificado encontrado no banco de dados")
        return
    
    # Usa o primeiro certificado (retorna tupla)
    cert = certificados[0]
    cnpj, caminho, senha, informante, cuf = cert
    
    print(f"🔢 CNPJ: {cnpj}")
    print(f"📁 Informante: {informante}")
    print(f"📍 UF: {cuf}\n")
    
    # Cria serviço NF-e
    service = NFeService(
        caminho,
        senha,
        informante,
        cuf
    )
    
    # Solicita chave para testar
    print("Digite uma chave de NF-e para testar (44 dígitos):")
    print("(Deixe vazio para buscar automaticamente do banco)\n")
    
    chave = input("Chave: ").strip()
    
    if not chave:
        # Busca qualquer chave do banco para testar
        with db._connect() as conn:
            row = conn.execute("""
                SELECT chave, data_emissao, numero, nome_emitente
                FROM notas_detalhadas 
                WHERE tipo = 'NF-e'
                AND LENGTH(chave) = 44
                ORDER BY data_emissao ASC
                LIMIT 1
            """).fetchone()
            
            if row:
                chave = row[0]
                data = row[1]
                numero = row[2]
                emit = row[3]
                print(f"✅ Usando chave do banco:")
                print(f"   Chave: {chave}")
                print(f"   Nota: {numero}")
                print(f"   Data: {data}")
                print(f"   Emitente: {emit[:50]}...\n")
            else:
                print("❌ Nenhuma chave encontrada no banco")
                print("\n💡 Dica: Execute o sistema e busque notas primeiro,")
                print("         ou execute novamente e insira uma chave manualmente\n")
                return
    
    if len(chave) != 44:
        print(f"❌ Chave inválida (deve ter 44 dígitos, tem {len(chave)})")
        return
    
    print("\n" + "-"*60)
    print("🔍 Testando ConsultaProtocolo (método antigo)")
    print("-"*60 + "\n")
    
    resp_protocolo = service.fetch_prot_nfe(chave)
    
    if resp_protocolo:
        resp_lower = resp_protocolo.lower()
        is_only_protocol = (
            '<retconssit' in resp_lower and 
            '<protnfe' in resp_lower and
            '<nfeproc' not in resp_lower
        )
        
        if is_only_protocol:
            print("⚠️  ConsultaProtocolo retornou apenas PROTOCOLO")
            print("    (XML completo não disponível por esse método)\n")
        else:
            print("✅ ConsultaProtocolo retornou XML COMPLETO")
            print(f"   Tamanho: {len(resp_protocolo)} bytes\n")
    else:
        print("❌ ConsultaProtocolo não retornou resposta\n")
    
    print("\n" + "-"*60)
    print("🔑 Testando Distribuição DFe por Chave (método novo)")
    print("-"*60 + "\n")
    
    resp_dist = service.fetch_by_chave_dist(chave)
    
    if resp_dist:
        resp_lower = resp_dist.lower()
        
        # Verifica o que foi retornado
        has_nfeproc = '<nfeproc' in resp_lower
        has_nfe = '<nfe' in resp_lower and '<nfe:' not in resp_lower  # NFe completa
        has_resnfe = '<resnfe' in resp_lower
        has_protnfe = '<protnfe' in resp_lower
        
        print(f"📊 Análise da resposta:")
        print(f"   • Tamanho: {len(resp_dist)} bytes")
        print(f"   • nfeProc: {'✅ Sim' if has_nfeproc else '❌ Não'}")
        print(f"   • NFe: {'✅ Sim' if has_nfe else '❌ Não'}")
        print(f"   • resNFe (resumo): {'✅ Sim' if has_resnfe else '❌ Não'}")
        print(f"   • protNFe (protocolo): {'✅ Sim' if has_protnfe else '❌ Não'}")
        print()
        
        if has_nfeproc or has_nfe:
            print("🎉 SUCESSO! Distribuição DFe retornou XML COMPLETO!")
            print("   Este método funciona para XMLs antigos (>180 dias)")
            print()
            
            # Salva XML de teste
            test_file = BASE_DIR / "test_xml_dist_por_chave.xml"
            test_file.write_text(resp_dist, encoding='utf-8')
            print(f"💾 XML salvo em: {test_file}")
            
        elif has_resnfe:
            print("⚠️  Distribuição DFe retornou apenas RESUMO")
            print("   XML completo não está disponível")
            
        elif has_protnfe:
            print("⚠️  Distribuição DFe retornou apenas PROTOCOLO")
            print("   XML completo não está disponível")
            
        else:
            print("❓ Resposta desconhecida da Distribuição DFe")
    else:
        print("❌ Distribuição DFe não retornou resposta")
    
    print("\n" + "="*60)
    print("✅ Teste concluído!")
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        test_dist_por_chave()
    except KeyboardInterrupt:
        print("\n\n⚠️  Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n\n❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
