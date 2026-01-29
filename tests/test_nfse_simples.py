#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste simples de NFS-e - Valida se o sistema consegue buscar NFS-e via API ADN
"""
import sys
import os

# Adiciona o diretório raiz ao path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

print("="*80)
print("🧪 TESTE DE NFS-e - INTEGRAÇÃO COM API ADN")
print("="*80)
print(f"📁 Diretório raiz: {ROOT_DIR}")

# Importa módulos
try:
    from modules.nfse_service import NFSeService
    print("✅ Módulo NFSeService importado com sucesso")
except ImportError as e:
    print(f"❌ Erro ao importar NFSeService: {e}")
    sys.exit(1)

# Carrega TODOS os certificados do banco de dados
import sqlite3

db_path = os.path.join(ROOT_DIR, 'notas.db')
print(f"\n📊 Banco de dados: {db_path}")

if not os.path.exists(db_path):
    print(f"❌ Banco de dados não encontrado: {db_path}")
    sys.exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.execute("""
    SELECT cnpj_cpf, caminho, senha, informante, cUF_autor, razao_social
    FROM certificados 
    WHERE ativo = 1
    ORDER BY cnpj_cpf
""")
certificados = cursor.fetchall()
conn.close()

if not certificados:
    print(f"❌ Nenhum certificado ativo encontrado no banco")
    sys.exit(1)

print(f"✅ {len(certificados)} certificado(s) encontrado(s)")
print("\n" + "="*80)

# Importa crypto para descriptografar senha
try:
    from modules.crypto_portable import get_portable_crypto
    crypto = get_portable_crypto()
except Exception as e:
    print(f"⚠️ Erro ao importar crypto (usando senhas sem descriptografar): {e}")
    crypto = None

# Testa cada certificado
resultados = []

for idx, (cnpj, cert_path, senha, informante, cuf, razao_social) in enumerate(certificados, 1):
    print(f"\n{'='*80}")
    print(f"🧪 TESTE {idx}/{len(certificados)}")
    print(f"{'='*80}")
    print(f"📋 Empresa: {razao_social or 'Sem razão social'}")
    print(f"   CNPJ: {cnpj}")
    print(f"   Informante: {informante}")
    print(f"   UF: {cuf}")
    
    if not os.path.exists(cert_path):
        print(f"❌ Arquivo do certificado não encontrado: {cert_path}")
        resultados.append({
            'cnpj': cnpj,
            'razao_social': razao_social,
            'status': 'ERRO',
            'mensagem': 'Certificado não encontrado'
        })
        continue
    
    # Descriptografa senha
    senha_uso = senha
    if crypto and crypto.is_encrypted(senha):
        try:
            senha_uso = crypto.decrypt(senha)
        except Exception as e:
            print(f"⚠️ Erro ao descriptografar senha: {e}")
    
    # Cria instância do serviço
    try:
        service = NFSeService(
            cert_path=cert_path,
            senha=senha_uso,
            informante=informante,
            cuf=cuf,
            ambiente='producao'
        )
        print("✅ NFSeService inicializado")
    except Exception as e:
        print(f"❌ Erro ao inicializar: {e}")
        resultados.append({
            'cnpj': cnpj,
            'razao_social': razao_social,
            'status': 'ERRO',
            'mensagem': f'Erro inicialização: {str(e)}'
        })
        continue
    
    # Executa consulta por NSU
    print(f"🔍 Consultando NFS-e (NSU inicial: 0)...")
    
    try:
        resultado = service.consultar_nsu("000000000000000")
        
        if resultado:
            # Extrai informações da resposta
            cStat, ultNSU, maxNSU = service.extrair_cstat_nsu(resultado)
            
            print(f"📊 Resposta ADN:")
            print(f"   cStat: {cStat if cStat else '(vazio)'}")
            print(f"   ultNSU: {ultNSU}")
            print(f"   maxNSU: {maxNSU}")
            
            if maxNSU == "000000000000000":
                print(f"   📌 SEM DOCUMENTOS")
                resultados.append({
                    'cnpj': cnpj,
                    'razao_social': razao_social,
                    'uf': cuf,
                    'status': 'SEM_DOCS',
                    'maxNSU': maxNSU
                })
            else:
                print(f"   ✅ DOCUMENTOS DISPONÍVEIS! (maxNSU: {maxNSU})")
                
                # Tenta extrair documentos
                docs = list(service.extrair_documentos(resultado))
                print(f"   📄 Documentos extraídos: {len(docs)}")
                
                resultados.append({
                    'cnpj': cnpj,
                    'razao_social': razao_social,
                    'uf': cuf,
                    'status': 'COM_DOCS',
                    'maxNSU': maxNSU,
                    'total_docs': len(docs)
                })
        else:
            print(f"❌ Nenhuma resposta do ADN")
            resultados.append({
                'cnpj': cnpj,
                'razao_social': razao_social,
                'status': 'SEM_RESPOSTA'
            })
            
    except Exception as e:
        print(f"❌ Erro na consulta: {e}")
        resultados.append({
            'cnpj': cnpj,
            'razao_social': razao_social,
            'status': 'ERRO',
            'mensagem': str(e)
        })

# Resumo final
print("\n" + "="*80)
print("📊 RESUMO DOS TESTES")
print("="*80)

com_docs = [r for r in resultados if r.get('status') == 'COM_DOCS']
sem_docs = [r for r in resultados if r.get('status') == 'SEM_DOCS']
erros = [r for r in resultados if r.get('status') == 'ERRO']

print(f"\n✅ COM DOCUMENTOS: {len(com_docs)}")
for r in com_docs:
    print(f"   • {r['razao_social']} (UF:{r['uf']}) - maxNSU: {r['maxNSU']} - {r.get('total_docs', 0)} docs")

print(f"\n📭 SEM DOCUMENTOS: {len(sem_docs)}")
for r in sem_docs:
    print(f"   • {r['razao_social']} (UF:{r['uf']}) - CNPJ: {r['cnpj']}")

if erros:
    print(f"\n❌ ERROS: {len(erros)}")
    for r in erros:
        print(f"   • {r['razao_social']} - {r.get('mensagem', 'Erro desconhecido')}")

print("\n" + "="*80)
print("✅ TESTE CONCLUÍDO")
print("="*80)
