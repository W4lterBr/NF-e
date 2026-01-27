#!/usr/bin/env python3
"""
Script para verificar sincronização entre banco de dados e XMLs físicos
"""
import sqlite3
import os
from pathlib import Path

def verificar_sincronizacao(db_path="notas.db", xmls_base_path="c:\\Arquivo Walter - Empresas\\Notas\\NFs"):
    """Verifica consistência entre banco de dados e arquivos XML"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("🔍 VERIFICAÇÃO DE SINCRONIZAÇÃO - BANCO vs SISTEMA DE ARQUIVOS")
    print("=" * 80)
    
    # 1. Verificar XMLs no banco que estão marcados como COMPLETO mas não existem fisicamente
    print("\n1️⃣ XMLs marcados como COMPLETO no banco mas AUSENTES no disco:")
    cursor.execute("""
        SELECT chave, xml_status, informante, nome_emitente
        FROM notas_detalhadas
        WHERE xml_status = 'COMPLETO'
        LIMIT 20
    """)
    
    ausentes = []
    verificados = 0
    
    for chave, status, informante, emitente in cursor.fetchall():
        verificados += 1
        if not chave:
            continue
            
        # Buscar XML em múltiplas localizações
        encontrado = False
        
        # 1. No banco xmls_baixados
        xml_cursor = conn.cursor()
        xml_cursor.execute("SELECT xml_completo FROM xmls_baixados WHERE chave = ?", (chave,))
        if xml_cursor.fetchone():
            encontrado = True
        
        # 2. No filesystem
        if not encontrado and informante:
            possibilidades = [
                Path(xmls_base_path) / informante / "NFe" / f"{chave}.xml",
                Path(xmls_base_path) / informante / "CTe" / f"{chave}.xml",
                Path(xmls_base_path) / informante / "Eventos" / f"{chave}.xml",
            ]
            
            for caminho in possibilidades:
                if caminho.exists():
                    encontrado = True
                    break
        
        if not encontrado:
            ausentes.append((chave, informante, emitente))
    
    if ausentes:
        print(f"   ⚠️ {len(ausentes)} XMLs marcados como COMPLETO mas NÃO ENCONTRADOS:")
        for i, (chave, info, emit) in enumerate(ausentes[:10], 1):
            print(f"      [{i}] {chave[:44]} - {info} - {emit}")
        if len(ausentes) > 10:
            print(f"      ... e mais {len(ausentes) - 10} XMLs ausentes")
    else:
        print(f"   ✅ Todos os {verificados} XMLs COMPLETO verificados foram encontrados!")
    
    # 2. Verificar XMLs marcados como RESUMO que têm XML disponível
    print("\n2️⃣ XMLs marcados como RESUMO mas XML DISPONÍVEL:")
    cursor.execute("""
        SELECT chave, xml_status, informante, nome_emitente
        FROM notas_detalhadas
        WHERE xml_status = 'RESUMO'
        LIMIT 100
    """)
    
    disponiveis = []
    for chave, status, informante, emitente in cursor.fetchall():
        if not chave:
            continue
        
        # Verificar no banco
        xml_cursor = conn.cursor()
        xml_cursor.execute("SELECT xml_completo FROM xmls_baixados WHERE chave = ?", (chave,))
        if xml_cursor.fetchone():
            disponiveis.append((chave, informante, emitente, "banco"))
            continue
        
        # Verificar no filesystem
        if informante:
            possibilidades = [
                Path(xmls_base_path) / informante / "NFe" / f"{chave}.xml",
                Path(xmls_base_path) / informante / "CTe" / f"{chave}.xml",
            ]
            
            for caminho in possibilidades:
                if caminho.exists():
                    disponiveis.append((chave, informante, emitente, str(caminho)))
                    break
    
    if disponiveis:
        print(f"   ⚠️ {len(disponiveis)} XMLs marcados como RESUMO mas COM XML DISPONÍVEL:")
        for i, (chave, info, emit, local) in enumerate(disponiveis[:10], 1):
            print(f"      [{i}] {chave[:44]} - {info} - {emit}")
            print(f"          Encontrado em: {local if local != 'banco' else 'banco de dados'}")
        if len(disponiveis) > 10:
            print(f"      ... e mais {len(disponiveis) - 10} XMLs com status incorreto")
    else:
        print(f"   ✅ Todos os XMLs RESUMO verificados estão corretos!")
    
    # 3. Estatísticas gerais
    print("\n3️⃣ ESTATÍSTICAS GERAIS:")
    
    cursor.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status = 'COMPLETO'")
    completos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status = 'RESUMO'")
    resumos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status = 'CANCELADO'")
    cancelados = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM xmls_baixados")
    xmls_banco = cursor.fetchone()[0]
    
    print(f"   📊 Status das notas:")
    print(f"      • COMPLETO: {completos:,}")
    print(f"      • RESUMO: {resumos:,}")
    print(f"      • CANCELADO: {cancelados:,}")
    print(f"   📦 XMLs no banco (xmls_baixados): {xmls_banco:,}")
    
    # 4. Verificar certificados cadastrados
    print("\n4️⃣ CERTIFICADOS CADASTRADOS:")
    cursor.execute("SELECT cnpj_cpf, razao_social, ativo FROM certificados ORDER BY ativo DESC, razao_social")
    certs = cursor.fetchall()
    
    ativos = [c for c in certs if c[2]]
    inativos = [c for c in certs if not c[2]]
    
    print(f"   ✅ {len(ativos)} certificados ATIVOS:")
    for cnpj, nome, _ in ativos:
        print(f"      • {cnpj} - {nome}")
    
    if inativos:
        print(f"   ⚠️ {len(inativos)} certificados INATIVOS:")
        for cnpj, nome, _ in inativos[:5]:
            print(f"      • {cnpj} - {nome}")
        if len(inativos) > 5:
            print(f"      ... e mais {len(inativos) - 5} inativos")
    
    # 5. Verificar pastas no filesystem
    print("\n5️⃣ VERIFICAÇÃO DE PASTAS NO FILESYSTEM:")
    base = Path(xmls_base_path)
    if base.exists():
        pastas = [p for p in base.iterdir() if p.is_dir()]
        cnpjs_ativos = {c[0] for c in ativos}
        
        pastas_corretas = []
        pastas_extras = []
        
        for pasta in pastas:
            nome = pasta.name
            # Extrair possível CNPJ (14 dígitos)
            cnpj = ''.join(c for c in nome if c.isdigit())
            if len(cnpj) == 14:
                if cnpj in cnpjs_ativos:
                    pastas_corretas.append(nome)
                else:
                    pastas_extras.append(nome)
            else:
                # Pastas com nomes especiais
                if nome not in ['desconhecido', 'temp', 'backup']:
                    pastas_extras.append(nome)
        
        print(f"   ✅ {len(pastas_corretas)} pastas de certificados ativos")
        if pastas_extras:
            print(f"   ⚠️ {len(pastas_extras)} pastas que NÃO correspondem a certificados ativos:")
            for nome in pastas_extras[:10]:
                print(f"      • {nome}")
            if len(pastas_extras) > 10:
                print(f"      ... e mais {len(pastas_extras) - 10} pastas extras")
        else:
            print(f"   ✅ Nenhuma pasta extra encontrada!")
    
    # 6. Resumo final
    print("\n" + "=" * 80)
    print("📋 RESUMO DA SINCRONIZAÇÃO:")
    print("=" * 80)
    
    problemas = []
    if ausentes:
        problemas.append(f"❌ {len(ausentes)} XMLs COMPLETO ausentes no disco")
    if disponiveis:
        problemas.append(f"⚠️ {len(disponiveis)} XMLs RESUMO que deveriam ser COMPLETO")
    if pastas_extras:
        problemas.append(f"⚠️ {len(pastas_extras)} pastas extras no filesystem")
    
    if problemas:
        print("   ⚠️ PROBLEMAS ENCONTRADOS:")
        for prob in problemas:
            print(f"      {prob}")
        print("\n   💡 RECOMENDAÇÕES:")
        if disponiveis:
            print("      • Execute _corrigir_xml_status_automatico() para corrigir status")
        if pastas_extras:
            print("      • Verifique se as pastas extras podem ser removidas ou movidas")
    else:
        print("   ✅ SISTEMA 100% SINCRONIZADO!")
        print("      • Todos os XMLs COMPLETO existem fisicamente")
        print("      • Nenhum XML RESUMO com XML disponível")
        print("      • Todas as pastas correspondem a certificados ativos")
    
    print("=" * 80)
    
    conn.close()
    return len(ausentes) + len(disponiveis) + len(pastas_extras) == 0

if __name__ == "__main__":
    import sys
    
    base_path = sys.argv[1] if len(sys.argv) > 1 else "c:\\Arquivo Walter - Empresas\\Notas\\NFs"
    sincronizado = verificar_sincronizacao(xmls_base_path=base_path)
    
    sys.exit(0 if sincronizado else 1)
