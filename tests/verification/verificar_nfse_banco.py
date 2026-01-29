import sqlite3

conn = sqlite3.connect('notas.db')

total = conn.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE tipo='NFS-e'").fetchone()[0]
print(f'✅ Total NFS-e no banco: {total}')

if total > 0:
    print('\n📊 Por certificado:')
    for row in conn.execute("SELECT informante, COUNT(*) as total FROM notas_detalhadas WHERE tipo='NFS-e' GROUP BY informante"):
        cert = conn.execute("SELECT razao_social FROM certificados WHERE cnpj_cpf=?", (row[0],)).fetchone()
        nome = cert[0] if cert else row[0]
        print(f'  • {nome}: {row[1]} NFS-e')
    
    print(f'\n📅 Últimas 5 NFS-e:')
    for row in conn.execute("SELECT numero, data_emissao, valor, nome_emitente, informante FROM notas_detalhadas WHERE tipo='NFS-e' ORDER BY data_emissao DESC LIMIT 5"):
        print(f'  • {row[0]} - {row[1]} - R$ {row[2]:.2f} - {row[3][:30]}')
else:
    print('\n⚠️  Nenhuma NFS-e no banco ainda')

conn.close()
