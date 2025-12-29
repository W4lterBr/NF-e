"""
Script de migração: Chave Local → Chave Mestre Portável

QUANDO USAR:
- ANTES de gerar o executável (.exe)
- Quando quiser distribuir o sistema para outros PCs
- Para tornar o banco de dados portável

O QUE FAZ:
1. Descriptografa senhas com chave local (%USERPROFILE%\.bot_nfe\key.bin)
2. Re-criptografa com chave mestre (embutida no código)
3. Atualiza banco de dados
4. Agora o banco funciona em qualquer PC!

IMPORTANTE:
- Execute APENAS UMA VEZ antes de gerar .exe
- Cria backup automático
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from modules.crypto_portable import migrate_to_portable_crypto, get_portable_crypto
from modules.crypto_utils import get_crypto
import sqlite3
import shutil
from datetime import datetime


def criar_backup(db_path: Path) -> Path:
    """Cria backup do banco antes da migração."""
    backup_path = db_path.parent / f"notas_backup_portable_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(db_path, backup_path)
    return backup_path


def testar_migracao(db_path: Path) -> bool:
    """Testa se migração funcionou."""
    crypto_portable = get_portable_crypto()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, informante, senha FROM certificados WHERE senha IS NOT NULL AND senha != ''")
    certs = cursor.fetchall()
    
    print("\n" + "="*70)
    print("  TESTE DE DESCRIPTOGRAFIA COM CHAVE PORTÁVEL")
    print("="*70 + "\n")
    
    sucesso = 0
    falhas = 0
    
    for cert_id, informante, senha_criptografada in certs:
        try:
            senha = crypto_portable.decrypt(senha_criptografada)
            
            if senha and len(senha) > 0:
                print(f"✅ ID {cert_id:3d} | {informante:20s} | OK ({len(senha)} chars)")
                sucesso += 1
            else:
                print(f"❌ ID {cert_id:3d} | {informante:20s} | Senha vazia")
                falhas += 1
        except Exception as e:
            print(f"❌ ID {cert_id:3d} | {informante:20s} | ERRO: {e}")
            falhas += 1
    
    conn.close()
    
    print(f"\n{'='*70}")
    print(f"  Sucesso: {sucesso} | Falhas: {falhas}")
    print(f"{'='*70}\n")
    
    return falhas == 0


def main():
    """Executa migração para chave portável."""
    db_path = Path(__file__).parent / "notas.db"
    
    if not db_path.exists():
        print(f"❌ Banco de dados não encontrado: {db_path}")
        return 1
    
    print("🔄 MIGRAÇÃO PARA CHAVE PORTÁVEL")
    print(f"📁 Banco de dados: {db_path}\n")
    
    # Verifica se já está usando chave portável
    crypto_local = get_crypto()
    crypto_portable = get_portable_crypto()
    
    if crypto_local.key == crypto_portable.key:
        print("⚠️  Sistema JÁ está usando chave portável!")
        print("   Não é necessário migrar novamente.\n")
        
        if testar_migracao(db_path):
            print("✅ Banco de dados está pronto para distribuição!")
            return 0
        else:
            print("❌ Erro ao testar banco de dados")
            return 1
    
    # Criar backup
    print("📦 Criando backup...")
    backup_path = criar_backup(db_path)
    print(f"✅ Backup criado: {backup_path}\n")
    
    # Confirmar
    print("⚠️  ATENÇÃO:")
    print("   - Senhas serão re-criptografadas com CHAVE MESTRE")
    print("   - Banco funcionará em QUALQUER PC")
    print("   - Chave local (%USERPROFILE%) NÃO será mais usada\n")
    
    resposta = input("Continuar? (sim/não): ").strip().lower()
    
    if resposta not in ['sim', 's', 'yes', 'y']:
        print("\n❌ Migração cancelada.")
        return 1
    
    # Executar migração
    print("\n🔄 Executando migração...\n")
    
    try:
        migrate_to_portable_crypto(db_path)
    except Exception as e:
        print(f"\n❌ ERRO durante migração: {e}")
        import traceback
        traceback.print_exc()
        print(f"\n⚠️  Restaure o backup: {backup_path}")
        return 1
    
    # Testar
    if testar_migracao(db_path):
        print("\n🎉 MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print(f"\n✅ Agora você pode:")
        print(f"   1. Gerar o executável: pyinstaller BOT_Busca_NFE.spec")
        print(f"   2. Distribuir para outros PCs")
        print(f"   3. Banco de dados funcionará em qualquer lugar!")
        print(f"\n📁 Backup mantido em: {backup_path}")
        return 0
    else:
        print("\n❌ Erro no teste pós-migração!")
        print(f"⚠️  Restaure o backup: {backup_path}")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Migração cancelada (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
