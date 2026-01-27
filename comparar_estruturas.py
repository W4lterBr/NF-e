import sqlite3

# Verifica estrutura das tabelas
print("Estrutura de notas.db:")
conn1 = sqlite3.connect('notas.db')
c1 = conn1.cursor()
c1.execute("PRAGMA table_info(notas_detalhadas)")
colunas_principal = c1.fetchall()
for col in colunas_principal:
    print(f"  {col[1]} ({col[2]})")
conn1.close()

print(f"\nTotal: {len(colunas_principal)} colunas")

print("\n" + "="*50)

print("\nEstrutura de notas_test.db:")
conn2 = sqlite3.connect('notas_test.db')
c2 = conn2.cursor()
c2.execute("PRAGMA table_info(notas_detalhadas)")
colunas_test = c2.fetchall()
for col in colunas_test:
    print(f"  {col[1]} ({col[2]})")
conn2.close()

print(f"\nTotal: {len(colunas_test)} colunas")
