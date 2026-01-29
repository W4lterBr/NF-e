#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teste rápido: processa apenas os 10 primeiros XMLs do certificado 47539664000197"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from nfse_search import NFSeDatabase, logger
from modules.nfse_service import NFSeService, consultar_nfse_incremental

# Certificado que tem NFS-e
CNPJ = "47539664000197"
CERT_PATH = "C:/Arquivo Walter - Empresas/Certificados/CERTIFICADO DIGITAL PARTNESS FUTURA valido ate 21 07 2026.pfx"
SENHA = "Certificado"  # Senha padrão
CUF = 52
INFORMANTE = CNPJ

print("="*70)
print("TESTE: Processando apenas 10 NFS-e do certificado 47539664000197")
print("="*70)

db = NFSeDatabase()

# Inicializa serviço
nfse_service = NFSeService(
    cert_path=CERT_PATH,
    senha=SENHA,
    informante=INFORMANTE,
    cuf=CUF,
    ambiente='producao'
)

# FORÇA NSU=1 para reprocessar
print("\n🔄 Resetando NSU para começar do início...")
db.set_last_nsu_nfse(INFORMANTE, "0")

# Busca documentos
print(f"\n🔍 Buscando NFS-e (max 10)...")
documentos = consultar_nfse_incremental(
    db=db,
    cert_path=CERT_PATH,
    senha=SENHA,
    informante=INFORMANTE,
    busca_completa=False
)

print(f"\n✅ {len(documentos)} documento(s) encontrado(s)")

# Processa apenas os 10 primeiros
from buscar_nfse_auto import salvar_xml_nfse
from nfe_search import salvar_nfse_detalhada
from lxml import etree

notas_salvas = 0
for doc in documentos[:10]:  # Limita a 10
    try:
        xml_content = doc['xml']
        nsu = doc['nsu']
        
        # Parse rápido para pegar dados
        tree = etree.fromstring(xml_content.encode('utf-8'))
        ns = {'nfse': 'http://www.sped.fazenda.gov.br/nfse'}
        
        numero = tree.findtext('.//nfse:nNFSe', namespaces=ns) or str(nsu)
        data_emissao = tree.findtext('.//nfse:dhProc', namespaces=ns) or "2023-01-01"
        if 'T' in data_emissao:
            data_emissao = data_emissao.split('T')[0]
        
        # Salva XML
        caminho_xml = salvar_xml_nfse(db, CNPJ, xml_content, numero, data_emissao)
        
        if caminho_xml:
            # Salva no banco principal (notas_detalhadas)
            salvar_nfse_detalhada(xml_content, nsu, INFORMANTE)
            notas_salvas += 1
            print(f"✅ NFS-e {numero} salva (NSU {nsu})")
        
    except Exception as e:
        print(f"❌ Erro ao processar NSU {nsu}: {e}")
        continue

print(f"\n{'='*70}")
print(f"✅ TESTE CONCLUÍDO: {notas_salvas} NFS-e salvas")
print(f"{'='*70}")
