"""
Script para analisar arquivos órfãos em detalhe.
Identifica se são arquivos legítimos que deveriam estar no banco.
"""

import sqlite3
import os
from pathlib import Path
from lxml import etree
from collections import Counter

DB_PATH = Path(__file__).parent / "notas_test.db"
XMLS_PATH = Path(__file__).parent / "xmls"

def analisar_xml_orfao(xml_path):
    """Analisa um XML órfão para extrair informações básicas."""
    try:
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        root = etree.fromstring(xml_content.encode('utf-8'))
        root_tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag
        
        # Tenta extrair chave
        chave = None
        ns_nfe = '{http://www.portalfiscal.inf.br/nfe}'
        ns_cte = '{http://www.portalfiscal.inf.br/cte}'
        
        # Para NFe
        chNFe = root.findtext(f'.//{ns_nfe}chNFe')
        if chNFe:
            chave = chNFe
        
        # Para CTe
        if not chave:
            chCTe = root.findtext(f'.//{ns_cte}chCTe')
            if chCTe:
                chave = chCTe
        
        # Para procNFe/procCTe
        if not chave:
            infNFe = root.find(f'.//{ns_nfe}infNFe')
            if infNFe is not None:
                chave_id = infNFe.attrib.get('Id', '')
                if chave_id:
                    chave = chave_id.replace('NFe', '').replace('CTe', '')[-44:]
        
        if not chave:
            infCTe = root.find(f'.//{ns_cte}infCte')
            if infCTe is not None:
                chave_id = infCTe.attrib.get('Id', '')
                if chave_id:
                    chave = chave_id.replace('NFe', '').replace('CTe', '')[-44:]
        
        return {
            'root_tag': root_tag,
            'chave': chave,
            'valido': chave is not None and len(chave) == 44
        }
    except Exception as e:
        return {
            'root_tag': 'ERRO',
            'chave': None,
            'valido': False,
            'erro': str(e)
        }

