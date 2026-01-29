"""
Processa XMLs salvos em disco que ainda não foram inseridos em notas_detalhadas
"""
import sqlite3
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime
import re

BASE_DIR = Path(__file__).parent
db_path = BASE_DIR / 'notas_test.db'

print("=" * 80)
print("PROCESSANDO XMLs ÓRFÃOS")
print("=" * 80)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Busca XMLs que estão em xmls_baixados mas não em notas_detalhadas
cursor.execute("""
    SELECT x.chave, x.caminho_arquivo
    FROM xmls_baixados x
    LEFT JOIN notas_detalhadas n ON x.chave = n.chave
    WHERE x.caminho_arquivo IS NOT NULL
    AND n.chave IS NULL
    LIMIT 10
""")

xmls_orfaos = cursor.fetchall()
print(f"\n📊 Encontrados {len(xmls_orfaos)} XMLs salvos sem registro em notas_detalhadas")

if not xmls_orfaos:
    print("\n✅ Não há XMLs órfãos para processar!")
    conn.close()
    exit(0)

# Namespace NFe
ns = {
    'nfe': 'http://www.portalfiscal.inf.br/nfe'
}

processados = 0
erros = 0

for chave, caminho in xmls_orfaos:
    try:
        xml_file = Path(caminho)
        if not xml_file.exists():
            print(f"\n❌ Arquivo não existe: {xml_file.name}")
            erros += 1
            continue
        
        print(f"\n📄 Processando: {xml_file.name}")
        
        # Parse XML
        tree = ET.parse(str(xml_file))
        root = tree.getroot()
        
        # Tenta encontrar infNFe com ou sem namespace
        inf_nfe = root.find('.//nfe:infNFe', ns)
        if inf_nfe is None:
            inf_nfe = root.find('.//infNFe')
        
        if inf_nfe is None:
            print(f"   ⚠️ Não encontrou infNFe no XML")
            erros += 1
            continue
        
        # Extrai dados
        def get_text(path, parent=inf_nfe):
            elem = parent.find(path, ns)
            if elem is None:
                elem = parent.find(path.replace('nfe:', ''))
            return elem.text if elem is not None else None
        
        # Dados básicos
        numero = get_text('.//nfe:ide/nfe:nNF')
        data_emissao = get_text('.//nfe:ide/nfe:dhEmi')
        if data_emissao and 'T' in data_emissao:
            data_emissao = data_emissao.split('T')[0]
        
        tipo_doc = get_text('.//nfe:ide/nfe:tpNF')
        tipo = 'NF-e Saída' if tipo_doc == '1' else 'NF-e Entrada'
        
        valor = get_text('.//nfe:total/nfe:ICMSTot/nfe:vNF')
        
        # Emitente
        cnpj_emit = get_text('.//nfe:emit/nfe:CNPJ')
        nome_emit = get_text('.//nfe:emit/nfe:xNome')
        
        # Destinatário  
        cnpj_dest = get_text('.//nfe:dest/nfe:CNPJ')
        nome_dest = get_text('.//nfe:dest/nfe:xNome')
        
        # UF
        uf_emit = get_text('.//nfe:emit/nfe:enderEmit/nfe:UF')
        
        print(f"   📋 NF {numero} - {nome_emit}")
        print(f"      Valor: R$ {valor}")
        
        # Insere em notas_detalhadas
        cursor.execute("""
            INSERT OR IGNORE INTO notas_detalhadas (
                chave, numero, data_emissao, tipo, valor,
                cnpj_emitente, nome_emitente,
                cnpj_destinatario, nome_destinatario,
                uf, xml_status, data_processamento
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'COMPLETO', datetime('now'))
        """, (
            chave, numero, data_emissao, tipo, valor,
            cnpj_emit, nome_emit,
            cnpj_dest, nome_dest,
            uf_emit
        ))
        
        processados += 1
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        erros += 1

conn.commit()

print(f"\n" + "=" * 80)
print(f"RESULTADO:")
print(f"   ✅ Processados: {processados}")
print(f"   ❌ Erros: {erros}")
print(f"=" * 80)

# Mostra estado final
cursor.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status = 'COMPLETO'")
total_completas = cursor.fetchone()[0]

print(f"\n📊 Total de notas COMPLETAS agora: {total_completas}")

# Lista as primeiras 5
cursor.execute("""
    SELECT n.numero, n.nome_emitente, n.valor, x.caminho_arquivo
    FROM notas_detalhadas n
    LEFT JOIN xmls_baixados x ON n.chave = x.chave
    WHERE n.xml_status = 'COMPLETO'
    LIMIT 5
""")

print(f"\n📋 Notas disponíveis para export:")
for i, (num, emit, val, path) in enumerate(cursor.fetchall(), 1):
    tem_arquivo = "✅" if path and Path(path).exists() else "❌"
    print(f"   {i}. NF {num} - {emit} - R$ {val}")
    print(f"      {tem_arquivo} Arquivo em disco")

conn.close()

print(f"\n✅ Agora abra a interface e teste o Export!")
