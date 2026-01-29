"""Adiciona configurações NFS-e para certificados sem configuração."""
import sqlite3

conn = sqlite3.connect('notas.db')

# CNPJs que precisam de configuração NFS-e
cnpjs_sem_config = [
    ('49068153000160', '5205497'),  # LUZ COMERCIO - Goiânia/GO
    ('01773924000193', '5002704'),  # ALFA COMPUTADORES - Campo Grande/MS
    ('48160135000140', '3106200'),  # JL COMERCIO - Belo Horizonte/MG
    ('47539664000197', '5205497'),  # PARTNESS FUTURA - Goiânia/GO
]

print("=" * 70)
print("ADICIONANDO CONFIGURAÇÕES NFS-e")
print("=" * 70)

for cnpj, cod_municipio in cnpjs_sem_config:
    # Verificar se já existe
    existe = conn.execute("SELECT COUNT(*) FROM nfse_config WHERE cnpj_cpf=? AND ativo=1", (cnpj,)).fetchone()[0]
    
    if existe:
        print(f"\n⚠️  {cnpj}: Já tem configuração ativa")
        continue
    
    # Buscar nome da empresa
    cert = conn.execute("SELECT razao_social FROM certificados WHERE cnpj_cpf=?", (cnpj,)).fetchone()
    nome = cert[0] if cert else cnpj
    
    # Adicionar configuração ADN
    conn.execute("""
        INSERT INTO nfse_config (cnpj_cpf, provedor, codigo_municipio, inscricao_municipal, ativo)
        VALUES (?, 'ADN', ?, '', 1)
    """, (cnpj, cod_municipio))
    
    print(f"\n✅ {cnpj}: {nome}")
    print(f"   Provedor: ADN (Ambiente Nacional)")
    print(f"   Município: {cod_municipio}")

conn.commit()

# Verificar resultado
print("\n" + "=" * 70)
print("CONFIGURAÇÕES FINAIS")
print("=" * 70)

configs = conn.execute("""
    SELECT c.cnpj_cpf, c.razao_social, n.provedor, n.codigo_municipio
    FROM certificados c
    LEFT JOIN nfse_config n ON c.cnpj_cpf = n.cnpj_cpf AND n.ativo = 1
    WHERE c.ativo = 1
    ORDER BY c.razao_social
""").fetchall()

for cfg in configs:
    cnpj, nome, provedor, municipio = cfg
    if provedor:
        print(f"\n✅ {nome}")
        print(f"   CNPJ: {cnpj}")
        print(f"   Provedor: {provedor} - Município: {municipio}")
    else:
        print(f"\n⚠️  {nome}")
        print(f"   CNPJ: {cnpj}")
        print(f"   SEM CONFIGURAÇÃO NFS-e")

conn.close()

print("\n" + "=" * 70)
print("✅ Configurações adicionadas! Execute a busca novamente.")
print("=" * 70)
