#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teste: processa XMLs NFS-e já salvos em disco"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from nfe_search import salvar_nfse_detalhada

# Pega XMLs salvos
xmls_dir = Path(__file__).parent / "xmls" / "47539664000197"
xml_files = list(xmls_dir.rglob("NFSe_*.xml"))

print(f"🔍 Encontrados {len(xml_files)} XMLs de NFS-e")

notas_salvas = 0
for xml_path in xml_files[:10]:  # Processa apenas 10
    try:
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # NSU fictício (não importa para este teste)
        nsu = xml_path.stem.replace('NFSe_', '')
        informante = "47539664000197"
        
        # Salva no banco
        if salvar_nfse_detalhada(xml_content, nsu, informante):
            notas_salvas += 1
            print(f"✅ {xml_path.name} processada")
        else:
            print(f"❌ {xml_path.name} falhou")
        
    except Exception as e:
        print(f"❌ Erro ao processar {xml_path.name}: {e}")

print(f"\n{'='*70}")
print(f"✅ TESTE CONCLUÍDO: {notas_salvas}/{len(xml_files[:10])} NFS-e salvas")
print(f"{'='*70}")

# Verifica no banco
print("\n🔍 Verificando no banco...")
import sqlite3
conn = sqlite3.connect('notas.db')
cursor = conn.execute("SELECT numero, valor, nome_emitente, xml_status FROM notas_detalhadas WHERE tipo LIKE '%NFS%' ORDER BY numero LIMIT 5")
print("\n📋 Primeiras 5 NFS-e no banco:")
for row in cursor.fetchall():
    numero, valor, nome, status = row
    print(f"  • NFS-e #{numero} - R$ {valor} - {nome[:30]} - {status}")