def main():
    print("=" * 80)
    print("🔍 ANÁLISE DETALHADA DE ARQUIVOS ÓRFÃOS")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Busca todas as chaves registradas no banco
    cur.execute("SELECT chave FROM xmls_baixados")
    chaves_banco = {row['chave'] for row in cur.fetchall()}
    print(f"\n📦 Chaves registradas no banco: {len(chaves_banco):,}")
    
    # Analisa arquivos XML no disco
    print(f"📁 Analisando pasta: {XMLS_PATH}")
    print("   Isso pode demorar alguns minutos...\n")
    
    xml_files = list(XMLS_PATH.rglob("*.xml"))
    print(f"📄 Total de arquivos .xml no disco: {len(xml_files):,}")
    
    # Categoriza arquivos
    orfaos_validos = []  # Chave válida mas não no banco
    orfaos_invalidos = []  # Sem chave ou chave inválida
    registrados = []  # Chave no banco
    
    tipos_orfaos = Counter()
    
    print("\n⏳ Processando arquivos...")
    for i, xml_file in enumerate(xml_files, 1):
        if i % 10000 == 0:
            print(f"   Processados: {i:,} / {len(xml_files):,}")
        
        nome = xml_file.stem
        
        # Se o nome do arquivo é uma chave (44 dígitos)
        if len(nome) == 44 and nome.isdigit():
            if nome in chaves_banco:
                registrados.append(xml_file)
            else:
                # Órfão com chave válida no nome
                info = analisar_xml_orfao(xml_file)
                tipos_orfaos[info['root_tag']] += 1
                orfaos_validos.append((xml_file, info))
        else:
            # Nome não é chave - analisa conteúdo
            info = analisar_xml_orfao(xml_file)
            tipos_orfaos[info['root_tag']] += 1
            
            if info['valido'] and info['chave'] not in chaves_banco:
                orfaos_validos.append((xml_file, info))
            else:
                orfaos_invalidos.append((xml_file, info))
    
    print(f"   ✅ Processamento concluído!")
    
    # ========================================
    # RESULTADOS
    # ========================================
    print("\n" + "=" * 80)
    print("📊 RESULTADOS DA ANÁLISE")
    print("=" * 80)
    
    print(f"\n✅ Arquivos registrados corretamente: {len(registrados):,}")
    print(f"⚠️ Órfãos com chave válida: {len(orfaos_validos):,}")
    print(f"❌ Órfãos sem chave válida: {len(orfaos_invalidos):,}")
    
    # Tipos de documentos órfãos
    print(f"\n📋 TIPOS DE DOCUMENTOS ÓRFÃOS:")
    print("-" * 80)
    for tipo, qtd in tipos_orfaos.most_common():
        print(f"  {tipo:20s}: {qtd:,}")
    
    # Exemplos de órfãos válidos
    if orfaos_validos:
        print(f"\n🔍 EXEMPLOS DE ÓRFÃOS COM CHAVE VÁLIDA (primeiros 10):")
        print("-" * 80)
        for i, (arquivo, info) in enumerate(orfaos_validos[:10], 1):
            print(f"\n  {i}. Arquivo: {arquivo.relative_to(XMLS_PATH)}")
            print(f"     Tipo: {info['root_tag']}")
            print(f"     Chave: {info['chave']}")
    
    # Exemplos de órfãos inválidos
    if orfaos_invalidos:
        print(f"\n❌ EXEMPLOS DE ÓRFÃOS SEM CHAVE VÁLIDA (primeiros 10):")
        print("-" * 80)
        for i, (arquivo, info) in enumerate(orfaos_invalidos[:10], 1):
            print(f"\n  {i}. Arquivo: {arquivo.name}")
            print(f"     Pasta: {arquivo.parent.relative_to(XMLS_PATH)}")
            print(f"     Tipo: {info['root_tag']}")
            if 'erro' in info:
                print(f"     Erro: {info['erro'][:100]}")
    
    # ========================================
    # ANÁLISE DE OMISSÃO
    # ========================================
    print("\n" + "=" * 80)
    print("🎯 ANÁLISE DE OMISSÃO")
    print("=" * 80)
    
    if len(orfaos_validos) == 0:
        print("\n✅ NENHUMA OMISSÃO DETECTADA!")
        print("   Todos os XMLs com chave válida estão registrados no banco.")
        print("   Os arquivos órfãos são arquivos de debug ou sem chave válida.")
    else:
        print(f"\n⚠️ POSSÍVEL OMISSÃO DETECTADA!")
        print(f"   {len(orfaos_validos):,} arquivos com chave válida não estão no banco.")
        
        # Verifica se são notas que deveriam estar no banco
        chaves_orfaos = {info['chave'] for _, info in orfaos_validos if info['chave']}
        
        # Verifica se essas chaves estão em notas_detalhadas
        if chaves_orfaos:
            placeholders = ','.join('?' * len(chaves_orfaos))
            cur.execute(f"""
                SELECT COUNT(*) as qtd 
                FROM notas_detalhadas 
                WHERE chave IN ({placeholders})
            """, list(chaves_orfaos))
            
            qtd_em_notas = cur.fetchone()['qtd']
            
            if qtd_em_notas > 0:
                print(f"\n   ⚠️ ATENÇÃO: {qtd_em_notas} dessas chaves estão em notas_detalhadas!")
                print(f"   Isso indica que houve erro no registro em xmls_baixados.")
                print(f"\n   💡 SOLUÇÃO: Execute o script de correção:")
                print(f"      python corrigir_caminhos_xmls.py")
            else:
                print(f"\n   ℹ️ Nenhuma dessas chaves está em notas_detalhadas.")
                print(f"   Podem ser XMLs baixados manualmente ou de teste.")
    
    # ========================================
    # RECOMENDAÇÕES
    # ========================================
    print("\n" + "=" * 80)
    print("💡 RECOMENDAÇÕES")
    print("=" * 80)
    
    if len(orfaos_invalidos) > 10000:
        print("\n⚠️ Grande quantidade de arquivos órfãos sem chave válida detectada.")
        print("   Provavelmente são arquivos de debug ou teste.")
        print("   Considere limpar a pasta 'Debug de notas' se necessário:")
        print(f"   - Total de arquivos: {len(orfaos_invalidos):,}")
    
    if len(orfaos_validos) > 0:
        print("\n⚠️ Arquivos órfãos com chave válida detectados.")
        print("   Verifique se são XMLs legítimos que deveriam estar no banco.")
        print("   Se necessário, crie um script para importá-los.")
    
    print("\n✅ Para garantir integridade completa:")
    print("   1. Execute: python corrigir_caminhos_xmls.py")
    print("   2. Execute: python verificar_omissoes.py")
    print("   3. Revise manualmente arquivos órfãos se houver suspeita de omissão")
    
    print("\n" + "=" * 80)
    
    conn.close()

if __name__ == "__main__":
    main()
