"""
Script de teste para verificar se o suporte a CTe está funcionando
"""
import sys
sys.path.insert(0, '.')

from nfe_search import DatabaseManager, setup_logger
from modules.cte_service import CTeService
from pathlib import Path
import logging

# Configura logger
setup_logger()
logger = logging.getLogger(__name__)

def testar_cte():
    """Testa busca de CTe para o primeiro certificado"""
    db = DatabaseManager(Path('notas.db'))
    
    # Pega primeiro certificado
    certs = list(db.get_certificados())
    if not certs:
        print("❌ Nenhum certificado encontrado")
        return False
    
    cnpj, path, senha, inf, cuf = certs[0]
    print(f"\n[TESTE] Testando CTe para certificado:")
    print(f"   CNPJ: {cnpj}")
    print(f"   Informante: {inf}")
    print(f"   cUF: {cuf}")
    
    try:
        # Tenta inicializar serviço CTe
        print(f"\n[INIT] Inicializando CTeService...")
        cte_svc = CTeService(path, senha, cnpj, cuf, ambiente='producao')
        print(f"[OK] CTeService inicializado com sucesso")
        
        # Busca último NSU
        last_nsu_cte = db.get_last_nsu_cte(inf)
        print(f"\n[NSU] Ultimo NSU CTe: {last_nsu_cte}")
        
        # Tenta primeira consulta
        print(f"\n[SEFAZ] Consultando SEFAZ para CTe...")
        resp = cte_svc.fetch_by_cnpj("CNPJ" if len(cnpj)==14 else "CPF", last_nsu_cte)
        
        if not resp:
            print(f"[ERRO] Sem resposta da SEFAZ")
            return False
        
        print(f"[OK] Resposta recebida ({len(resp)} bytes)")
        
        # Extrai cStat
        cstat = cte_svc.extract_cstat(resp)
        print(f"   cStat: {cstat}")
        
        # Extrai NSU
        ult_nsu = cte_svc.extract_last_nsu(resp)
        max_nsu = cte_svc.extract_max_nsu(resp)
        print(f"   ultNSU: {ult_nsu}")
        print(f"   maxNSU: {max_nsu}")
        
        # Tenta extrair documentos
        docs = list(cte_svc.extrair_docs(resp))
        print(f"\n[DOCS] Documentos CTe encontrados: {len(docs)}")
        
        if docs:
            for i, (nsu, xml, schema) in enumerate(docs[:3], 1):  # Mostra apenas 3 primeiros
                print(f"   {i}. NSU={nsu}, schema={schema}, tamanho={len(xml)} bytes")
        
        return True
        
    except Exception as e:
        print(f"\n[ERRO] Erro ao testar CTe: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TESTE DE SUPORTE A CTe")
    print("=" * 60)
    
    sucesso = testar_cte()
    
    print("\n" + "=" * 60)
    if sucesso:
        print("[OK] TESTE CONCLUIDO COM SUCESSO")
        print("\nO sistema esta pronto para buscar CTe!")
        print("Execute 'python nfe_search.py' para iniciar.")
    else:
        print("[AVISO] TESTE ENCONTROU PROBLEMAS")
        print("\nVerifique os logs acima para detalhes.")
    print("=" * 60)
