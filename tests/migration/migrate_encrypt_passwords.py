"""
Script de migração para criptografar senhas existentes no banco de dados.

IMPORTANTE: Execute este script UMA ÚNICA VEZ após atualizar o sistema.

O que este script faz:
1. Verifica se há senhas em texto claro no banco
2. Criptografa todas as senhas encontradas
3. Atualiza o banco de dados
4. Cria backup antes de modificar

Uso:
    python migrate_encrypt_passwords.py

"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from modules.crypto_utils import get_crypto


def criar_backup(db_path: Path) -> Path:
    """Cria backup do banco de dados antes da migração."""
    backup_path = db_path.parent / f"notas_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    import shutil
    shutil.copy2(db_path, backup_path)
    
    return backup_path


def verificar_senhas_criptografadas(db_path: Path) -> dict:
    """
    Verifica estado das senhas no banco.
    
    Returns:
        dict com contadores de senhas criptografadas e em texto claro
    """
    crypto = get_crypto()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Verifica senhas na tabela certificados
    cursor.execute("SELECT id, informante, senha FROM certificados")
    certificados = cursor.fetchall()
    
    criptografadas = 0
    texto_claro = 0
    vazias = 0
    
    for cert_id, informante, senha in certificados:
        if not senha:
            vazias += 1
        elif crypto.is_encrypted(senha):
            criptografadas += 1
        else:
            texto_claro += 1
    
    conn.close()
    
    return {
        'total': len(certificados),
        'criptografadas': criptografadas,
        'texto_claro': texto_claro,
        'vazias': vazias
    }


def migrar_senhas(db_path: Path, dry_run: bool = False) -> dict:
    """
    Migra senhas de texto claro para criptografadas.
    
    Args:
        db_path: Caminho do banco de dados
        dry_run: Se True, apenas simula sem modificar
    
    Returns:
        dict com estatísticas da migração
    """
    crypto = get_crypto()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Busca todas as senhas
    cursor.execute("SELECT id, informante, senha FROM certificados")
    certificados = cursor.fetchall()
    
    migradas = 0
    ja_criptografadas = 0
    vazias = 0
    erros = 0
    
    print(f"\n{'=' * 70}")
    print(f"  MIGRAÇÃO DE SENHAS - {'SIMULAÇÃO' if dry_run else 'EXECUÇÃO REAL'}")
    print(f"{'=' * 70}\n")
    
    for cert_id, informante, senha in certificados:
        if not senha:
            print(f"⚪ ID {cert_id:3d} | {informante:20s} | [VAZIA]")
            vazias += 1
            continue
        
        if crypto.is_encrypted(senha):
            print(f"✅ ID {cert_id:3d} | {informante:20s} | Já criptografada")
            ja_criptografadas += 1
            continue
        
        # Senha em texto claro - precisa criptografar
        try:
            senha_criptografada = crypto.encrypt(senha)
            
            if not dry_run:
                cursor.execute(
                    "UPDATE certificados SET senha = ? WHERE id = ?",
                    (senha_criptografada, cert_id)
                )
            
            # Mostra apenas parte da senha original (segurança)
            senha_mascarada = senha[:3] + '*' * (len(senha) - 3) if len(senha) > 3 else '***'
            print(f"🔐 ID {cert_id:3d} | {informante:20s} | '{senha_mascarada}' → CRIPTOGRAFADA")
            migradas += 1
        
        except Exception as e:
            print(f"❌ ID {cert_id:3d} | {informante:20s} | ERRO: {e}")
            erros += 1
    
    if not dry_run:
        conn.commit()
    
    conn.close()
    
    print(f"\n{'=' * 70}")
    print(f"  RESUMO DA MIGRAÇÃO")
    print(f"{'=' * 70}")
    print(f"  Total de certificados:    {len(certificados)}")
    print(f"  ✅ Já criptografadas:     {ja_criptografadas}")
    print(f"  🔐 Migradas agora:        {migradas}")
    print(f"  ⚪ Senhas vazias:         {vazias}")
    print(f"  ❌ Erros:                 {erros}")
    print(f"{'=' * 70}\n")
    
    return {
        'total': len(certificados),
        'migradas': migradas,
        'ja_criptografadas': ja_criptografadas,
        'vazias': vazias,
        'erros': erros
    }


def testar_descriptografia(db_path: Path):
    """Testa se as senhas podem ser descriptografadas corretamente."""
    crypto = get_crypto()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, informante, senha FROM certificados WHERE senha IS NOT NULL AND senha != ''")
    certificados = cursor.fetchall()
    
    print(f"\n{'=' * 70}")
    print(f"  TESTE DE DESCRIPTOGRAFIA")
    print(f"{'=' * 70}\n")
    
    sucesso = 0
    falhas = 0
    
    for cert_id, informante, senha_criptografada in certificados:
        try:
            senha_descriptografada = crypto.decrypt(senha_criptografada)
            
            if senha_descriptografada:
                # Mostra apenas tamanho da senha (segurança)
                print(f"✅ ID {cert_id:3d} | {informante:20s} | OK ({len(senha_descriptografada)} caracteres)")
                sucesso += 1
            else:
                print(f"⚠️  ID {cert_id:3d} | {informante:20s} | Senha vazia após descriptografar")
                falhas += 1
        
        except Exception as e:
            print(f"❌ ID {cert_id:3d} | {informante:20s} | ERRO: {e}")
            falhas += 1
    
    conn.close()
    
    print(f"\n{'=' * 70}")
    print(f"  Sucesso: {sucesso} | Falhas: {falhas}")
    print(f"{'=' * 70}\n")
    
    return sucesso > 0 and falhas == 0


def main():
    """Função principal de migração."""
    # Localiza banco de dados
    db_path = Path(__file__).parent / "notas.db"
    
    if not db_path.exists():
        print(f"❌ Banco de dados não encontrado: {db_path}")
        print(f"\nVerifique se o arquivo 'notas.db' está na pasta do sistema.")
        return 1
    
    print("🔒 MIGRAÇÃO DE SENHAS - Sistema de Criptografia")
    print(f"📁 Banco de dados: {db_path}")
    print(f"🔑 Chave de criptografia: {get_crypto().key_file}\n")
    
    # Passo 1: Verificar estado atual
    print("=" * 70)
    print("  PASSO 1: Verificando estado atual das senhas")
    print("=" * 70)
    
    estado = verificar_senhas_criptografadas(db_path)
    
    print(f"\n📊 Estado atual:")
    print(f"   Total de certificados:  {estado['total']}")
    print(f"   ✅ Já criptografadas:   {estado['criptografadas']}")
    print(f"   🔓 Texto claro:         {estado['texto_claro']}")
    print(f"   ⚪ Vazias:              {estado['vazias']}\n")
    
    if estado['texto_claro'] == 0:
        print("✅ Todas as senhas já estão criptografadas!")
        print("\n🧪 Executando teste de descriptografia...")
        
        if testar_descriptografia(db_path):
            print("✅ Teste de descriptografia: SUCESSO")
            print("\n🎉 Sistema está funcionando corretamente!")
            return 0
        else:
            print("❌ Teste de descriptografia: FALHA")
            return 1
    
    # Passo 2: Criar backup
    print("\n" + "=" * 70)
    print("  PASSO 2: Criando backup do banco de dados")
    print("=" * 70 + "\n")
    
    backup_path = criar_backup(db_path)
    print(f"✅ Backup criado: {backup_path}")
    
    # Passo 3: Simulação
    print("\n" + "=" * 70)
    print("  PASSO 3: Simulação (nenhuma alteração será feita)")
    print("=" * 70)
    
    migrar_senhas(db_path, dry_run=True)
    
    # Passo 4: Confirmação
    print("\n⚠️  ATENÇÃO: As senhas serão criptografadas permanentemente!")
    print("   Um backup foi criado, mas é recomendado verificar antes de prosseguir.\n")
    
    resposta = input("Deseja continuar com a migração? (sim/não): ").strip().lower()
    
    if resposta not in ['sim', 's', 'yes', 'y']:
        print("\n❌ Migração cancelada pelo usuário.")
        print(f"   Backup mantido em: {backup_path}")
        return 1
    
    # Passo 5: Migração real
    print("\n" + "=" * 70)
    print("  PASSO 4: Executando migração (REAL)")
    print("=" * 70)
    
    resultado = migrar_senhas(db_path, dry_run=False)
    
    if resultado['erros'] > 0:
        print("\n⚠️  Migração concluída COM ERROS!")
        print(f"   Backup disponível em: {backup_path}")
        return 1
    
    # Passo 6: Teste de descriptografia
    print("\n" + "=" * 70)
    print("  PASSO 5: Testando descriptografia")
    print("=" * 70)
    
    if testar_descriptografia(db_path):
        print("\n🎉 MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print(f"   ✅ {resultado['migradas']} senhas foram criptografadas")
        print(f"   📁 Backup mantido em: {backup_path}")
        print(f"\n   Agora as senhas estão protegidas com criptografia AES-128.")
        print(f"   Chave armazenada em: {get_crypto().key_file}")
        return 0
    else:
        print("\n❌ ERRO: Falha no teste de descriptografia!")
        print(f"   Restaure o backup se necessário: {backup_path}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n❌ Migração cancelada pelo usuário (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
