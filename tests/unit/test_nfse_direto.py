#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de teste direto para NFS-e via API ADN
"""
import sys
import os

# Adiciona o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(__file__))

from nfse_search import NFSeService

# Configuração do teste
CNPJ = "33251845000109"
CODIGO_MUNICIPIO = "5002704"  # Campo Grande/MS
INSCRICAO_MUNICIPAL = ""  # Deixe vazio se não souber
DATA_INICIAL = "01/05/2025"
DATA_FINAL = "17/12/2025"

# Caminho do certificado (buscar do banco)
import sqlite3
conn = sqlite3.connect('nfe_data.db')
cursor = conn.execute("""
    SELECT caminho, senha FROM certificados_sefaz 
    WHERE cnpj_cpf = ? LIMIT 1
""", (CNPJ,))
row = cursor.fetchone()

if not row:
    print(f"❌ Certificado não encontrado para CNPJ {CNPJ}")
    sys.exit(1)

cert_path, senha = row
print(f"✅ Certificado encontrado: {cert_path}")

# Criar instância do serviço
service = NFSeService(cert_path, senha, CNPJ)

# Executar busca
print(f"\n🔍 Buscando NFS-e...")
print(f"   CNPJ: {CNPJ}")
print(f"   Município: {CODIGO_MUNICIPIO}")
print(f"   Período: {DATA_INICIAL} a {DATA_FINAL}\n")

resultado = service.buscar_ginfes(
    codigo_municipio=CODIGO_MUNICIPIO,
    inscricao_municipal=INSCRICAO_MUNICIPAL,
    data_inicial=DATA_INICIAL,
    data_final=DATA_FINAL
)

# Mostrar resultado
print("\n" + "="*80)
print("RESULTADO DA BUSCA")
print("="*80)
print(f"Status: {resultado['status']}")
print(f"Mensagem: {resultado['mensagem']}")

if 'erros' in resultado and resultado['erros']:
    print(f"\n⚠️  Erros encontrados:")
    for erro in resultado['erros']:
        print(f"   - {erro}")

if 'notas' in resultado and resultado['notas']:
    print(f"\n📄 Notas encontradas: {len(resultado['notas'])}")
    for nota in resultado['notas']:
        print(f"   - NFS-e {nota['numero']} - R$ {nota['valor']:.2f} - {nota['data_emissao']}")
else:
    print(f"\nℹ️  Nenhuma nota encontrada")

print("="*80)
