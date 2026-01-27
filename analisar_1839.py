import sqlite3

conn = sqlite3.connect('notas.db')
c = conn.cursor()

print("Total de documentos por tipo:")
c.execute("SELECT tipo, COUNT(*) FROM notas_detalhadas GROUP BY tipo ORDER BY tipo")
totals = {}
for tipo, count in c.fetchall():
    totals[tipo] = count
    print(f"  {tipo}: {count}")

total_geral = sum(totals.values())
print(f"\nTotal geral: {total_geral}")

print("\n" + "="*70)

# Simula filtro "Emitidos por terceiros" (exclui notas da própria empresa)
print("\nSimulando filtro 'Emitidos por terceiros':")
print("(Exclui notas onde cnpj_emitente está nos certificados cadastrados)")

# Lista CNPJs dos certificados
c.execute("SELECT DISTINCT cnpj_cpf FROM certificados")
company_cnpjs = [row[0] for row in c.fetchall() if row[0]]
print(f"\nCNPJs da empresa cadastrados: {company_cnpjs}")

# Conta documentos EXCLUINDO notas emitidas pela empresa
if company_cnpjs:
    placeholders = ','.join('?' * len(company_cnpjs))
    
    # Remove formatação dos CNPJs
    company_cnpjs_clean = [''.join(c for c in cnpj if c.isdigit()) for cnpj in company_cnpjs]
    
    query = f"""
        SELECT tipo, COUNT(*) 
        FROM notas_detalhadas 
        WHERE xml_status != 'EVENTO'
          AND REPLACE(REPLACE(REPLACE(REPLACE(cnpj_emitente, '.', ''), '-', ''), '/', ''), ' ', '') NOT IN ({placeholders})
        GROUP BY tipo
    """
    
    c.execute(query, company_cnpjs_clean)
    print("\nDocumentos 'Emitidos por terceiros':")
    total_terceiros = 0
    for tipo, count in c.fetchall():
        print(f"  {tipo}: {count}")
        total_terceiros += count
    print(f"\nTotal: {total_terceiros}")
    
    # Verifica se bate com 1839
    if total_terceiros == 1839:
        print("\n✅ ENCONTRADO! O valor 1839 corresponde aos 'Emitidos por terceiros'")
        print("   (excluindo notas emitidas pela própria empresa)")
    
    # Mostra quantos documentos foram EXCLUÍDOS
    print("\n" + "="*70)
    print("Documentos 'Emitidos pela empresa' (EXCLUÍDOS da aba principal):")
    query_empresa = f"""
        SELECT tipo, COUNT(*) 
        FROM notas_detalhadas 
        WHERE xml_status != 'EVENTO'
          AND REPLACE(REPLACE(REPLACE(REPLACE(cnpj_emitente, '.', ''), '-', ''), '/', ''), ' ', '') IN ({placeholders})
        GROUP BY tipo
    """
    c.execute(query_empresa, company_cnpjs_clean)
    total_empresa = 0
    for tipo, count in c.fetchall():
        print(f"  {tipo}: {count}")
        total_empresa += count
    print(f"\nTotal: {total_empresa}")
    
    print("\n" + "="*70)
    print(f"Verificação: {total_terceiros} (terceiros) + {total_empresa} (empresa) = {total_terceiros + total_empresa}")
    print(f"Total no banco: {total_geral}")

conn.close()
