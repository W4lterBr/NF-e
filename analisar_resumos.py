"""
Analisa notas com status RESUMO para verificar se são emitidas ou recebidas
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "notas_test.db"

conn = sqlite3.connect(DB_PATH)

# Busca CNPJs da empresa (certificados)
cur_certs = conn.execute("SELECT REPLACE(REPLACE(REPLACE(cnpj_cpf, '.', ''), '/', ''), '-', '') FROM certificados")
cnpjs_empresa = set(row[0] for row in cur_certs.fetchall())

print("=" * 80)
print("ANÁLISE DE NOTAS RESUMO")
print("=" * 80)
print(f"\nCNPJs da empresa: {cnpjs_empresa}\n")

# Busca notas RESUMO
cur = conn.execute("""
    SELECT 
        chave,
        REPLACE(REPLACE(REPLACE(cnpj_emitente, '.', ''), '/', ''), '-', '') as cnpj_emit,
        REPLACE(REPLACE(REPLACE(cnpj_destinatario, '.', ''), '/', ''), '-', '') as cnpj_dest,
        valor,
        data_emissao,
        nome_emitente,
        xml_status
    FROM notas_detalhadas
    WHERE xml_status = 'RESUMO'
    ORDER BY data_emissao DESC
    LIMIT 50
""")

notas = cur.fetchall()

print(f"Total de notas RESUMO analisadas: {len(notas)}\n")

emitidas = []
recebidas = []
outras = []

for nota in notas:
    chave, cnpj_emit, cnpj_dest, valor, data, nome_emit, status = nota
    
    # Normaliza CNPJs
    cnpj_emit_norm = ''.join(filter(str.isdigit, cnpj_emit or ''))
    cnpj_dest_norm = ''.join(filter(str.isdigit, cnpj_dest or ''))
    
    if cnpj_emit_norm in cnpjs_empresa:
        emitidas.append(nota)
    elif cnpj_dest_norm in cnpjs_empresa:
        recebidas.append(nota)
    else:
        outras.append(nota)

print("=" * 80)
print("CLASSIFICAÇÃO")
print("=" * 80)
print(f"✅ Notas EMITIDAS pela empresa: {len(emitidas)}")
print(f"❌ Notas RECEBIDAS pela empresa: {len(recebidas)} ⚠️ PROBLEMA DE OMISSÃO!")
print(f"❓ Outras (nem emit nem dest): {len(outras)}")

if recebidas:
    print("\n" + "=" * 80)
    print("⚠️ NOTAS RECEBIDAS QUE DEVERIAM TER XML COMPLETO:")
    print("=" * 80)
    for nota in recebidas[:10]:  # Mostra primeiras 10
        chave, cnpj_emit, cnpj_dest, valor, data, nome_emit, status = nota
        print(f"\nChave: {chave}")
        print(f"  Data: {data}")
        print(f"  Valor: R$ {valor}")
        print(f"  Emitente: {nome_emit} ({cnpj_emit})")
        print(f"  Destinatário CNPJ: {cnpj_dest}")
        print(f"  Status: {status}")

if emitidas:
    print("\n" + "=" * 80)
    print("✅ NOTAS EMITIDAS (normal ficar como RESUMO):")
    print("=" * 80)
    for nota in emitidas[:5]:  # Mostra primeiras 5
        chave, cnpj_emit, cnpj_dest, valor, data, nome_emit, status = nota
        print(f"\nChave: {chave}")
        print(f"  Data: {data}")
        print(f"  Valor: R$ {valor}")
        print(f"  Destinatário CNPJ: {cnpj_dest}")

# Verifica se há verificações que retornaram erro 217
print("\n" + "=" * 80)
print("VERIFICAÇÕES ANTERIORES (erro 217)")
print("=" * 80)

cur_verif = conn.execute("""
    SELECT COUNT(*) 
    FROM notas_verificadas 
    WHERE resultado = 'nao_encontrado'
""")
count_217 = cur_verif.fetchone()[0]
print(f"Total de notas marcadas como 'não encontrado': {count_217}")

# Cruza com as notas RESUMO
cur_cross = conn.execute("""
    SELECT 
        nd.chave,
        REPLACE(REPLACE(REPLACE(nd.cnpj_emitente, '.', ''), '/', ''), '-', '') as cnpj_emit,
        REPLACE(REPLACE(REPLACE(nd.cnpj_destinatario, '.', ''), '/', ''), '-', '') as cnpj_dest,
        nd.nome_emitente,
        nd.valor,
        nd.data_emissao
    FROM notas_detalhadas nd
    INNER JOIN notas_verificadas nv ON nd.chave = nv.chave
    WHERE nv.resultado = 'nao_encontrado'
    AND nd.xml_status = 'RESUMO'
    LIMIT 20
""")

notas_217 = cur_cross.fetchall()

if notas_217:
    print(f"\nNotas com erro 217 (primeiras 20):")
    
    emit_217 = 0
    receb_217 = 0
    
    for nota in notas_217:
        chave, cnpj_emit, cnpj_dest, nome_emit, valor, data = nota
        
        cnpj_emit_norm = ''.join(filter(str.isdigit, cnpj_emit or ''))
        cnpj_dest_norm = ''.join(filter(str.isdigit, cnpj_dest or ''))
        
        if cnpj_emit_norm in cnpjs_empresa:
            tipo = "EMITIDA"
            emit_217 += 1
        elif cnpj_dest_norm in cnpjs_empresa:
            tipo = "RECEBIDA ⚠️"
            receb_217 += 1
        else:
            tipo = "OUTRA"
        
        print(f"\n  [{tipo}] {chave}")
        print(f"    Data: {data}, Valor: R$ {valor}")
        if tipo == "EMITIDA":
            print(f"    Destinatário CNPJ: {cnpj_dest}")
        else:
            print(f"    Emitente: {nome_emit} (CNPJ: {cnpj_emit})")
    
    print("\n" + "=" * 80)
    print("RESUMO DOS ERROS 217:")
    print("=" * 80)
    print(f"✅ Emitidas (normal): {emit_217}")
    print(f"❌ Recebidas (OMISSÃO!): {receb_217}")

conn.close()

print("\n" + "=" * 80)
print("CONCLUSÃO")
print("=" * 80)

if 'receb_217' in locals() and receb_217 > 0:
    print(f"⚠️ PROBLEMA DETECTADO: {receb_217} notas RECEBIDAS não foram encontradas!")
    print("   Essas notas deveriam ter XML completo salvo na pasta de arquivos.")
    print("   O sistema de distribuição NSU deveria ter salvo o procNFe/procCTe completo.")
elif len(notas) == 0:
    print("ℹ️ Não há notas com status RESUMO no banco.")
    print("   Todas as notas já foram processadas ou o banco está vazio.")
else:
    print("✅ Tudo OK: Todas as notas com erro 217 são EMITIDAS pela empresa.")
    print("   É normal que notas emitidas não sejam encontradas via consulta por chave.")
