"""Diagnóstico de busca NFS-e para CNPJ específico."""
import sqlite3

conn = sqlite3.connect('notas.db')

cnpj = '49068153000160'

print("=" * 70)
print(f"DIAGNÓSTICO NFS-e - CNPJ: {cnpj}")
print("=" * 70)

# 1. Verificar certificado
print(f"\n1️⃣ Certificado:")
cert = conn.execute("SELECT informante, caminho, ativo, razao_social FROM certificados WHERE cnpj_cpf=?", (cnpj,)).fetchone()
if cert:
    print(f"   ✅ Encontrado: {cert[3]}")
    print(f"   📄 Arquivo: {cert[1]}")
    print(f"   {'✅ ATIVO' if cert[2] else '❌ INATIVO'}")
else:
    print(f"   ❌ Certificado não encontrado!")

# 2. Verificar configuração NFS-e
print(f"\n2️⃣ Configuração NFS-e:")
configs = conn.execute("SELECT provedor, codigo_municipio, inscricao_municipal, ativo FROM nfse_config WHERE cnpj_cpf=?", (cnpj,)).fetchall()
if configs:
    for cfg in configs:
        print(f"   ✅ Provedor: {cfg[0]}")
        print(f"      Município: {cfg[1]}")
        print(f"      Inscrição: {cfg[2] or '(não informada)'}")
        print(f"      {'✅ ATIVO' if cfg[3] else '❌ INATIVO'}")
else:
    print(f"   ❌ Nenhuma configuração NFS-e encontrada!")
    print(f"   💡 Dica: Execute para adicionar:")
    print(f"      INSERT INTO nfse_config (cnpj_cpf, provedor, codigo_municipio, ativo)")
    print(f"      VALUES ('{cnpj}', 'ADN', '5205497', 1);")

# 3. Verificar NSU atual
print(f"\n3️⃣ NSU Atual:")
nsu_row = conn.execute("SELECT ult_nsu, data_ultima_busca, total_notas FROM nsu_nfse WHERE informante=?", (cnpj,)).fetchone()
if nsu_row:
    print(f"   📊 Último NSU: {nsu_row[0]}")
    print(f"   📅 Última busca: {nsu_row[1]}")
    print(f"   📝 Total de notas: {nsu_row[2]}")
else:
    print(f"   ⚠️  Registro NSU não existe (será criado na primeira busca)")

# 4. Verificar NFS-e já baixadas
print(f"\n4️⃣ NFS-e já baixadas:")
nfse_count = conn.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE tipo='NFS-e' AND informante=?", (cnpj,)).fetchone()[0]
print(f"   📋 Total: {nfse_count} NFS-e")

if nfse_count > 0:
    print(f"\n   Últimas 5 NFS-e:")
    rows = conn.execute("""
        SELECT numero, data_emissao, valor, nome_emitente, xml_status 
        FROM notas_detalhadas 
        WHERE tipo='NFS-e' AND informante=? 
        ORDER BY data_emissao DESC 
        LIMIT 5
    """, (cnpj,)).fetchall()
    for row in rows:
        print(f"      • {row[0]} - {row[1]} - R$ {row[2]:.2f} - {row[3]} - {row[4]}")

# 5. Verificar outros certificados que TÊM NFS-e
print(f"\n5️⃣ Outros certificados com NFS-e:")
outros = conn.execute("""
    SELECT DISTINCT informante, COUNT(*) as total
    FROM notas_detalhadas 
    WHERE tipo='NFS-e'
    GROUP BY informante
""").fetchall()

if outros:
    print(f"   Total de certificados com NFS-e: {len(outros)}")
    for outro in outros:
        cert_info = conn.execute("SELECT razao_social FROM certificados WHERE cnpj_cpf=?", (outro[0],)).fetchone()
        nome = cert_info[0] if cert_info else outro[0]
        print(f"      • {outro[0]}: {outro[1]} NFS-e - {nome}")
else:
    print(f"   ⚠️  Nenhum certificado tem NFS-e no banco")

# 6. Análise do problema
print(f"\n" + "=" * 70)
print("ANÁLISE DO PROBLEMA")
print("=" * 70)

problemas = []

if not cert:
    problemas.append("Certificado não cadastrado")
elif not cert[2]:
    problemas.append("Certificado está INATIVO")

if not configs:
    problemas.append("Sem configuração NFS-e (tabela nfse_config)")
elif not any(cfg[3] for cfg in configs):
    problemas.append("Todas as configurações NFS-e estão INATIVAS")

# Verificar se realmente tem NFS-e para buscar
if nfse_count == 0 and not nsu_row:
    problemas.append("Possível ausência de documentos no Ambiente Nacional")

if problemas:
    print("\n❌ PROBLEMAS IDENTIFICADOS:")
    for i, prob in enumerate(problemas, 1):
        print(f"   {i}. {prob}")
    
    print("\n💡 SOLUÇÕES SUGERIDAS:")
    if "Sem configuração NFS-e" in problemas[0] if problemas else "":
        print(f"   • Adicione configuração ADN:")
        print(f"     INSERT INTO nfse_config (cnpj_cpf, provedor, codigo_municipio, ativo)")
        print(f"     VALUES ('{cnpj}', 'ADN', '5205497', 1);")
    
    if "Certificado está INATIVO" in str(problemas):
        print(f"   • Ative o certificado:")
        print(f"     UPDATE certificados SET ativo=1 WHERE cnpj_cpf='{cnpj}';")
    
    if "ausência de documentos" in str(problemas):
        print(f"   • Verifique se a empresa REALMENTE emite NFS-e")
        print(f"   • Teste com o outro certificado que JÁ TEM NFS-e funcionando:")
        if outros:
            print(f"     CNPJ de teste: {outros[0][0]}")
else:
    print("\n✅ CONFIGURAÇÃO CORRETA!")
    print("\n🔍 POSSÍVEIS MOTIVOS PARA NÃO RETORNAR DOCUMENTOS:")
    print("   1. Empresa não emite NFS-e (apenas NF-e)")
    print("   2. Empresa não está ativa no município")
    print("   3. Ambiente Nacional ainda não tem dados dessa empresa")
    print("   4. API do ADN com problemas temporários")
    print("\n💡 RECOMENDAÇÃO:")
    print("   • Teste com certificado que já funcionou (33251845000109)")
    print("   • Verifique na prefeitura se a empresa emite NFS-e")

conn.close()
print("=" * 70)
