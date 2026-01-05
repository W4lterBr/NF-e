"""
Guia para preparar dados de teste para o sistema de Export
"""
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
db_path = BASE_DIR / 'notas_test.db'

print("=" * 80)
print("GUIA PARA TESTAR O SISTEMA DE EXPORT")
print("=" * 80)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Estado atual
cursor.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status = 'COMPLETO'")
notas_completas = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status = 'RESUMO'")
notas_resumo = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM xmls_baixados WHERE caminho_arquivo IS NOT NULL")
xmls_salvos = cursor.fetchone()[0]

print(f"\n📊 ESTADO ATUAL:")
print(f"   Notas COMPLETAS: {notas_completas}")
print(f"   Notas RESUMO: {notas_resumo}")
print(f"   XMLs salvos em disco: {xmls_salvos}")

if notas_completas > 0:
    print(f"\n✅ Você JÁ TEM {notas_completas} nota(s) COMPLETA(S)!")
    
    # Lista algumas
    cursor.execute("""
        SELECT n.chave, n.numero, n.nome_emitente, x.caminho_arquivo
        FROM notas_detalhadas n
        LEFT JOIN xmls_baixados x ON n.chave = x.chave
        WHERE n.xml_status = 'COMPLETO'
        LIMIT 5
    """)
    
    print(f"\n   📋 Notas disponíveis para export:")
    for i, (chave, num, emit, path) in enumerate(cursor.fetchall(), 1):
        tem_arquivo = "✅" if path and Path(path).exists() else "❌"
        print(f"   {i}. NF {num} - {emit}")
        print(f"      {tem_arquivo} XML: {chave[:20]}...")
    
    print(f"\n✅ PRONTO PARA TESTAR!")
    print(f"\n📝 COMO TESTAR:")
    print(f"   1. Abra a interface (pressione F5)")
    print(f"   2. Vá para aba 'Notas Recebidas' ou 'Notas Emitidas'")
    print(f"   3. Selecione uma ou mais notas com ícone VERDE (XML Completo)")
    print(f"   4. Clique no botão 'Exportar' 📥")
    print(f"   5. Escolha opções e pasta de destino")
    print(f"   6. ✅ Os arquivos serão exportados!")

elif notas_resumo > 0:
    print(f"\n⚠️ Você tem {notas_resumo} nota(s) apenas como RESUMO")
    print(f"   É necessário baixar o XML completo de pelo menos uma nota")
    
    # Mostra algumas notas resumo
    cursor.execute("""
        SELECT chave, numero, nome_emitente, tipo
        FROM notas_detalhadas
        WHERE xml_status = 'RESUMO'
        LIMIT 5
    """)
    
    print(f"\n   📋 Notas disponíveis:")
    for i, (chave, num, emit, tipo) in enumerate(cursor.fetchall(), 1):
        print(f"   {i}. {tipo} {num} - {emit}")
        print(f"      Chave: {chave[:20]}...")
    
    print(f"\n📝 COMO BAIXAR XML COMPLETO:")
    print(f"   1. Abra a interface (pressione F5)")
    print(f"   2. Vá para aba 'Notas Recebidas'")
    print(f"   3. Encontre uma nota com ícone CINZA (Resumo)")
    print(f"   4. Dê DUPLO CLIQUE na nota")
    print(f"   5. O sistema baixará o XML completo")
    print(f"   6. O ícone ficará VERDE")
    print(f"   7. Agora você pode exportar essa nota!")

else:
    print(f"\n❌ Você NÃO TEM notas no banco de dados")
    print(f"\n📝 COMO BUSCAR NOTAS:")
    print(f"   1. Abra a interface (pressione F5)")
    print(f"   2. Configure um certificado (⚙️ Configurações → Certificados)")
    print(f"   3. Clique em 'Buscar Notas' 🔍")
    print(f"   4. O sistema buscará automaticamente notas da Sefaz")
    print(f"   5. As notas aparecerão na tabela")
    print(f"   6. Dê duplo clique em uma nota para baixar XML completo")
    print(f"   7. Depois teste o Export!")

# Se tem XMLs salvos mas não estão em notas_detalhadas
if xmls_salvos > 0 and notas_completas == 0:
    print(f"\n⚠️ ATENÇÃO: Você tem {xmls_salvos} XMLs salvos mas não aparecem como COMPLETOS")
    print(f"   Isso pode indicar que:")
    print(f"   1. Os XMLs foram baixados mas não processados")
    print(f"   2. Os XMLs não têm registro correspondente em notas_detalhadas")
    
    # Mostra alguns XMLs órfãos
    cursor.execute("""
        SELECT x.chave, x.caminho_arquivo
        FROM xmls_baixados x
        LEFT JOIN notas_detalhadas n ON x.chave = n.chave
        WHERE x.caminho_arquivo IS NOT NULL
        AND n.chave IS NULL
        LIMIT 5
    """)
    
    orfaos = cursor.fetchall()
    if orfaos:
        print(f"\n   📋 XMLs sem registro em notas_detalhadas:")
        for i, (chave, path) in enumerate(orfaos, 1):
            print(f"   {i}. {chave[:20]}...")
            print(f"      📄 {Path(path).name if path else 'N/A'}")

conn.close()

print("\n" + "=" * 80)
print("Para dúvidas, consulte: CORRECAO_EXPORT.md")
print("=" * 80)
