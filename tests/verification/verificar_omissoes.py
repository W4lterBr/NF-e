"""
Script para verificar se há omissão de XMLs no armazenamento.

Verifica:
1. Todas as notas no banco têm XML salvo?
2. Todos os XMLs salvos estão registrados no banco?
3. Há notas sem caminho_arquivo?
4. Há arquivos órfãos (no disco mas não no banco)?
"""

import sqlite3
import os
from pathlib import Path
from collections import defaultdict

DB_PATH = Path(__file__).parent / "notas_test.db"
XMLS_PATH = Path(__file__).parent / "xmls"

def main():
    print("=" * 80)
    print("🔍 VERIFICAÇÃO DE OMISSÕES NO ARMAZENAMENTO DE XMLs")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # ========================================
    # 1. NOTAS NO BANCO vs XMLs SALVOS
    # ========================================
    print("\n📊 1. NOTAS NO BANCO DE DADOS")
    print("-" * 80)
    
    # Total de notas
    cur.execute("SELECT COUNT(*) as total FROM notas_detalhadas")
    total_notas = cur.fetchone()['total']
    print(f"Total de notas detalhadas: {total_notas:,}")
    
    # Por status
    cur.execute("""
        SELECT xml_status, COUNT(*) as qtd 
        FROM notas_detalhadas 
        GROUP BY xml_status
    """)
    print("\nPor status:")
    for row in cur.fetchall():
        status = row['xml_status'] or 'NULL'
        qtd = row['qtd']
        print(f"  {status:12s}: {qtd:,}")
    
    # ========================================
    # 2. XMLs REGISTRADOS NO BANCO
    # ========================================
    print("\n📦 2. XMLs REGISTRADOS (xmls_baixados)")
    print("-" * 80)
    
    cur.execute("SELECT COUNT(*) as total FROM xmls_baixados")
    total_xmls = cur.fetchone()['total']
    print(f"Total de XMLs registrados: {total_xmls:,}")
    
    # Com caminho vs sem caminho
    cur.execute("""
        SELECT 
            COUNT(CASE WHEN caminho_arquivo IS NOT NULL THEN 1 END) as com_caminho,
            COUNT(CASE WHEN caminho_arquivo IS NULL THEN 1 END) as sem_caminho
        FROM xmls_baixados
    """)
    row_caminho = cur.fetchone()
    print(f"  ✅ Com caminho_arquivo: {row_caminho['com_caminho']:,}")
    print(f"  ⚠️ Sem caminho_arquivo: {row_caminho['sem_caminho']:,}")
    
    if row_caminho['sem_caminho'] > 0:
        print("\n  ⚠️ ATENÇÃO: Há XMLs sem caminho registrado!")
        print("  Execute: python corrigir_caminhos_xmls.py")
    
    # ========================================
    # 3. NOTAS SEM XML REGISTRADO
    # ========================================
    print("\n🔍 3. NOTAS SEM XML REGISTRADO")
    print("-" * 80)
    
    cur.execute("""
        SELECT 
            nd.xml_status,
            COUNT(*) as qtd
        FROM notas_detalhadas nd
        LEFT JOIN xmls_baixados xb ON nd.chave = xb.chave
        WHERE xb.chave IS NULL
        GROUP BY nd.xml_status
    """)
    
    notas_sem_xml = cur.fetchall()
    if notas_sem_xml:
        print("  ⚠️ Há notas no banco sem XML registrado:")
        total_sem_xml = 0
        for row in notas_sem_xml:
            status = row['xml_status'] or 'NULL'
            qtd = row['qtd']
            total_sem_xml += qtd
            print(f"    {status:12s}: {qtd:,}")
        print(f"\n  TOTAL SEM XML: {total_sem_xml:,}")
        
        # Mostra exemplos
        cur.execute("""
            SELECT nd.chave, nd.numero, nd.xml_status, nd.informante
            FROM notas_detalhadas nd
            LEFT JOIN xmls_baixados xb ON nd.chave = xb.chave
            WHERE xb.chave IS NULL
            LIMIT 5
        """)
        print("\n  Exemplos (primeiras 5):")
        for row in cur.fetchall():
            print(f"    Chave: {row['chave']}, Número: {row['numero']}, Status: {row['xml_status']}")
    else:
        print("  ✅ Todas as notas têm XML registrado!")
    
    # ========================================
    # 4. ARQUIVOS NO DISCO vs BANCO
    # ========================================
    print("\n💾 4. ARQUIVOS NO DISCO")
    print("-" * 80)
    
    if not XMLS_PATH.exists():
        print(f"  ⚠️ Pasta xmls não encontrada: {XMLS_PATH}")
    else:
        # Conta arquivos XML no disco
        xml_files = list(XMLS_PATH.rglob("*.xml"))
        print(f"Total de arquivos .xml no disco: {len(xml_files):,}")
        
        # Agrupa por tipo de pasta
        por_tipo = defaultdict(int)
        for xml_file in xml_files:
            # Obtém o tipo pela pasta pai (NFe, CTe, Resumos, Eventos, Outros)
            tipo_pasta = xml_file.parent.name
            if tipo_pasta and not tipo_pasta.startswith('20'):  # Ignora pastas de data
                por_tipo[tipo_pasta] += 1
        
        print("\nPor tipo de pasta:")
        for tipo, qtd in sorted(por_tipo.items()):
            print(f"  {tipo:12s}: {qtd:,}")
        
        # ========================================
        # 5. ARQUIVOS ÓRFÃOS (no disco mas não no banco)
        # ========================================
        print("\n🔍 5. VERIFICAÇÃO DE ARQUIVOS ÓRFÃOS")
        print("-" * 80)
        
        # Busca todas as chaves registradas no banco
        cur.execute("SELECT chave FROM xmls_baixados")
        chaves_banco = {row['chave'] for row in cur.fetchall()}
        
        print(f"Chaves no banco: {len(chaves_banco):,}")
        print("Analisando arquivos no disco...")
        
        orfaos = []
        chaves_disco = set()
        
        for xml_file in xml_files:
            nome = xml_file.stem  # Nome sem extensão
            
            # Se o nome é uma chave (44 dígitos)
            if len(nome) == 44 and nome.isdigit():
                chaves_disco.add(nome)
                if nome not in chaves_banco:
                    orfaos.append(xml_file)
        
        print(f"Chaves no disco: {len(chaves_disco):,}")
        
        if orfaos:
            print(f"\n  ⚠️ Encontrados {len(orfaos)} arquivos órfãos (no disco mas não no banco):")
            for i, arq in enumerate(orfaos[:10], 1):
                print(f"    {i}. {arq.relative_to(XMLS_PATH)}")
            if len(orfaos) > 10:
                print(f"    ... e mais {len(orfaos) - 10}")
        else:
            print("  ✅ Não há arquivos órfãos!")
        
        # ========================================
        # 6. CAMINHOS INVÁLIDOS
        # ========================================
        print("\n🔍 6. VERIFICAÇÃO DE CAMINHOS INVÁLIDOS")
        print("-" * 80)
        
        cur.execute("""
            SELECT chave, caminho_arquivo 
            FROM xmls_baixados 
            WHERE caminho_arquivo IS NOT NULL
        """)
        
        caminhos_invalidos = []
        total_verificados = 0
        
        for row in cur.fetchall():
            total_verificados += 1
            caminho = row['caminho_arquivo']
            if not os.path.exists(caminho):
                caminhos_invalidos.append((row['chave'], caminho))
        
        print(f"Caminhos verificados: {total_verificados:,}")
        
        if caminhos_invalidos:
            print(f"\n  ⚠️ Encontrados {len(caminhos_invalidos)} caminhos inválidos (não existem):")
            for i, (chave, caminho) in enumerate(caminhos_invalidos[:10], 1):
                print(f"    {i}. Chave: {chave}")
                print(f"       Caminho: {caminho}")
            if len(caminhos_invalidos) > 10:
                print(f"    ... e mais {len(caminhos_invalidos) - 10}")
        else:
            print("  ✅ Todos os caminhos são válidos!")
    
    # ========================================
    # 7. RESUMO FINAL
    # ========================================
    print("\n" + "=" * 80)
    print("📋 RESUMO FINAL")
    print("=" * 80)
    
    issues = []
    
    if row_caminho['sem_caminho'] > 0:
        issues.append(f"⚠️ {row_caminho['sem_caminho']:,} XMLs sem caminho_arquivo")
    
    if notas_sem_xml:
        total_sem_xml = sum(r['qtd'] for r in notas_sem_xml)
        issues.append(f"⚠️ {total_sem_xml:,} notas sem XML registrado")
    
    if orfaos:
        issues.append(f"⚠️ {len(orfaos):,} arquivos órfãos no disco")
    
    if caminhos_invalidos:
        issues.append(f"⚠️ {len(caminhos_invalidos):,} caminhos inválidos")
    
    if not issues:
        print("✅ NENHUM PROBLEMA ENCONTRADO!")
        print("✅ Todos os XMLs estão armazenados e registrados corretamente!")
    else:
        print("⚠️ PROBLEMAS ENCONTRADOS:")
        for issue in issues:
            print(f"  {issue}")
        
        print("\n💡 RECOMENDAÇÕES:")
        if row_caminho['sem_caminho'] > 0:
            print("  1. Execute: python corrigir_caminhos_xmls.py")
        if notas_sem_xml:
            print("  2. Verifique se houve erro durante download NSU")
        if orfaos:
            print("  3. Considere importar arquivos órfãos para o banco")
    
    print("=" * 80)
    
    conn.close()

if __name__ == "__main__":
    main()
