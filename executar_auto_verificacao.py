"""
Script para executar auto-verificação diretamente via terminal
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from nfe_search import DatabaseManager, NFeService, salvar_xml_por_certificado
from lxml import etree

def log(msg):
    """Print com flush para aparecer imediatamente"""
    print(msg, flush=True)

def executar_auto_verificacao():
    """Executa auto-verificação das notas RESUMO"""
    
    # Conecta ao banco
    DB_PATH = BASE_DIR / "notas_test.db"
    db = DatabaseManager(DB_PATH)
    
    log("[AUTO-VERIFICAÇÃO] ========================================")
    log("[AUTO-VERIFICAÇÃO] Carregando notas RESUMO do banco...")
    
    # Busca notas RESUMO diretamente usando o banco SQLite
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT chave, informante, xml_status 
        FROM notas_detalhadas 
        WHERE xml_status = 'RESUMO'
        AND chave NOT IN (SELECT chave FROM notas_verificadas WHERE resultado IS NOT NULL)
        ORDER BY data_emissao DESC
    """)
    notas_resumo = [{'chave': row[0], 'informante': row[1], 'xml_status': row[2]} 
                    for row in cursor.fetchall()]
    conn.close()
    
    log(f"[AUTO-VERIFICAÇÃO] Total de notas RESUMO: {len(notas_resumo)}")
    
    if not notas_resumo:
        log("[AUTO-VERIFICAÇÃO] Nenhuma nota RESUMO pendente!")
        return
    
    # Carrega certificados
    certificados = db.get_certificados()
    if not certificados:
        log("[AUTO-VERIFICAÇÃO] ❌ Nenhum certificado configurado!")
        return
    
    # Converte para formato dict
    certs = []
    for cert in certificados:
        certs.append({
            'cnpj_cpf': cert[0],
            'caminho': cert[1],
            'senha': cert[2],
            'informante': cert[3],
            'cUF_autor': cert[4]
        })
    
    log(f"[AUTO-VERIFICAÇÃO] Certificados disponíveis: {len(certs)}")
    log("[AUTO-VERIFICAÇÃO] ========================================")
    
    encontrados = 0
    nao_encontrados = 0
    total = len(notas_resumo)
    
    for idx, item in enumerate(notas_resumo, 1):
        chave = item.get('chave')
        if not chave:
            continue
        
        # Detecta tipo (NF-e ou CT-e)
        modelo = chave[20:22] if len(chave) >= 22 else '55'
        is_cte = modelo == '57'
        tipo_doc = 'CT-e' if is_cte else 'NF-e'
        
        log(f"\n[AUTO-VERIFICAÇÃO] [{idx}/{total}] {tipo_doc}: {chave}")
        
        xml_encontrado = False
        resp_xml = None
        cert_usado = None
        
        # Tenta com cada certificado
        for cert_idx, cert in enumerate(certs, 1):
            cnpj_cert = cert.get('cnpj_cpf')
            senha_cert = cert.get('senha')
            caminho_cert = cert.get('caminho')
            cuf_cert = cert.get('cUF_autor')
            
            log(f"[AUTO-VERIFICAÇÃO]    Tentativa {cert_idx}/{len(certs)} - Certificado: {cnpj_cert} (UF: {cuf_cert})")
            
            try:
                # Cria serviço NF-e
                svc = NFeService(caminho_cert, senha_cert, cnpj_cert, cuf_cert)
                
                # Busca usando o método apropriado
                if is_cte:
                    resp_xml = svc.fetch_prot_cte(chave)
                else:
                    resp_xml = svc.fetch_prot_nfe(chave)
                
                if resp_xml:
                    # Verifica erros que indicam "tentar outro certificado"
                    erros_tentar_outro = ['217', '226', '404']
                    tem_erro_cert = any(f'<cStat>{cod}</cStat>' in resp_xml for cod in erros_tentar_outro)
                    
                    if tem_erro_cert:
                        # Identifica erro
                        if '<cStat>217</cStat>' in resp_xml:
                            log(f"[AUTO-VERIFICAÇÃO]       ❌ Nota não consta na base (217)")
                        elif '<cStat>226</cStat>' in resp_xml:
                            log(f"[AUTO-VERIFICAÇÃO]       ❌ UF divergente (226)")
                        elif '<cStat>404</cStat>' in resp_xml:
                            log(f"[AUTO-VERIFICAÇÃO]       ❌ Erro de namespace (404)")
                        continue
                    
                    # XML encontrado!
                    cert_usado = cert
                    xml_encontrado = True
                    log(f"[AUTO-VERIFICAÇÃO]    ✅ XML encontrado! Tamanho: {len(resp_xml)} bytes")
                    break
                else:
                    log(f"[AUTO-VERIFICAÇÃO]       ❌ Resposta vazia")
                    
            except Exception as e:
                error_detail = str(e)
                log(f"[AUTO-VERIFICAÇÃO]       ⚠️ Erro: {error_detail[:100]}")
                continue
        
        if xml_encontrado and resp_xml and cert_usado:
            try:
                # Parse e extrai XML completo
                tree = etree.fromstring(resp_xml.encode('utf-8') if isinstance(resp_xml, str) else resp_xml)
                
                # Log da estrutura do XML para debug
                root_tag = tree.tag.split('}')[-1] if '}' in tree.tag else tree.tag
                log(f"[AUTO-VERIFICAÇÃO]    🔍 Tag raiz do XML: {root_tag}")
                
                # Lista todas as tags filhas principais
                for child in tree:
                    child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    log(f"[AUTO-VERIFICAÇÃO]       - Child tag: {child_tag}")
                
                if is_cte:
                    NS = {'cte': 'http://www.portalfiscal.inf.br/cte'}
                    
                    # Tenta diferentes caminhos para encontrar o CT-e
                    proc_node = tree.find('.//cte:cteProc', namespaces=NS)
                    if proc_node is None:
                        proc_node = tree.find('.//cte:CTe', namespaces=NS)
                    if proc_node is None:
                        # Procura sem namespace
                        proc_node = tree.find('.//cteProc')
                    if proc_node is None:
                        proc_node = tree.find('.//CTe')
                    
                    if proc_node is not None:
                        log(f"[AUTO-VERIFICAÇÃO]    📦 Encontrado nó: {proc_node.tag}")
                        xml_completo = etree.tostring(proc_node, encoding='utf-8').decode()
                    else:
                        log(f"[AUTO-VERIFICAÇÃO]    ⚠️ Nó cteProc/CTe não encontrado, salvando resposta completa")
                        xml_completo = resp_xml
                else:
                    NS = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
                    
                    # Tenta diferentes caminhos para encontrar a NF-e
                    proc_node = tree.find('.//nfe:nfeProc', namespaces=NS)
                    if proc_node is None:
                        proc_node = tree.find('.//nfe:NFe', namespaces=NS)
                    if proc_node is None:
                        # Procura sem namespace
                        proc_node = tree.find('.//nfeProc')
                    if proc_node is None:
                        proc_node = tree.find('.//NFe')
                    
                    if proc_node is not None:
                        log(f"[AUTO-VERIFICAÇÃO]    📦 Encontrado nó: {proc_node.tag}")
                        xml_completo = etree.tostring(proc_node, encoding='utf-8').decode()
                    else:
                        log(f"[AUTO-VERIFICAÇÃO]    ⚠️ Nó nfeProc/NFe não encontrado, salvando resposta completa")
                        xml_completo = resp_xml
                
                # Salva XML
                cnpj_salvar = cert_usado.get('cnpj_cpf')
                caminho_xml = salvar_xml_por_certificado(xml_completo, cnpj_salvar)
                
                if caminho_xml:
                    log(f"[AUTO-VERIFICAÇÃO]    💾 Salvo em: {caminho_xml}")
                    
                    # Atualiza banco - registra XML
                    db.registrar_xml(chave, cnpj_salvar, caminho_xml)
                    
                    # Atualiza status da nota
                    import sqlite3
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute("""
                        UPDATE notas_detalhadas 
                        SET xml_status = 'COMPLETO'
                        WHERE chave = ?
                    """, (chave,))
                    conn.commit()
                    conn.close()
                    
                    # Marca como verificada
                    import sqlite3
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute("""
                        INSERT OR REPLACE INTO notas_verificadas (chave, resultado, verificada_em)
                        VALUES (?, 'xml_completo', datetime('now'))
                    """, (chave,))
                    conn.commit()
                    conn.close()
                    
                    encontrados += 1
                    log(f"[AUTO-VERIFICAÇÃO]    ✅ Sucesso! Total encontrados: {encontrados}")
                else:
                    log(f"[AUTO-VERIFICAÇÃO]    ❌ Erro ao salvar XML")
                    nao_encontrados += 1
                    
            except Exception as e:
                log(f"[AUTO-VERIFICAÇÃO]    ❌ Erro ao processar: {str(e)}")
                nao_encontrados += 1
        else:
            nao_encontrados += 1
            # Marca como verificada (não encontrado)
            import sqlite3
            conn = sqlite3.connect(DB_PATH)
            conn.execute("""
                INSERT OR REPLACE INTO notas_verificadas (chave, resultado, verificada_em)
                VALUES (?, 'nao_encontrado', datetime('now'))
            """, (chave,))
            conn.commit()
            conn.close()
            log(f"[AUTO-VERIFICAÇÃO]    ❌ XML não encontrado em nenhum certificado")
    
    log(f"\n[AUTO-VERIFICAÇÃO] ========================================")
    log(f"[AUTO-VERIFICAÇÃO] Verificação concluída!")
    log(f"[AUTO-VERIFICAÇÃO] ✅ Encontrados: {encontrados}")
    log(f"[AUTO-VERIFICAÇÃO] ❌ Não encontrados: {nao_encontrados}")
    log(f"[AUTO-VERIFICAÇÃO] ========================================")

if __name__ == "__main__":
    executar_auto_verificacao()
