#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para verificar se xml_status está correto no banco
comparando com os XMLs salvos no disco
"""

import sqlite3
from pathlib import Path
from lxml import etree

# Conecta no banco
conn = sqlite3.connect('notas.db')
cursor = conn.cursor()

# Busca todas as notas
cursor.execute('''
    SELECT chave, xml_status, nome_emitente, numero, informante
    FROM notas_detalhadas 
    WHERE xml_status IS NOT NULL
    ORDER BY RANDOM()
    LIMIT 20
''')

notas = cursor.fetchall()

print("="*100)
print("VERIFICAÇÃO: xml_status no BANCO vs XML no DISCO")
print("="*100)

for chave, xml_status_banco, nome_emitente, numero, informante in notas:
    # Procura XML no disco
    pasta_base = Path(f'xmls/{informante}')
    
    xml_encontrado = None
    xml_status_real = None
    
    # Procura em todas as subpastas
    if pasta_base.exists():
        for xml_file in pasta_base.rglob('*.xml'):
            if chave in xml_file.name:
                xml_encontrado = xml_file
                break
    
    if xml_encontrado and xml_encontrado.exists():
        try:
            with open(xml_encontrado, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            tree = etree.fromstring(xml_content.encode('utf-8'))
            root_tag = tree.tag.split('}')[-1] if '}' in tree.tag else tree.tag
            
            # Determina xml_status baseado na tag raiz
            if root_tag in ['nfeProc', 'cteProc', 'NFe', 'CTe']:
                xml_status_real = 'COMPLETO'
            elif root_tag == 'resNFe':
                xml_status_real = 'RESUMO'
            elif root_tag in ['resEvento', 'procEventoNFe', 'evento']:
                xml_status_real = 'EVENTO'
            else:
                xml_status_real = 'DESCONHECIDO'
            
            # Compara
            status_match = '✅' if xml_status_banco == xml_status_real else '❌'
            
            print(f"\n{status_match} Nota {numero or 'S/N'} - {nome_emitente or '(sem nome)'}:")
            print(f"   Chave: {chave[:25]}...")
            print(f"   Banco: {xml_status_banco}")
            print(f"   Disco: {xml_status_real} (tag raiz: {root_tag})")
            print(f"   Arquivo: {xml_encontrado.name}")
            
            if xml_status_banco != xml_status_real:
                print(f"   ⚠️ INCONSISTÊNCIA DETECTADA!")
        
        except Exception as e:
            print(f"\n⚠️ Erro ao ler XML {chave[:25]}...: {e}")
    else:
        print(f"\n❓ Nota {numero or 'S/N'} - Banco diz '{xml_status_banco}' mas XML não encontrado no disco")
        print(f"   Chave: {chave[:25]}...")

print("\n" + "="*100)
print("VERIFICAÇÃO CONCLUÍDA")
print("="*100)

conn.close()
