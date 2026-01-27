"""
Script para verificar se as notas marcadas como RESUMO 
realmente não possuem XML completo no disco
"""

import sqlite3
from pathlib import Path
from lxml import etree

# Caminho do banco de dados
DB_PATH = Path(__file__).parent / "notas.db"
DATA_DIR = Path(__file__).parent

def detectar_tipo_xml(xml_path):
    """Detecta o tipo de XML pelo root tag"""
    try:
        tree = etree.parse(str(xml_path))
        root = tree.getroot()
        tag = etree.QName(root).localname
        
        if tag in ['nfeProc', 'cteProc', 'NFe', 'CTe']:
            return 'COMPLETO'
        elif tag == 'resNFe':
            return 'RESUMO'
        elif tag in ['resEvento', 'procEventoNFe', 'evento']:
            return 'EVENTO'
        else:
            return f'DESCONHECIDO ({tag})'
    except Exception as e:
        return f'ERRO ({str(e)[:30]})'

def verificar_resumos():
    """Verifica se notas RESUMO realmente não têm XML no disco"""
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Busca todas as notas com status RESUMO
    cursor.execute("""
        SELECT chave, informante, tipo, data_emissao, nome_emitente, xml_status
        FROM notas_detalhadas 
        WHERE xml_status = 'RESUMO'
        ORDER BY data_emissao DESC
    """)
    
    notas_resumo = cursor.fetchall()
    total = len(notas_resumo)
    
    print("=" * 100)
    print(f"VERIFICAÇÃO DE NOTAS RESUMO - Total: {total}")
    print("=" * 100)
    
    # Contadores
    com_xml_completo = 0
    com_xml_resumo = 0
    com_xml_evento = 0
    sem_xml = 0
    erro_xml = 0
    chaves_invalidas = 0
    
    resultados = []
    
    for idx, (chave, informante, tipo, data_emissao, nome_emitente, xml_status) in enumerate(notas_resumo, 1):
        # Valida chave
        if not chave or len(chave) != 44 or not chave.isdigit():
            chaves_invalidas += 1
            tipo_invalido = "NFS-e" if "NFSE" in (chave or "").upper() else "Inválida"
            resultados.append({
                'idx': idx,
                'chave': chave[:50] if chave else 'N/A',
                'status_disco': f'CHAVE {tipo_invalido}',
                'resultado': '⚠️',
                'nome': nome_emitente or 'N/A'
            })
            continue
        
        # Extrai ano-mês da data
        if not data_emissao or len(data_emissao) < 7:
            # Tenta extrair da chave (posições 2-7 = AAMMDD)
            try:
                ano = '20' + chave[2:4]
                mes = chave[4:6]
                year_month = f"{ano}-{mes}"
            except:
                year_month = None
        else:
            year_month = data_emissao[:7]
        
        if not year_month:
            sem_xml += 1
            resultados.append({
                'idx': idx,
                'chave': chave[:20],
                'status_disco': 'Sem data',
                'resultado': '❌',
                'nome': nome_emitente or 'N/A'
            })
            continue
        
        # Tipo normalizado
        tipo_norm = (tipo or 'NFE').strip().upper().replace('-', '')
        
        # Possíveis localizações do XML
        xml_paths = [
            # Estrutura nova: xmls/informante/YYYY-MM/TIPO/chave.xml
            DATA_DIR / "xmls" / informante / year_month / tipo_norm / f"{chave}.xml",
            # Estrutura antiga: xmls/informante/YYYY-MM/chave.xml
            DATA_DIR / "xmls" / informante / year_month / f"{chave}.xml",
            # Pasta específica de chaves
            DATA_DIR / "xmls_chave" / f"{chave}.xml",
            # Pasta genérica
            DATA_DIR / "xml_extraidos" / f"{chave}.xml",
            DATA_DIR / "xml_NFs" / f"{chave}.xml",
        ]
        
        # Verifica se existe em algum local
        xml_encontrado = None
        for xml_path in xml_paths:
            if xml_path.exists():
                xml_encontrado = xml_path
                break
        
        if xml_encontrado:
            # Detecta tipo real do XML
            tipo_xml = detectar_tipo_xml(xml_encontrado)
            
            if tipo_xml == 'COMPLETO':
                com_xml_completo += 1
                resultado = '🔴'  # INCONSISTÊNCIA GRAVE
            elif tipo_xml == 'RESUMO':
                com_xml_resumo += 1
                resultado = '✅'  # CORRETO
            elif tipo_xml == 'EVENTO':
                com_xml_evento += 1
                resultado = '🟠'  # EVENTO (não deveria estar como RESUMO)
            else:
                erro_xml += 1
                resultado = '⚠️'
            
            resultados.append({
                'idx': idx,
                'chave': chave[:20],
                'status_disco': tipo_xml,
                'resultado': resultado,
                'nome': nome_emitente or 'N/A',
                'caminho': str(xml_encontrado.relative_to(DATA_DIR))
            })
        else:
            sem_xml += 1
            resultados.append({
                'idx': idx,
                'chave': chave[:20],
                'status_disco': 'SEM XML',
                'resultado': '✅',  # CORRETO (realmente é RESUMO)
                'nome': nome_emitente or 'N/A'
            })
    
    # Mostra resultados
    print("\n📋 AMOSTRA DOS PRIMEIROS 50 REGISTROS:")
    print("-" * 100)
    
    for r in resultados[:50]:
        caminho = r.get('caminho', '')
        caminho_str = f" → {caminho}" if caminho else ""
        print(f"{r['resultado']} [{r['idx']:3d}/{total}] {r['chave']}... | {r['status_disco']:<20} | {r['nome'][:30]}{caminho_str}")
    
    if total > 50:
        print(f"\n... (+{total - 50} registros omitidos)")
    
    # Estatísticas finais
    print("\n" + "=" * 100)
    print("📊 ESTATÍSTICAS FINAIS")
    print("=" * 100)
    print(f"Total de notas RESUMO no banco: {total}")
    print(f"Chaves inválidas (NFS-e, etc):  {chaves_invalidas} ({chaves_invalidas/total*100:.1f}%)")
    print()
    print(f"✅ SEM XML no disco (CORRETO):   {sem_xml} ({sem_xml/total*100:.1f}%)")
    print(f"✅ COM XML RESUMO (CORRETO):     {com_xml_resumo} ({com_xml_resumo/total*100:.1f}%)")
    print()
    print(f"🔴 COM XML COMPLETO (ERRO!):     {com_xml_completo} ({com_xml_completo/total*100:.1f}%)")
    print(f"🟠 COM XML EVENTO (ERRO!):       {com_xml_evento} ({com_xml_evento/total*100:.1f}%)")
    print(f"⚠️  ERRO AO LER XML:              {erro_xml} ({erro_xml/total*100:.1f}%)")
    print()
    
    # Total de inconsistências
    inconsistencias = com_xml_completo + com_xml_evento
    taxa_consistencia = (total - inconsistencias - chaves_invalidas) / (total - chaves_invalidas) * 100 if (total - chaves_invalidas) > 0 else 0
    
    print(f"🎯 Taxa de consistência:         {taxa_consistencia:.1f}%")
    print(f"❌ Total de inconsistências:     {inconsistencias} ({inconsistencias/total*100:.1f}%)")
    print("=" * 100)
    
    # Mostra detalhes das inconsistências
    if com_xml_completo > 0:
        print("\n🔴 INCONSISTÊNCIAS GRAVES (XML COMPLETO marcado como RESUMO):")
        print("-" * 100)
        for r in resultados:
            if r['status_disco'] == 'COMPLETO':
                print(f"  • {r['chave']}... | {r['nome'][:40]} | {r.get('caminho', 'N/A')}")
    
    if com_xml_evento > 0:
        print("\n🟠 EVENTOS MARCADOS COMO RESUMO:")
        print("-" * 100)
        for r in resultados:
            if r['status_disco'] == 'EVENTO':
                print(f"  • {r['chave']}... | {r['nome'][:40]} | {r.get('caminho', 'N/A')}")
    
    conn.close()

if __name__ == "__main__":
    verificar_resumos()
