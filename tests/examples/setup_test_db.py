#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para copiar certificados do banco de produção para o banco de teste

Este script copia apenas a configuração dos certificados (sem NSUs ou XMLs),
permitindo testar no ambiente de homologação sem afetar dados de produção.
"""

import sqlite3
import shutil
from pathlib import Path

def setup_test_database():
    """Copia certificados de notas.db para notas_test.db"""
    
    db_prod = Path("notas.db")
    db_test = Path("notas_test.db")
    
    print("=" * 80)
    print("🔧 CONFIGURAÇÃO DO BANCO DE TESTE")
    print("=" * 80)
    print()
    
    # Verifica se banco de produção existe
    if not db_prod.exists():
        print(f"❌ Erro: Banco de produção não encontrado: {db_prod}")
        print()
        print("Execute a interface gráfica primeiro para criar o banco de produção.")
        return False
    
    print(f"✅ Banco de produção encontrado: {db_prod}")
    
    # Backup do banco de teste se existir
    if db_test.exists():
        backup = db_test.with_suffix('.db.bak')
        shutil.copy(db_test, backup)
        print(f"📦 Backup criado: {backup}")
    
    # Conecta aos bancos
    try:
        conn_prod = sqlite3.connect(db_prod)
        conn_test = sqlite3.connect(db_test)
        
        # Copia estrutura das tabelas necessárias
        print()
        print("📋 Copiando estrutura das tabelas...")
        
        # Obtém DDL das tabelas de certificados
        cursor_prod = conn_prod.cursor()
        
        # Drop tabela certificados se existir
        conn_test.execute("DROP TABLE IF EXISTS certificados")
        
        # Tabela certificados
        ddl = cursor_prod.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='certificados'"
        ).fetchone()
        
        if ddl:
            conn_test.execute(ddl[0])
            print("   ✅ Tabela 'certificados' criada")
        else:
            print("   ⚠️ Tabela 'certificados' não encontrada no banco de produção")
            return False
        
        # Copia dados dos certificados
        print()
        print("📥 Copiando certificados...")
        
        certs = cursor_prod.execute("SELECT * FROM certificados").fetchall()
        
        if not certs:
            print("   ⚠️ Nenhum certificado encontrado no banco de produção")
            conn_prod.close()
            conn_test.close()
            return False
        
        # Obtém nomes das colunas
        cols = [desc[0] for desc in cursor_prod.description]
        placeholders = ','.join(['?' for _ in cols])
        
        for cert in certs:
            conn_test.execute(
                f"INSERT OR REPLACE INTO certificados ({','.join(cols)}) VALUES ({placeholders})",
                cert
            )
            print(f"   ✅ Certificado copiado: {cert[0]}")  # cert[0] = cnpj_cpf
        
        conn_test.commit()
        
        # Cria tabelas auxiliares com NSU zerado
        print()
        print("📋 Criando tabelas auxiliares...")
        
        # Tabela NSU (NF-e) - começa do zero
        conn_test.execute('''
            CREATE TABLE IF NOT EXISTS nsu (
                informante TEXT PRIMARY KEY,
                ult_nsu TEXT
            )
        ''')
        
        # Inicializa NSU zerado para cada certificado
        for cert in certs:
            informante = cert[3] if len(cert) > 3 else cert[0]  # informante ou cnpj_cpf
            conn_test.execute(
                "INSERT OR REPLACE INTO nsu (informante, ult_nsu) VALUES (?, '000000000000000')",
                (informante,)
            )
        
        print("   ✅ Tabela 'nsu' criada (NSUs zerados)")
        
        # Tabela NSU CT-e - começa do zero
        conn_test.execute('''
            CREATE TABLE IF NOT EXISTS nsu_cte (
                informante TEXT PRIMARY KEY,
                ult_nsu TEXT
            )
        ''')
        
        for cert in certs:
            informante = cert[3] if len(cert) > 3 else cert[0]
            conn_test.execute(
                "INSERT OR REPLACE INTO nsu_cte (informante, ult_nsu) VALUES (?, '000000000000000')",
                (informante,)
            )
        
        print("   ✅ Tabela 'nsu_cte' criada (NSUs zerados)")
        
        # Outras tabelas necessárias
        conn_test.execute('''
            CREATE TABLE IF NOT EXISTS xmls_baixados (
                chave TEXT PRIMARY KEY,
                cnpj_cpf TEXT
            )
        ''')
        print("   ✅ Tabela 'xmls_baixados' criada")
        
        conn_test.execute('''
            CREATE TABLE IF NOT EXISTS nf_status (
                chNFe TEXT PRIMARY KEY,
                cStat TEXT,
                xMotivo TEXT
            )
        ''')
        print("   ✅ Tabela 'nf_status' criada")
        
        conn_test.execute('''
            CREATE TABLE IF NOT EXISTS erro_656 (
                informante TEXT PRIMARY KEY,
                ultimo_erro TEXT,
                nsu_bloqueado TEXT
            )
        ''')
        print("   ✅ Tabela 'erro_656' criada")
        
        conn_test.execute('''
            CREATE TABLE IF NOT EXISTS config (
                chave TEXT PRIMARY KEY,
                valor TEXT
            )
        ''')
        print("   ✅ Tabela 'config' criada")
        
        conn_test.commit()
        
        # Fecha conexões
        conn_prod.close()
        conn_test.close()
        
        print()
        print("=" * 80)
        print("✅ BANCO DE TESTE CONFIGURADO COM SUCESSO!")
        print("=" * 80)
        print()
        print(f"📂 Banco de teste: {db_test}")
        print(f"📊 Certificados copiados: {len(certs)}")
        print(f"🔄 NSUs inicializados em: 000000000000000")
        print()
        print("💡 Próximo passo:")
        print("   python run_test.py")
        print()
        
        return True
        
    except Exception as e:
        print()
        print(f"❌ Erro ao configurar banco de teste: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    setup_test_database()
