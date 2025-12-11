"""
Processa eventos salvos na pasta Eventos/ e atualiza o status das notas.
"""
from pathlib import Path
import xml.etree.ElementTree as ET
import sqlite3

BASE_DIR = Path(__file__).parent
XMLS_DIR = BASE_DIR / "xmls"

conn = sqlite3.connect('notas.db')

eventos_processados = 0
cancelamentos = 0
correcoes = 0

print("Processando eventos salvos...\n")

# Procura XMLs nas pastas de Eventos
for eventos_dir in XMLS_DIR.rglob("Eventos"):
    if not eventos_dir.is_dir():
        continue
    
    print(f"📁 {eventos_dir.relative_to(XMLS_DIR)}")
    
    for xml_file in eventos_dir.glob("*.xml"):
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Remove namespace
            ns = '{http://www.portalfiscal.inf.br/nfe}'
            
            # Extrai dados do evento
            chNFe = None
            tpEvento = None
            cStat = None
            xMotivo = None
            
            for elem in root.iter():
                tag = elem.tag.replace(ns, '')
                if tag == 'chNFe':
                    chNFe = elem.text
                elif tag == 'tpEvento':
                    tpEvento = elem.text
                elif tag == 'cStat':
                    cStat = elem.text
                elif tag == 'xMotivo':
                    xMotivo = elem.text
            
            if not chNFe or len(chNFe) != 44:
                continue
            
            # Verifica se a nota existe no banco
            nota_existe = conn.execute(
                "SELECT chave FROM notas_detalhadas WHERE chave = ?",
                (chNFe,)
            ).fetchone()
            
            if not nota_existe:
                continue
            
            # Atualiza status baseado no evento
            novo_status = None
            
            if tpEvento == '110111' and cStat == '135':  # Cancelamento
                novo_status = "Cancelamento de NF-e homologado"
                cancelamentos += 1
                print(f"  ❌ Cancelamento: {xml_file.name}")
            
            elif tpEvento == '110110' and cStat == '135':  # Carta correção
                novo_status = "Carta de Correção registrada"
                correcoes += 1
                print(f"  📝 Correção: {xml_file.name}")
            
            if novo_status:
                conn.execute(
                    "UPDATE notas_detalhadas SET status = ? WHERE chave = ?",
                    (novo_status, chNFe)
                )
                eventos_processados += 1
        
        except Exception as e:
            print(f"  ⚠ Erro em {xml_file.name}: {e}")
            continue

conn.commit()
conn.close()

print(f"\n=== RESULTADO ===")
print(f"Eventos processados: {eventos_processados}")
print(f"  • Cancelamentos: {cancelamentos}")
print(f"  • Correções: {correcoes}")
print(f"\n➜ Reinicie a interface para ver as mudanças!")
