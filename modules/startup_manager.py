"""
Gerenciador de Inicialização Automática do Windows
Controla a entrada no registro para iniciar com o Windows
"""
import winreg
import os
import sys
from pathlib import Path


class StartupManager:
    """Gerencia a inicialização automática do aplicativo com o Windows"""
    
    def __init__(self, app_name: str = "BOT Busca NFE"):
        self.app_name = app_name
        self.reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
    def get_executable_path(self) -> str:
        """Retorna o caminho do executável ou script atual"""
        if getattr(sys, 'frozen', False):
            # Executável compilado
            return sys.executable
        else:
            # Modo desenvolvimento - retorna caminho do Python + script
            script_path = Path(__file__).parent.parent / "Busca NF-e.py"
            python_exe = sys.executable
            return f'"{python_exe}" "{script_path}" --startup'
    
    def is_startup_enabled(self) -> bool:
        """Verifica se a inicialização automática está habilitada"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.reg_path,
                0,
                winreg.KEY_READ
            )
            try:
                value, _ = winreg.QueryValueEx(key, self.app_name)
                winreg.CloseKey(key)
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except Exception as e:
            print(f"[STARTUP] Erro ao verificar inicialização: {e}")
            return False
    
    def enable_startup(self) -> bool:
        """Habilita a inicialização automática com o Windows"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.reg_path,
                0,
                winreg.KEY_SET_VALUE
            )
            
            exe_path = self.get_executable_path()
            # Adiciona flag --startup para iniciar minimizado
            if not exe_path.endswith('--startup'):
                exe_path = exe_path.rstrip('"') + ' --startup"' if exe_path.startswith('"') else f'{exe_path} --startup'
            
            winreg.SetValueEx(
                key,
                self.app_name,
                0,
                winreg.REG_SZ,
                exe_path
            )
            winreg.CloseKey(key)
            
            print(f"[STARTUP] ✓ Inicialização automática HABILITADA")
            print(f"[STARTUP]   Path: {exe_path}")
            return True
            
        except Exception as e:
            print(f"[STARTUP] ✗ Erro ao habilitar inicialização: {e}")
            return False
    
    def disable_startup(self) -> bool:
        """Desabilita a inicialização automática com o Windows"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.reg_path,
                0,
                winreg.KEY_SET_VALUE
            )
            
            try:
                winreg.DeleteValue(key, self.app_name)
                print(f"[STARTUP] ✓ Inicialização automática DESABILITADA")
                return True
            except FileNotFoundError:
                print(f"[STARTUP] Entrada não encontrada no registro")
                return True
            finally:
                winreg.CloseKey(key)
                
        except Exception as e:
            print(f"[STARTUP] ✗ Erro ao desabilitar inicialização: {e}")
            return False
    
    def toggle_startup(self) -> bool:
        """Alterna entre habilitar/desabilitar inicialização automática"""
        if self.is_startup_enabled():
            return self.disable_startup()
        else:
            return self.enable_startup()
