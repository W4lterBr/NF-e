"""
🔍 DIAGNÓSTICO COMPLETO - Análise do fluxo de salvamento de XMLs
Identifica pontos de falha no processo de download e registro de NF-e
"""

import sqlite3
from pathlib import Path
import os

def main():
    print("=" * 80)
    print("🔍 DIAGNÓSTICO COMPLETO - Fluxo de Salvamento de XMLs")
    print("=" * 80)
    
    # Conectar ao banco
    conn = sqlite3.connect('notas_test.db')
    cursor = conn.cursor()
    
    # 1. ESTATÍSTICAS GERAIS
    print("\n📊 1. ESTATÍSTICAS GERAIS")
    print("-" * 80)
    
    cursor.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status = 'RESUMO'")
    resumo = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status = 'COMPLETO'")
    completo = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status = 'EVENTO'")
    evento = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM xmls_baixados")
    xmls_registrados = cursor.fetchone()[0]
    
    print(f"   RESUMO: {resumo}")
    print(f"   COMPLETO: {completo}")
    print(f"   EVENTO: {evento}")
    print(f"   XMLs registrados em xmls_baixados: {xmls_registrados}")
    print(f"   Total de notas: {resumo + completo + evento}")
    
    # 2. INCONSISTÊNCIAS CRÍTICAS
    print("\n🚨 2. INCONSISTÊNCIAS CRÍTICAS")
    print("-" * 80)
    
    # 2.1 Notas COMPLETO sem registro em xmls_baixados
    cursor.execute("""
        SELECT nd.chave, nd.numero, nd.data_emissao, nd.informante
        FROM notas_detalhadas nd
        LEFT JOIN xmls_baixados xb ON nd.chave = xb.chave
        WHERE nd.xml_status = 'COMPLETO' AND xb.chave IS NULL
        LIMIT 10
    """)
    sem_registro = cursor.fetchall()
    
    print(f"\n   🔴 Notas COMPLETO SEM registro em xmls_baixados: {len(sem_registro)}")
    if sem_registro:
        print("   Exemplos:")
        for chave, numero, data, informante in sem_registro[:5]:
            print(f"      - {chave[:25]}... | NF {numero} | {data} | {informante}")
    
    # 2.2 Registros em xmls_baixados sem caminho
    cursor.execute("""
        SELECT chave, nsu
        FROM xmls_baixados
        WHERE caminho_arquivo IS NULL OR caminho_arquivo = ''
        LIMIT 10
    """)
    sem_caminho = cursor.fetchall()
    
    print(f"\n   🟡 Registros em xmls_baixados SEM caminho: {len(sem_caminho)}")
    if sem_caminho:
        print("   Exemplos:")
        for chave, nsu in sem_caminho[:5]:
            print(f"      - {chave[:25]}... | NSU {nsu}")
    
    # 2.3 XMLs registrados mas arquivo não existe no disco
    cursor.execute("""
        SELECT chave, caminho_arquivo, nsu
        FROM xmls_baixados
        WHERE caminho_arquivo IS NOT NULL AND caminho_arquivo != ''
        LIMIT 100
    """)
    registros_com_caminho = cursor.fetchall()
    
    arquivos_nao_encontrados = []
    for chave, caminho, nsu in registros_com_caminho:
        if not Path(caminho).exists():
            arquivos_nao_encontrados.append((chave, caminho, nsu))
    
    print(f"\n   🔴 XMLs registrados mas ARQUIVO NÃO EXISTE: {len(arquivos_nao_encontrados)}")
    if arquivos_nao_encontrados:
        print("   Exemplos:")
        for chave, caminho, nsu in arquivos_nao_encontrados[:5]:
            print(f"      - {chave[:25]}... | {caminho}")
    
    # 3. ANÁLISE DE XMLs NO DISCO
    print("\n📁 3. ANÁLISE DE XMLs NO DISCO")
    print("-" * 80)
    
    # Contar XMLs nas pastas
    xmls_pasta = Path("xmls")
    xmls_chave_pasta = Path("xmls_chave")
    
    if xmls_pasta.exists():
        xmls_disco_count = len(list(xmls_pasta.rglob("*.xml")))
        print(f"   XMLs na pasta xmls/: {xmls_disco_count}")
    else:
        xmls_disco_count = 0
        print(f"   Pasta xmls/ não encontrada")
    
    if xmls_chave_pasta.exists():
        xmls_chave_disco_count = len(list(xmls_chave_pasta.rglob("*.xml")))
        print(f"   XMLs na pasta xmls_chave/: {xmls_chave_disco_count}")
    else:
        xmls_chave_disco_count = 0
        print(f"   Pasta xmls_chave/ não encontrada")
    
    # 4. NOTAS RESUMO QUE DEVERIAM SER COMPLETO
    print("\n🔄 4. NOTAS RESUMO COM XML NO DISCO")
    print("-" * 80)
    
    cursor.execute("""
        SELECT nd.chave, nd.numero, nd.data_emissao, xb.caminho_arquivo
        FROM notas_detalhadas nd
        INNER JOIN xmls_baixados xb ON nd.chave = xb.chave
        WHERE nd.xml_status = 'RESUMO' 
        AND xb.caminho_arquivo IS NOT NULL 
        AND xb.caminho_arquivo != ''
        LIMIT 20
    """)
    resumo_com_xml = cursor.fetchall()
    
    resumo_com_arquivo_ok = []
    for chave, numero, data, caminho in resumo_com_xml:
        if Path(caminho).exists():
            resumo_com_arquivo_ok.append((chave, numero, data, caminho))
    
    print(f"   🟢 Notas RESUMO com XML existente no disco: {len(resumo_com_arquivo_ok)}")
    if resumo_com_arquivo_ok:
        print("   Exemplos (PRECISAM ser corrigidas para COMPLETO):")
        for chave, numero, data, caminho in resumo_com_arquivo_ok[:5]:
            print(f"      - {chave[:25]}... | NF {numero} | {data}")
            print(f"        Arquivo: {caminho}")
    
    # 5. ANÁLISE DE NSUs VAZIOS
    print("\n🔒 5. ANÁLISE DE NSUs")
    print("-" * 80)
    
    cursor.execute("""
        SELECT COUNT(*) FROM notas_detalhadas 
        WHERE nsu IS NULL OR nsu = ''
    """)
    nsu_vazio = cursor.fetchone()[0]
    
    print(f"   Notas sem NSU: {nsu_vazio}")
    
    if nsu_vazio > 0:
        cursor.execute("""
            SELECT chave, numero, data_emissao, tipo, informante
            FROM notas_detalhadas 
            WHERE nsu IS NULL OR nsu = ''
            LIMIT 10
        """)
        sem_nsu = cursor.fetchall()
        print("   Exemplos:")
        for chave, numero, data, tipo, informante in sem_nsu[:5]:
            print(f"      - {chave[:25]}... | {tipo} {numero} | {data} | {informante}")
    
    # 6. RECOMENDAÇÕES
    print("\n💡 6. RECOMENDAÇÕES")
    print("-" * 80)
    
    if len(sem_registro) > 0:
        print("   🔴 CRÍTICO: Notas marcadas COMPLETO sem registro em xmls_baixados")
        print("      → Problema no fluxo de salvamento: XML baixado mas não registrado")
        print("      → Analisar função que salva XMLs (salvar_xml_completo)")
    
    if len(sem_caminho) > 0:
        print("   🟡 ATENÇÃO: Registros em xmls_baixados sem caminho de arquivo")
        print("      → INSERT parcial: chave registrada mas caminho não preenchido")
    
    if len(arquivos_nao_encontrados) > 0:
        print("   🔴 CRÍTICO: Caminhos registrados mas arquivos não existem")
        print("      → XMLs foram movidos ou deletados após registro")
        print("      → Ou erro no caminho ao salvar")
    
    if len(resumo_com_arquivo_ok) > 0:
        print(f"   🟢 BOM: {len(resumo_com_arquivo_ok)} notas RESUMO podem ser promovidas para COMPLETO")
        print("      → Execute o script corrigir_forcado.py para corrigir")
    
    # 7. PRÓXIMOS PASSOS
    print("\n🎯 7. PRÓXIMOS PASSOS")
    print("-" * 80)
    print("   1. Analisar logs de busca_nfe para ver erros de salvamento")
    print("   2. Verificar função salvar_xml_completo() em nfe_search.py")
    print("   3. Verificar se INSERT em xmls_baixados está completo")
    print("   4. Executar corrigir_forcado.py se houver XMLs válidos marcados como RESUMO")
    print("   5. Verificar permissões de escrita nas pastas xmls/")
    
    print("\n" + "=" * 80)
    print("✅ Diagnóstico concluído!")
    print("=" * 80)
    
    conn.close()

if __name__ == "__main__":
    main()
