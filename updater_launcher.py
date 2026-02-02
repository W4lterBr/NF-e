"""
Updater Launcher - Executado separadamente para substituir o executável principal
Desenvolvido por: DWM System Developer

Este script é executado FORA do processo principal para poder substituir o .exe
"""

import sys
import time
import shutil
from pathlib import Path
import subprocess
import os

def wait_for_process_to_close(process_name: str, timeout: int = 30):
    """Aguarda o processo principal fechar."""
    print(f"⏳ Aguardando {process_name} fechar...")
    import psutil
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        found = False
        for proc in psutil.process_iter(['name']):
            try:
                if process_name.lower() in proc.info['name'].lower():
                    found = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if not found:
            print("✅ Processo fechado!")
            return True
        
        time.sleep(0.5)
    
    print("⚠️ Timeout aguardando processo fechar")
    return False

def main():
    if len(sys.argv) < 3:
        print("❌ Uso: updater_launcher.py <novo_exe> <exe_destino> [nova_versao]")
        sys.exit(1)
    
    novo_exe = Path(sys.argv[1])
    exe_destino = Path(sys.argv[2])
    nova_versao = sys.argv[3] if len(sys.argv) > 3 else None
    
    print("=" * 60)
    print("🚀 UPDATER LAUNCHER - Atualização Automática")
    print("=" * 60)
    print(f"📥 Novo executável: {novo_exe}")
    print(f"📝 Destino: {exe_destino}")
    print()
    
    # Aguarda um pouco para garantir que o app principal fechou
    time.sleep(2)
    
    # Aguarda o processo fechar
    processo_principal = exe_destino.stem
    if not wait_for_process_to_close(processo_principal):
        print("⚠️ Continuando mesmo sem confirmar fechamento...")
    
    try:
        # Faz backup do executável antigo
        backup_path = exe_destino.with_suffix('.exe.bak')
        if exe_destino.exists():
            print(f"💾 Criando backup: {backup_path.name}")
            shutil.copy2(exe_destino, backup_path)
        
        # Substitui o executável
        print("🔄 Substituindo executável...")
        if novo_exe.exists():
            shutil.move(str(novo_exe), str(exe_destino))
            print("✅ Executável atualizado com sucesso!")
            
            # Atualiza version.txt se nova versão foi fornecida
            if nova_versao:
                version_file = exe_destino.parent / 'version.txt'
                print(f"📝 Atualizando version.txt para {nova_versao}...")
                try:
                    version_file.write_text(nova_versao, encoding='utf-8')
                    print("✅ version.txt atualizado!")
                except Exception as e:
                    print(f"⚠️ Erro ao atualizar version.txt: {e}")
        else:
            print(f"❌ Erro: Arquivo {novo_exe} não encontrado!")
            sys.exit(1)
        
        # Aguarda um pouco antes de reiniciar
        print("⏳ Aguardando 2 segundos...")
        time.sleep(2)
        
        # Reinicia a aplicação
        print(f"🚀 Reiniciando aplicação: {exe_destino}")
        
        # Usa subprocess.Popen para não bloquear
        # E executa em segundo plano sem manter o launcher aberto
        if os.name == 'nt':  # Windows
            subprocess.Popen(
                [str(exe_destino)],
                cwd=str(exe_destino.parent),
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                close_fds=True
            )
        else:  # Linux/Mac
            subprocess.Popen(
                [str(exe_destino)],
                cwd=str(exe_destino.parent),
                start_new_session=True,
                close_fds=True
            )
        
        print("✅ Atualização concluída! Aplicação reiniciada.")
        print()
        print("Esta janela fechará em 3 segundos...")
        time.sleep(3)
        
    except Exception as e:
        print(f"❌ ERRO durante atualização: {e}")
        print()
        print("Tentando restaurar backup...")
        
        # Tenta restaurar backup
        if backup_path.exists() and not exe_destino.exists():
            try:
                shutil.copy2(backup_path, exe_destino)
                print("✅ Backup restaurado!")
            except Exception as restore_error:
                print(f"❌ Falha ao restaurar backup: {restore_error}")
        
        print()
        print("Pressione ENTER para fechar...")
        input()
        sys.exit(1)

if __name__ == "__main__":
    main()
