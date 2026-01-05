"""
Script para baixar notas reais via NSU para testar o sistema de export
"""
import sys
from pathlib import Path
import sqlite3

# Adiciona o diretório ao path para importar módulos
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from modules.database import DatabaseManager
from nfe_search import NFESearch

print("=" * 80)
print("BAIXANDO NOTAS PARA TESTE DE EXPORT")
print("=" * 80)

# Inicializa banco
db = DatabaseManager()

# Busca certificados disponíveis
with db._connect() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT cnpj, razao_social FROM certificados WHERE ativo = 1 LIMIT 1")
    cert_row = cursor.fetchone()

if not cert_row:
    print("\n❌ ERRO: Nenhum certificado ativo encontrado!")
    print("   Configure um certificado antes de continuar.")
    sys.exit(1)

cnpj_cert, razao = cert_row
print(f"\n✅ Usando certificado: {cnpj_cert} - {razao}")

# Busca último NSU processado
with db._connect() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(nsu) FROM nsu WHERE cnpj_informante = ?", (cnpj_cert,))
    row = cursor.fetchone()
    ultimo_nsu = row[0] if row and row[0] else 0

print(f"📊 Último NSU processado: {ultimo_nsu}")
print(f"🔍 Iniciando busca de novas notas...")

# Inicializa NFESearch
nfe_search = NFESearch(cnpj_cert, db)

# Faz busca por NSU (limite de 10 documentos para teste)
print(f"\n⏳ Buscando documentos via distribuição DFe...")

try:
    # Busca próximos documentos
    documentos = nfe_search.buscar_por_nsu(
        nsu_inicial=ultimo_nsu,
        limite=10  # Limita a 10 documentos para teste
    )
    
    print(f"\n📥 {len(documentos)} documento(s) encontrado(s)")
    
    # Conta tipos
    nfes = [d for d in documentos if d.get('tipo') in ['NFe', 'NF-e']]
    eventos = [d for d in documentos if d.get('tipo') == 'evento']
    outros = [d for d in documentos if d.get('tipo') not in ['NFe', 'NF-e', 'evento']]
    
    print(f"   📄 NFe: {len(nfes)}")
    print(f"   📋 Eventos: {len(eventos)}")
    print(f"   📦 Outros: {len(outros)}")
    
    # Verifica quantas foram salvas em notas_detalhadas
    with db._connect() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status != 'EVENTO'")
        total_notas = cursor.fetchone()[0]
    
    print(f"\n✅ Total de notas no banco após busca: {total_notas}")
    
    if nfes:
        print(f"\n📋 Exemplo de NFes encontradas:")
        for i, doc in enumerate(nfes[:3], 1):
            print(f"   {i}. Chave: {doc.get('chave', 'N/A')[:20]}...")
            print(f"      Tipo: {doc.get('tipo')}")
            print(f"      NSU: {doc.get('nsu')}")
    
    # Verifica se alguma tem XML completo
    with db._connect() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT chave, numero, nome_emitente, xml_status 
            FROM notas_detalhadas 
            WHERE xml_status = 'COMPLETO' 
            LIMIT 5
        """)
        notas_completas = cursor.fetchall()
    
    if notas_completas:
        print(f"\n✅ {len(notas_completas)} nota(s) COMPLETA(S) disponível(is) para export:")
        for i, (chave, num, emit, status) in enumerate(notas_completas, 1):
            print(f"   {i}. NF {num} - {emit}")
            print(f"      Chave: {chave}")
            
            # Verifica se tem arquivo em xmls_baixados
            cursor.execute("SELECT caminho_arquivo FROM xmls_baixados WHERE chave = ?", (chave,))
            path_row = cursor.fetchone()
            if path_row and path_row[0]:
                arquivo = Path(path_row[0])
                if arquivo.exists():
                    print(f"      ✅ XML salvo: {arquivo.name}")
                else:
                    print(f"      ⚠️ Caminho registrado mas arquivo não existe")
            else:
                print(f"      ❌ Não tem caminho em xmls_baixados")
    else:
        print(f"\n⚠️ Nenhuma nota COMPLETA encontrada")
        print(f"   As notas podem estar apenas como RESUMO")
        print(f"   Use a interface para baixar o XML completo de uma nota")

except Exception as e:
    print(f"\n❌ ERRO durante busca: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("BUSCA CONCLUÍDA")
print("=" * 80)
print("\n💡 Próximos passos:")
print("   1. Abra a interface")
print("   2. Vá para aba 'Notas Recebidas' ou 'Notas Emitidas'")
print("   3. Dê duplo clique em uma nota RESUMO para baixar XML completo")
print("   4. Selecione notas COMPLETAS e teste o Export")
