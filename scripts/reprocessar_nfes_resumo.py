"""
🔄 REPROCESSAR NF-e COM STATUS RESUMO
======================================

Este script busca todas as NF-e que têm xml_status='RESUMO' (dados vazios)
e tenta baixar o XML completo da SEFAZ usando a chave de acesso.

Execução: python reprocessar_nfes_resumo.py
"""

import sqlite3
import sys
import os
from datetime import datetime
from lxml import etree

# Adiciona o diretório atual ao path para importar os módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nfe_search import DatabaseManager, NFeService, extrair_nota_detalhada

print("=" * 80)
print("🔄 REPROCESSAMENTO DE NF-e COM STATUS RESUMO")
print("=" * 80)

# Inicializa database
db = DatabaseManager('notas.db')

# 1. Busca NF-e com status RESUMO
print("\n📊 1. BUSCANDO NF-e COM STATUS RESUMO")
print("-" * 80)

conn = sqlite3.connect('notas.db')
cursor = conn.execute("""
    SELECT chave, informante, nsu, tipo
    FROM notas_detalhadas 
    WHERE xml_status='RESUMO'
    AND (tipo='NFe' OR tipo='NF-e')
    ORDER BY atualizado_em DESC
""")

nfes_resumo = cursor.fetchall()
conn.close()

total = len(nfes_resumo)
print(f"\nEncontradas {total} NF-e com status RESUMO")

if total == 0:
    print("\n✅ Nenhuma NF-e pendente! Todas estão completas.")
    sys.exit(0)

# 2. Agrupa por informante
print("\n📋 Distribuição por informante:")
informantes_dict = {}
for chave, informante, nsu, tipo in nfes_resumo:
    if informante not in informantes_dict:
        informantes_dict[informante] = []
    informantes_dict[informante].append((chave, nsu))

for inf, lista in informantes_dict.items():
    print(f"   {inf}: {len(lista)} NF-e")

# 3. Confirma reprocessamento
print(f"\n⚠️ ATENÇÃO: Serão reprocessadas {total} NF-e")
print("   Isso fará consultas na SEFAZ para buscar os XMLs completos.")
print("   ")

resposta = input("Deseja continuar? (S/N): ")
if resposta.upper() != 'S':
    print("\n❌ Operação cancelada pelo usuário")
    sys.exit(0)

# 4. Reprocessa cada NF-e
print("\n\n🔄 2. INICIANDO REPROCESSAMENTO")
print("-" * 80)

sucessos = 0
erros = 0
nao_encontrados = 0

for idx, (chave, informante, nsu, tipo) in enumerate(nfes_resumo, 1):
    print(f"\n[{idx}/{total}] Chave: {chave[:25]}...")
    print(f"        Informante: {informante}, NSU: {nsu}")
    
    # Busca certificado do informante
    certs = db.get_certificados()
    cert_info = next((c for c in certs if c[3] == informante), None)
    
    if not cert_info:
        print(f"   ❌ Certificado não encontrado para informante {informante}")
        erros += 1
        continue
    
    cnpj, path, senha, _, cuf = cert_info
    print(f"        Certificado: {path}")
    
    # Cria serviço SOAP
    try:
        svc = NFeService(path, senha, cnpj, cuf)
        
        print(f"   🔍 Buscando XML completo na SEFAZ...")
        
        # Tenta buscar XML completo por chave
        xml_completo = svc.fetch_by_chave_dist(chave)
        
        if xml_completo and len(xml_completo) > 1000:  # XML mínimo tem ~1KB
            print(f"   ✅ XML completo obtido ({len(xml_completo)} bytes)")
            
            # Valida XML
            try:
                tree = etree.fromstring(xml_completo.encode('utf-8'))
                print(f"   ✅ XML válido")
                
                # Extrai dados detalhados (o parser está embutido no extrair_nota_detalhada)
                nota = extrair_nota_detalhada(xml_completo, None, db, chave, informante, nsu)
                
                print(f"   📊 Dados extraídos:")
                print(f"      Número: {nota.get('numero', 'N/A')}")
                print(f"      Data: {nota.get('data_emissao', 'N/A')}")
                print(f"      Emitente: {nota.get('nome_emitente', 'N/A')[:40]}")
                print(f"      Valor: {nota.get('valor', 'N/A')}")
                
                # Salva no banco
                db.salvar_nota_detalhada(nota)
                print(f"   ✅ Nota atualizada no banco!")
                
                sucessos += 1
                
            except Exception as e:
                print(f"   ❌ Erro ao processar XML: {e}")
                erros += 1
        
        elif xml_completo:
            print(f"   ⚠️ Resposta muito pequena ({len(xml_completo)} bytes) - possível erro")
            print(f"      Resposta: {xml_completo[:200]}")
            nao_encontrados += 1
        else:
            print(f"   ❌ Busca por chave retornou vazio")
            print(f"      Possíveis causas:")
            print(f"      - NF-e não autorizada para destinatário")
            print(f"      - Chave inválida")
            print(f"      - Erro temporário da SEFAZ")
            nao_encontrados += 1
    
    except Exception as e:
        print(f"   ❌ Erro ao buscar: {e}")
        import traceback
        traceback.print_exc()
        erros += 1

# 5. Resumo final
print("\n\n" + "=" * 80)
print("📊 RESUMO DO REPROCESSAMENTO")
print("=" * 80)

print(f"\nTotal de NF-e processadas: {total}")
print(f"   ✅ Sucessos: {sucessos} ({sucessos/total*100:.1f}%)")
print(f"   ❌ Erros: {erros} ({erros/total*100:.1f}%)")
print(f"   ⚠️ Não encontradas: {nao_encontrados} ({nao_encontrados/total*100:.1f}%)")

if sucessos > 0:
    print(f"\n✅ {sucessos} NF-e foram atualizadas com sucesso!")
    print(f"   Agora elas devem aparecer na interface com todos os dados.")

if nao_encontrados > 0:
    print(f"\n⚠️ {nao_encontrados} NF-e não puderam ser obtidas da SEFAZ")
    print(f"   Possíveis motivos:")
    print(f"   - Destinatário não tem permissão para baixar essas NF-e")
    print(f"   - NF-e cancelada ou denegada")
    print(f"   - Chave de acesso inválida")
    print(f"\n   Recomendação: Verificar manualmente essas chaves na SEFAZ")

if erros > 0:
    print(f"\n❌ {erros} NF-e tiveram erro durante processamento")
    print(f"   Verifique os logs acima para detalhes")

print("\n" + "=" * 80)
print("✅ Reprocessamento finalizado!")
print("=" * 80)
