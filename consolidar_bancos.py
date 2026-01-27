"""
Script para consolidar todos os dados em um único banco: notas.db
"""
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

# Bancos de dados
BANCO_PRINCIPAL = "notas.db"
BANCO_TEST = "notas_test.db"
BANCO_NFE_DATA = "nfe_data.db"

def backup_banco(caminho):
    """Faz backup do banco antes de modificar"""
    if Path(caminho).exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = f"{caminho.replace('.db', '')}_backup_{timestamp}.db"
        shutil.copy2(caminho, backup)
        print(f"✅ Backup criado: {backup}")
        return backup
    return None

def migrar_nfse_para_principal():
    """Migra NFS-e de notas_test.db para notas.db"""
    print("\n" + "="*80)
    print("CONSOLIDANDO BANCOS DE DADOS")
    print("="*80 + "\n")
    
    # Verifica se existem os bancos
    if not Path(BANCO_TEST).exists():
        print(f"❌ {BANCO_TEST} não encontrado!")
        return
    
    if not Path(BANCO_PRINCIPAL).exists():
        print(f"❌ {BANCO_PRINCIPAL} não encontrado!")
        return
    
    # Backup do banco principal
    print("📦 Fazendo backup do banco principal...")
    backup_banco(BANCO_PRINCIPAL)
    
    # Conecta aos dois bancos
    conn_test = sqlite3.connect(BANCO_TEST)
    conn_principal = sqlite3.connect(BANCO_PRINCIPAL)
    
    try:
        # Conta NFS-e no banco test
        c_test = conn_test.cursor()
        c_test.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE tipo='NFS-e'")
        total_nfse = c_test.fetchone()[0]
        print(f"\n📊 Encontradas {total_nfse} NFS-e em {BANCO_TEST}")
        
        if total_nfse == 0:
            print("⚠️  Nenhuma NFS-e para migrar")
            return
        
        # Busca todas as NFS-e
        c_test.execute("SELECT * FROM notas_detalhadas WHERE tipo='NFS-e'")
        colunas = [desc[0] for desc in c_test.description]
        nfse_rows = c_test.fetchall()
        
        # Busca XMLs baixados das NFS-e
        chaves_nfse = [row[colunas.index('chave')] for row in nfse_rows]
        placeholders = ','.join('?' * len(chaves_nfse))
        c_test.execute(f"SELECT * FROM xmls_baixados WHERE chave IN ({placeholders})", chaves_nfse)
        colunas_xmls = [desc[0] for desc in c_test.description]
        xmls_rows = c_test.fetchall()
        
        print(f"📄 Encontrados {len(xmls_rows)} XMLs relacionados")
        
        # Insere no banco principal
        c_principal = conn_principal.cursor()
        
        print("\n🔄 Migrando dados...")
        
        # Insere notas detalhadas
        importados = 0
        duplicados = 0
        for row in nfse_rows:
            chave = row[colunas.index('chave')]
            
            # Verifica se já existe
            c_principal.execute("SELECT chave FROM notas_detalhadas WHERE chave=?", (chave,))
            if c_principal.fetchone():
                duplicados += 1
                continue
            
            # Insere
            placeholders_insert = ','.join('?' * len(row))
            c_principal.execute(f"INSERT INTO notas_detalhadas VALUES ({placeholders_insert})", row)
            importados += 1
        
        print(f"  ✅ {importados} NFS-e importadas")
        print(f"  ⏭️  {duplicados} já existiam")
        
        # Insere XMLs baixados
        xmls_importados = 0
        xmls_duplicados = 0
        for row in xmls_rows:
            chave = row[colunas_xmls.index('chave')]
            
            # Verifica se já existe
            c_principal.execute("SELECT chave FROM xmls_baixados WHERE chave=?", (chave,))
            if c_principal.fetchone():
                xmls_duplicados += 1
                continue
            
            # Insere
            placeholders_insert = ','.join('?' * len(row))
            c_principal.execute(f"INSERT INTO xmls_baixados VALUES ({placeholders_insert})", row)
            xmls_importados += 1
        
        print(f"  ✅ {xmls_importados} registros de XML importados")
        print(f"  ⏭️  {xmls_duplicados} já existiam")
        
        # Commit
        conn_principal.commit()
        
        # Verifica resultado final
        c_principal.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE tipo='NFS-e'")
        total_final = c_principal.fetchone()[0]
        
        print("\n" + "="*80)
        print("📊 RESUMO FINAL")
        print("="*80)
        print(f"✅ Total de NFS-e em {BANCO_PRINCIPAL}: {total_final}")
        print(f"📦 Backup salvo antes da migração")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERRO durante migração: {e}")
        import traceback
        traceback.print_exc()
        conn_principal.rollback()
    finally:
        conn_test.close()
        conn_principal.close()

def listar_bancos_desnecessarios():
    """Lista bancos que podem ser deletados após migração"""
    print("\n" + "="*80)
    print("🗑️  BANCOS QUE PODEM SER DELETADOS")
    print("="*80)
    
    bancos_desnecessarios = [
        "notas_test.db",
        "test.db",
        "test_no_downgrade.db",
        "configuracoes.db",
        "nfe_config.db",
        "fluxo_caixa.db"
    ]
    
    for banco in bancos_desnecessarios:
        if Path(banco).exists():
            tamanho = Path(banco).stat().st_size / 1024  # KB
            print(f"  - {banco} ({tamanho:.1f} KB)")
    
    print("\n💡 Para deletar, execute:")
    print("   Remove-Item notas_test.db, test*.db, configuracoes.db, nfe_config.db, fluxo_caixa.db")
    print("="*80 + "\n")

if __name__ == "__main__":
    migrar_nfse_para_principal()
    listar_bancos_desnecessarios()
