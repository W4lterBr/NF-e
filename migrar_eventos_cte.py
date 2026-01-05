"""
Script de migração: Processa eventos de CT-e já baixados para atualizar status.
"""

from pathlib import Path
from lxml import etree
import sqlite3

print("=" * 80)
print("MIGRAÇÃO: Processando Eventos de CT-e Já Baixados")
print("=" * 80)

# Conecta no banco
conn = sqlite3.connect("notas.db")

# Busca todos os eventos de CT-e no banco
cursor = conn.execute("""
    SELECT chave, tipo, xml_status, status 
    FROM notas_detalhadas 
    WHERE tipo = 'CTe' AND xml_status = 'EVENTO'
""")

eventos = cursor.fetchall()
print(f"\n📊 Eventos de CT-e encontrados no banco: {len(eventos)}")

if not eventos:
    print("✅ Nenhum evento de CT-e para processar")
    conn.close()
    exit(0)

# Busca XMLs de eventos
xmls_dir = Path("xmls")
eventos_processados = 0
cancelamentos_detectados = 0

for chave_evento, tipo, xml_status, status_atual in eventos:
    print(f"\n🔍 Processando evento {chave_evento}...")
    
    # Busca XML do evento (pode estar em várias pastas)
    xmls_found = list(xmls_dir.rglob(f"*{chave_evento}*.xml"))
    
    if not xmls_found:
        print(f"  ⚠️ XML não encontrado para {chave_evento}")
        continue
    
    # Processa primeiro XML encontrado
    xml_file = xmls_found[0]
    print(f"  📄 Arquivo: {xml_file}")
    
    try:
        # Lê XML
        xml_text = xml_file.read_text(encoding='utf-8')
        root = etree.fromstring(xml_text.encode('utf-8'))
        
        # Extrai dados do evento
        ch_cte = root.findtext('.//{http://www.portalfiscal.inf.br/cte}chCTe')
        tp_evento = root.findtext('.//{http://www.portalfiscal.inf.br/cte}tpEvento')
        c_stat = root.findtext('.//{http://www.portalfiscal.inf.br/cte}cStat')
        x_evento = root.findtext('.//{http://www.portalfiscal.inf.br/cte}xEvento')
        
        print(f"  📋 Evento:")
        print(f"     chCTe: {ch_cte}")
        print(f"     tpEvento: {tp_evento}")
        print(f"     cStat: {c_stat}")
        print(f"     xEvento: {x_evento}")
        
        # Verifica se é cancelamento autorizado
        if tp_evento == '110111' and c_stat == '135':
            # Atualiza status da nota relacionada
            novo_status = "Cancelamento de CT-e homologado"
            
            conn.execute("""
                UPDATE notas_detalhadas 
                SET status = ? 
                WHERE chave = ?
            """, (novo_status, ch_cte))
            conn.commit()
            
            print(f"  ✅ Status atualizado: {ch_cte} → {novo_status}")
            cancelamentos_detectados += 1
        
        eventos_processados += 1
        
    except Exception as e:
        print(f"  ❌ Erro ao processar: {e}")

conn.close()

print("\n" + "=" * 80)
print(f"📊 RESULTADO:")
print(f"   Eventos processados: {eventos_processados}")
print(f"   Cancelamentos detectados: {cancelamentos_detectados}")
print("=" * 80)
