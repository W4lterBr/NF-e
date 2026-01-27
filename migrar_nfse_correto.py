"""
Migra NFS-e de notas_test.db para notas.db com mapeamento correto de colunas
"""
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

# Backup
print("Fazendo backup de notas.db...")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2("notas.db", f"notas_backup_{timestamp}.db")
print(f"Backup: notas_backup_{timestamp}.db")

# Conecta aos bancos
conn_test = sqlite3.connect('notas_test.db')
conn_principal = sqlite3.connect('notas.db')

c_test = conn_test.cursor()
c_principal = conn_principal.cursor()

# Busca NFS-e do banco test
c_test.execute("SELECT * FROM notas_detalhadas WHERE tipo='NFS-e'")
colunas_test = [desc[0] for desc in c_test.description]
rows = c_test.fetchall()

print(f"\nEncontradas {len(rows)} NFS-e para migrar\n")

# Mapeamento de colunas (test -> principal)
# test: chave, ie_tomador, nome_emitente, cnpj_emitente, numero, data_emissao, tipo, valor, cfop, vencimento, ncm, status, natureza, uf, base_icms, valor_icms, informante, xml_status, atualizado_em, cnpj_destinatario, nome_destinatario
# principal: chave, ie_tomador, nome_emitente, cnpj_emitente, numero, data_emissao, tipo, valor, cfop, vencimento, uf, natureza, status, atualizado_em, cnpj_destinatario, nome_destinatario, xml_status, informante, nsu, base_icms, valor_icms, ncm, pdf_path

importados = 0
duplicados = 0

for row in rows:
    # Extrai dados do row
    dados_test = dict(zip(colunas_test, row))
    
    # Verifica duplicado
    c_principal.execute("SELECT chave FROM notas_detalhadas WHERE chave=?", (dados_test['chave'],))
    if c_principal.fetchone():
        duplicados += 1
        continue
    
    # Mapeia para estrutura principal (na ordem correta)
    valores_principal = (
        dados_test['chave'],
        dados_test['ie_tomador'],
        dados_test['nome_emitente'],
        dados_test['cnpj_emitente'],
        dados_test['numero'],
        dados_test['data_emissao'],
        dados_test['tipo'],
        dados_test['valor'],
        dados_test['cfop'],
        dados_test['vencimento'],
        dados_test['uf'],
        dados_test['natureza'],
        dados_test['status'],
        dados_test['atualizado_em'],
        dados_test.get('cnpj_destinatario', ''),
        dados_test.get('nome_destinatario', ''),
        dados_test['xml_status'],
        dados_test['informante'],
        '',  # nsu (vazio para NFS-e)
        dados_test['base_icms'],
        dados_test['valor_icms'],
        dados_test['ncm'],
        ''   # pdf_path (vazio por enquanto)
    )
    
    c_principal.execute('''
        INSERT INTO notas_detalhadas (
            chave, ie_tomador, nome_emitente, cnpj_emitente, numero, data_emissao, tipo, valor,
            cfop, vencimento, uf, natureza, status, atualizado_em, cnpj_destinatario,
            nome_destinatario, xml_status, informante, nsu, base_icms, valor_icms, ncm, pdf_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', valores_principal)
    
    importados += 1
    if importados % 20 == 0:
        print(f"  Importadas: {importados}/{len(rows)}")

# Migra xmls_baixados
print("\nMigrando XMLs baixados...")
c_test.execute("SELECT chave FROM notas_detalhadas WHERE tipo='NFS-e'")
chaves = [r[0] for r in c_test.fetchall()]

xmls_importados = 0
for chave in chaves:
    c_test.execute("SELECT * FROM xmls_baixados WHERE chave=?", (chave,))
    row = c_test.fetchone()
    if not row:
        continue
    
    # Verifica duplicado
    c_principal.execute("SELECT chave FROM xmls_baixados WHERE chave=?", (chave,))
    if c_principal.fetchone():
        continue
    
    # Insere
    c_principal.execute("INSERT OR REPLACE INTO xmls_baixados VALUES (?, ?, ?, ?, ?)", row)
    xmls_importados += 1

# Commit
conn_principal.commit()

# Resultado
c_principal.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE tipo='NFS-e'")
total_final = c_principal.fetchone()[0]

print("\n" + "="*60)
print("RESULTADO DA MIGRACAO")
print("="*60)
print(f"OK Importadas: {importados}")
print(f">> Duplicadas: {duplicados}")
print(f"OK XMLs migrados: {xmls_importados}")
print(f">> Total NFS-e em notas.db: {total_final}")
print("="*60)

conn_test.close()
conn_principal.close()
