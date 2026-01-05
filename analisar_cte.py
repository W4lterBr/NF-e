#!/usr/bin/env python3
"""Analisa o XML do CT-e específico."""

from lxml import etree
from pathlib import Path

xml_path = Path("xmls/01773924000193/2025-12/CTe/50251203232675000154570010056290311009581385.xml")

if not xml_path.exists():
    print(f"❌ Arquivo não encontrado: {xml_path}")
    exit(1)

print(f"\n{'='*80}")
print(f"ANÁLISE DO CT-e")
print(f"{'='*80}\n")
print(f"Arquivo: {xml_path}")
print(f"Tamanho: {xml_path.stat().st_size} bytes\n")

content = xml_path.read_text(encoding='utf-8')
tree = etree.fromstring(content.encode('utf-8'))

root_tag = tree.tag.split('}')[-1] if '}' in tree.tag else tree.tag
print(f"Tag raiz: {root_tag}")

ns_cte = {'cte': 'http://www.portalfiscal.inf.br/cte'}

# Extrai informações básicas
chave = tree.findtext('.//cte:chCTe', namespaces=ns_cte)
print(f"Chave: {chave}\n")

# Verifica se é evento ou documento completo
if root_tag in ['procEventoCTe', 'eventoCTe']:
    print("📋 TIPO: EVENTO DE CT-e\n")
    
    # Dados do evento
    tp_evento = tree.findtext('.//cte:tpEvento', namespaces=ns_cte)
    desc_evento = tree.findtext('.//cte:descEvento', namespaces=ns_cte) or tree.findtext('.//cte:xEvento', namespaces=ns_cte)
    cstat_evento = tree.findtext('.//cte:cStat', namespaces=ns_cte)
    xmotivo_evento = tree.findtext('.//cte:xMotivo', namespaces=ns_cte)
    dh_evento = tree.findtext('.//cte:dhEvento', namespaces=ns_cte)
    nseq_evento = tree.findtext('.//cte:nSeqEvento', namespaces=ns_cte)
    
    print(f"Tipo de Evento: {tp_evento}")
    if tp_evento == '110111':
        print("   → 🚫 CANCELAMENTO DE CT-e")
    elif tp_evento == '110110':
        print("   → ✅ Carta de Correção")
    
    print(f"\nDescrição: {desc_evento}")
    print(f"Status (cStat): {cstat_evento}")
    if cstat_evento == '135':
        print("   → ✅ EVENTO HOMOLOGADO")
    
    print(f"Motivo: {xmotivo_evento}")
    print(f"Data/Hora: {dh_evento}")
    print(f"Sequência: {nseq_evento}")
    
    # Chave do CT-e relacionado
    ch_cte_rel = tree.findtext('.//cte:chCTe', namespaces=ns_cte)
    print(f"\nCT-e relacionado: {ch_cte_rel}")
    
elif root_tag in ['cteProc', 'CTe']:
    print("📄 TIPO: CT-e COMPLETO\n")
    
    # Dados do protocolo
    cstat = tree.findtext('.//cte:cStat', namespaces=ns_cte)
    xmotivo = tree.findtext('.//cte:xMotivo', namespaces=ns_cte)
    nprot = tree.findtext('.//cte:nProt', namespaces=ns_cte)
    
    print(f"Status (cStat): {cstat}")
    print(f"Motivo: {xmotivo}")
    print(f"Protocolo: {nprot}")
    
    # Dados do CT-e
    ncte = tree.findtext('.//cte:nCT', namespaces=ns_cte)
    dh_emi = tree.findtext('.//cte:dhEmi', namespaces=ns_cte)
    emit_cnpj = tree.findtext('.//cte:emit/cte:CNPJ', namespaces=ns_cte)
    emit_nome = tree.findtext('.//cte:emit/cte:xNome', namespaces=ns_cte)
    dest_cnpj = tree.findtext('.//cte:dest/cte:CNPJ', namespaces=ns_cte)
    dest_nome = tree.findtext('.//cte:dest/cte:xNome', namespaces=ns_cte)
    valor = tree.findtext('.//cte:vCarga', namespaces=ns_cte) or tree.findtext('.//cte:vTPrest', namespaces=ns_cte)
    
    print(f"\nNúmero: {ncte}")
    print(f"Emissão: {dh_emi}")
    print(f"Emitente: {emit_nome} (CNPJ: {emit_cnpj})")
    print(f"Destinatário: {dest_nome} (CNPJ: {dest_cnpj})")
    print(f"Valor: R$ {valor}")
    
elif root_tag == 'resCTe':
    print("📝 TIPO: RESUMO DE CT-e\n")
    
else:
    print(f"⚠️  TIPO DESCONHECIDO: {root_tag}\n")

# Busca eventos no mesmo CT-e
print(f"\n{'='*80}")
print("PROCURANDO EVENTOS DO CT-e")
print(f"{'='*80}\n")

eventos_dir = xml_path.parent.parent.parent / "Eventos"
if eventos_dir.exists():
    eventos_found = list(eventos_dir.glob(f"*{chave}*.xml"))
    if eventos_found:
        print(f"✅ {len(eventos_found)} evento(s) encontrado(s):\n")
        for evt in eventos_found:
            print(f"📄 {evt.name}")
            evt_content = evt.read_text(encoding='utf-8')
            evt_tree = etree.fromstring(evt_content.encode('utf-8'))
            tp = evt_tree.findtext('.//cte:tpEvento', namespaces=ns_cte)
            desc = evt_tree.findtext('.//cte:descEvento', namespaces=ns_cte)
            cstat_evt = evt_tree.findtext('.//cte:cStat', namespaces=ns_cte)
            print(f"   Tipo: {tp} ({desc})")
            print(f"   Status: {cstat_evt}")
            print()
    else:
        print("ℹ️  Nenhum evento encontrado para esta chave")
else:
    print(f"⚠️  Pasta de eventos não existe: {eventos_dir}")

print(f"{'='*80}\n")
