"""
Sistema de Atualização Automática via GitHub
Desenvolvido por: DWM System Developer
"""

import requests
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import shutil
import logging
import sys
import subprocess
import tempfile
import os

logger = logging.getLogger(__name__)

class GitHubUpdater:
    """Gerenciador de atualizações via GitHub."""
    
    def __init__(self, repo: str, base_dir: Path, backup_dir: Optional[Path] = None):
        """
        Args:
            repo: Repositório no formato 'usuario/repo'
            base_dir: Diretório base da aplicação (onde estão os arquivos .py)
            backup_dir: Diretório para backups (opcional, padrão: base_dir/backups)
        """
        self.repo = repo
        self.base_dir = Path(base_dir)
        self.backup_dir = Path(backup_dir) if backup_dir else self.base_dir / "backups"
        self.api_url = f"https://api.github.com/repos/{repo}"
        self.raw_url = f"https://raw.githubusercontent.com/{repo}/main"
        self.releases_url = f"{self.api_url}/releases/latest"
        self.version_file = self.base_dir / "version.txt"
        
    def get_current_version(self) -> str:
        """Retorna a versão atual instalada."""
        if self.version_file.exists():
            return self.version_file.read_text(encoding='utf-8').strip()
        return "0.0.0"
    
    def get_remote_version(self) -> Optional[str]:
        """Busca a versão mais recente no GitHub."""
        try:
            response = requests.get(
                f"{self.raw_url}/version.txt",
                timeout=10
            )
            if response.status_code == 200:
                return response.text.strip()
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar versão remota: {e}")
            return None
    
    def get_latest_release(self) -> Optional[Dict]:
        """Busca informações da última release do GitHub."""
        try:
            response = requests.get(self.releases_url, timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar release: {e}")
            return None
    
    def check_for_updates(self) -> Tuple[bool, str, str]:
        """
        Verifica se há atualizações disponíveis.
        
        Returns:
            (tem_atualizacao, versao_atual, versao_remota)
        """
        current = self.get_current_version()
        remote = self.get_remote_version()
        
        if remote is None:
            return False, current, "Erro ao conectar"
        
        has_update = remote != current
        return has_update, current, remote
    
    def download_installer_from_release(self, progress_callback=None) -> Optional[Path]:
        """
        Baixa o instalador (.exe) da última release do GitHub.
        
        Args:
            progress_callback: Função callback(message: str) para reportar progresso
            
        Returns:
            Path do instalador baixado ou None se falhar
        """
        def log_progress(msg):
            if progress_callback:
                progress_callback(msg)
            logger.info(msg)
        
        try:
            log_progress("🔍 Buscando última release...")
            release = self.get_latest_release()
            
            if not release:
                log_progress("❌ Não foi possível buscar informações da release")
                return None
            
            # Procura asset do instalador
            assets = release.get('assets', [])
            installer_asset = None
            
            for asset in assets:
                name = asset.get('name', '').lower()
                if name.endswith('.exe') and ('setup' in name or 'installer' in name or 'busca_xml' in name):
                    installer_asset = asset
                    break
            
            if not installer_asset:
                log_progress("❌ Instalador não encontrado na release")
                return None
            
            download_url = installer_asset.get('browser_download_url')
            file_size = installer_asset.get('size', 0)
            file_name = installer_asset.get('name', 'installer.exe')
            
            log_progress(f"📥 Baixando instalador...")
            
            # Baixa instalador
            response = requests.get(download_url, stream=True, timeout=60)
            response.raise_for_status()
            
            # Salva em diretório temporário
            temp_dir = Path(tempfile.gettempdir())
            installer_path = temp_dir / file_name
            
            downloaded = 0
            last_percent = -1
            with open(installer_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if file_size > 0:
                            percent = int((downloaded / file_size) * 100)
                            # Atualiza apenas quando a porcentagem muda
                            if percent != last_percent:
                                log_progress(f"📥 Baixando: {percent}%")
                                last_percent = percent
            
            log_progress(f"✅ Download concluído!")
            return installer_path
            
        except Exception as e:
            logger.error(f"Erro ao baixar instalador: {e}")
            log_progress(f"❌ Erro: {str(e)}")
            return None
    
    def download_executable_from_release(self, progress_callback=None) -> Optional[Path]:
        """
        Baixa o executável principal (.exe) da última release do GitHub.
        Busca por "Busca XML.exe" nos assets da release.
        
        Args:
            progress_callback: Função callback(message: str) para reportar progresso
            
        Returns:
            Path do executável baixado ou None se falhar
        """
        def log_progress(msg):
            if progress_callback:
                progress_callback(msg)
            logger.info(msg)
        
        try:
            log_progress("🔍 Buscando última release...")
            release = self.get_latest_release()
            
            if not release:
                log_progress("❌ Não foi possível buscar informações da release")
                return None
            
            # Procura asset do executável principal
            assets = release.get('assets', [])
            exe_asset = None
            
            for asset in assets:
                name = asset.get('name', '')
                # Busca exatamente "Busca XML.exe" (o executável principal, não o instalador)
                if name == 'Busca XML.exe' or (name.endswith('.exe') and 'busca' in name.lower() and 'xml' in name.lower() and 'setup' not in name.lower() and 'install' not in name.lower()):
                    exe_asset = asset
                    break
            
            if not exe_asset:
                log_progress("❌ Executável não encontrado na release")
                log_progress("💡 Certifique-se de que a release contém 'Busca XML.exe'")
                return None
            
            download_url = exe_asset.get('browser_download_url')
            file_size = exe_asset.get('size', 0)
            file_name = exe_asset.get('name', 'Busca XML.exe')
            
            log_progress(f"📥 Baixando executável: {file_name}...")
            
            # Baixa executável
            response = requests.get(download_url, stream=True, timeout=60)
            response.raise_for_status()
            
            # Salva em diretório temporário
            temp_dir = Path(tempfile.gettempdir())
            exe_path = temp_dir / file_name
            
            downloaded = 0
            last_percent = -1
            with open(exe_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if file_size > 0:
                            percent = int((downloaded / file_size) * 100)
                            if percent != last_percent:
                                log_progress(f"📥 Baixando executável: {percent}%")
                                last_percent = percent
            
            log_progress(f"✅ Executável baixado com sucesso!")
            return exe_path
            
        except Exception as e:
            logger.error(f"Erro ao baixar executável: {e}")
            log_progress(f"❌ Erro: {str(e)}")
            return None
    
    def update_executable(self, progress_callback=None) -> Dict[str, any]:
        """
        Atualiza o executável principal usando o updater_launcher.
        Este método baixa o novo exe e inicia o launcher para substituí-lo.
        
        Args:
            progress_callback: Função callback(message: str) para reportar progresso
            
        Returns:
            Dict com resultado: {'success': bool, 'message': str, 'restart_required': bool}
        """
        def log_progress(msg):
            if progress_callback:
                progress_callback(msg)
            logger.info(msg)
        
        try:
            # Verifica se está rodando como executável
            if not getattr(sys, 'frozen', False):
                return {
                    'success': False,
                    'message': 'Atualização de executável só funciona quando compilado com PyInstaller',
                    'restart_required': False
                }
            
            # Verifica se há atualizações
            has_update, current, remote = self.check_for_updates()
            
            if not has_update:
                return {
                    'success': False,
                    'message': f'Você já está na versão mais recente ({current})',
                    'restart_required': False
                }
            
            log_progress(f"🔄 Atualizando de {current} para {remote}...")
            
            # Baixa novo executável
            log_progress("📥 Baixando nova versão...")
            novo_exe = self.download_executable_from_release(progress_callback)
            
            if not novo_exe or not novo_exe.exists():
                return {
                    'success': False,
                    'message': 'Falha ao baixar o executável atualizado',
                    'restart_required': False
                }
            
            # Localiza o executável atual
            exe_atual = Path(sys.executable)
            log_progress(f"📍 Executável atual: {exe_atual}")
            
            # Localiza o updater launcher
            # Quando compilado com PyInstaller, arquivos de dados ficam em _internal ou no mesmo diretório
            if hasattr(sys, '_MEIPASS'):
                # Modo executável
                launcher_locations = [
                    Path(sys._MEIPASS) / 'updater_launcher.py',
                    exe_atual.parent / '_internal' / 'updater_launcher.py',
                    exe_atual.parent / 'updater_launcher.py',
                ]
            else:
                # Modo desenvolvimento
                launcher_locations = [self.base_dir / 'updater_launcher.py']
            
            launcher_script = None
            for loc in launcher_locations:
                if loc.exists():
                    launcher_script = loc
                    break
            
            if not launcher_script:
                log_progress("⚠️ updater_launcher.py não encontrado")
                log_progress("💡 Tentando copiar launcher para temp...")
                
                # Cria launcher temporário
                temp_launcher = Path(tempfile.gettempdir()) / 'updater_launcher.py'
                
                # Código do launcher embutido (fallback)
                launcher_code = Path(__file__).parent.parent / 'updater_launcher.py'
                if launcher_code.exists():
                    shutil.copy2(launcher_code, temp_launcher)
                    launcher_script = temp_launcher
                else:
                    return {
                        'success': False,
                        'message': 'updater_launcher.py não encontrado no pacote',
                        'restart_required': False
                    }
            
            log_progress("🚀 Preparando para atualizar...")
            
            # Executa o updater launcher
            # Ele aguardará o app fechar, substituirá o exe e reiniciará
            try:
                # Usa pythonw.exe se disponível (não mostra console)
                python_exe = sys.executable
                if 'python.exe' in python_exe.lower():
                    pythonw = python_exe.replace('python.exe', 'pythonw.exe')
                    if Path(pythonw).exists():
                        python_exe = pythonw
                
                # Inicia o launcher em background
                subprocess.Popen(
                    [python_exe, str(launcher_script), str(novo_exe), str(exe_atual)],
                    cwd=str(launcher_script.parent),
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                    close_fds=True
                )
                
                log_progress("✅ Updater iniciado!")
                
                return {
                    'success': True,
                    'message': f'✅ Atualização iniciada!\n\nO aplicativo será fechado e atualizado automaticamente.\n\nVersão: {current} → {remote}',
                    'restart_required': True
                }
                
            except Exception as e:
                logger.error(f"Erro ao iniciar updater launcher: {e}")
                return {
                    'success': False,
                    'message': f'Erro ao iniciar processo de atualização: {str(e)}',
                    'restart_required': False
                }
                
        except Exception as e:
            logger.error(f"Erro ao atualizar executável: {e}")
            return {
                'success': False,
                'message': f'Erro durante atualização: {str(e)}',
                'restart_required': False
            }
    
    def get_file_list(self) -> List[str]:
        """
        Retorna lista de arquivos Python para atualizar.
        Busca dinamicamente TODOS os arquivos .py do repositório via GitHub API.
        """
        try:
            # Busca árvore completa do repositório
            tree_url = f"{self.api_url}/git/trees/main?recursive=1"
            response = requests.get(tree_url, timeout=30)
            
            if response.status_code != 200:
                logger.warning("Falha ao buscar lista de arquivos via API, usando lista fixa")
                return self._get_fallback_file_list()
            
            tree = response.json()
            files_to_update = []
            
            # Filtra apenas arquivos .py (não .pyc)
            for item in tree.get('tree', []):
                path = item.get('path', '')
                item_type = item.get('type', '')
                
                # Inclui apenas arquivos .py (não pastas)
                if item_type == 'blob' and path.endswith('.py') and not path.endswith('.pyc'):
                    # Exclui alguns arquivos específicos que não devem ser atualizados
                    exclude_patterns = [
                        '__pycache__',
                        '.venv',
                        'venv',
                        'build/',
                        'dist/',
                        '.git/',
                        'test_',  # Arquivos de teste locais
                        'debug_',  # Scripts de debug locais
                    ]
                    
                    # Verifica se o arquivo deve ser excluído
                    should_exclude = any(pattern in path for pattern in exclude_patterns)
                    
                    if not should_exclude:
                        files_to_update.append(path)
            
            logger.info(f"📋 Encontrados {len(files_to_update)} arquivos Python para atualizar")
            return files_to_update if files_to_update else self._get_fallback_file_list()
            
        except Exception as e:
            logger.error(f"Erro ao buscar lista de arquivos: {e}")
            return self._get_fallback_file_list()
    
    def _get_fallback_file_list(self) -> List[str]:
        """Lista fixa de arquivos como fallback se a API falhar."""
        files_to_update = [
            "nfe_search.py",
            "interface_pyqt5.py",
            "modules/__init__.py",
            "modules/database.py",
            "modules/cte_service.py",
            "modules/updater.py",
            "modules/sandbox_worker.py",
            "modules/sandbox_task.py",
            "modules/sandbox_task_runner.py",
            "modules/certificate_manager.py",
            "modules/certificate_dialog.py",
            "modules/sefaz_integration.py",
            "modules/sefaz_config_dialog.py",
            "modules/pdf_generator.py",
            "modules/pdf_simple.py",
            "modules/pdf_cli_worker.py",
            "modules/qt_components.py",
            "modules/ui_components.py",
            "modules/utils.py",
            "modules/monitor.py",
            "modules/deps_checker.py",
            "modules/download_completo.py",
            "modules/_temp_runner.py",
        ]
        return files_to_update
    
    def download_file(self, remote_path: str) -> Optional[bytes]:
        """
        Baixa um arquivo do GitHub.
        
        Args:
            remote_path: Caminho relativo no repositório (ex: 'modules/database.py')
            
        Returns:
            Conteúdo do arquivo em bytes ou None se falhar
        """
        try:
            url = f"{self.raw_url}/{remote_path}"
            logger.info(f"Baixando: {url}")
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                return response.content
            else:
                logger.warning(f"Arquivo não encontrado: {remote_path} (status {response.status_code})")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao baixar {remote_path}: {e}")
            return None
    
    def backup_file(self, file_path: Path) -> bool:
        """Cria backup de um arquivo antes de sobrescrever."""
        if not file_path.exists():
            return True
            
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = self.backup_dir / f"{file_path.name}.bak"
            shutil.copy2(file_path, backup_path)
            logger.info(f"Backup criado: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Erro ao criar backup de {file_path}: {e}")
            return False
    
    def apply_update(self, progress_callback=None) -> Dict[str, any]:
        """
        Aplica atualização baixando e substituindo arquivos.
        Prioriza instalador do GitHub Releases, depois atualiza arquivos individuais.
        
        Args:
            progress_callback: Função callback(message: str) para reportar progresso
            
        Returns:
            Dict com resultado: {'success': bool, 'message': str, 'updated_files': list}
        """
        updated_files = []
        errors = []
        
        def log_progress(msg):
            if progress_callback:
                progress_callback(msg)
            logger.info(msg)
        
        try:
            # Verifica se há atualizações
            has_update, current, remote = self.check_for_updates()
            
            if not has_update:
                return {
                    'success': False,
                    'message': f'Você já está na versão mais recente ({current})',
                    'updated_files': []
                }
            
            log_progress(f"📥 Atualizando de {current} para {remote}...")
            
            # MÉTODO 1: Tenta baixar e executar instalador (melhor opção)
            if getattr(sys, 'frozen', False):
                # Aplicativo compilado - pode usar instalador
                log_progress("📦 Tentando baixar instalador...")
                installer_path = self.download_installer_from_release(progress_callback)
                
                if installer_path and installer_path.exists():
                    log_progress("🚀 Executando instalador...")
                    
                    try:
                        # Tenta instalação silenciosa
                        subprocess.Popen([str(installer_path), '/VERYSILENT', '/NORESTART'])
                        
                        return {
                            'success': True,
                            'message': '✅ Instalador executado com sucesso!\n\nO aplicativo será atualizado automaticamente.\nAguarde alguns segundos e reinicie.',
                            'updated_files': ['Instalador automático executado']
                        }
                        
                    except Exception as e:
                        logger.warning(f"Falha instalação silenciosa: {e}")
                        
                        # Tenta execução normal
                        try:
                            subprocess.Popen([str(installer_path)])
                            return {
                                'success': True,
                                'message': '✅ Instalador iniciado!\n\nSiga as instruções na tela para atualizar.',
                                'updated_files': ['Instalador manual iniciado']
                            }
                        except:
                            log_progress(f"⚠️ Execute manualmente: {installer_path}")
            
            # MÉTODO 2: Atualiza arquivos individuais (fallback ou modo desenvolvimento)
            log_progress("📥 Preparando atualização...")
            
            files = self.get_file_list()
            total = len(files)
            
            for idx, file_path in enumerate(files, 1):
                percent = int((idx / total) * 100)
                log_progress(f"📥 Atualizando: {percent}%")
                
                # Baixa arquivo
                content = self.download_file(file_path)
                
                if content is None:
                    errors.append(f"Falha ao baixar: {file_path}")
                    continue
                
                # Prepara caminho local
                local_path = self.base_dir / file_path
                local_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Faz backup se arquivo existir
                if local_path.exists():
                    if not self.backup_file(local_path):
                        errors.append(f"Falha no backup: {file_path}")
                        continue
                
                # Escreve novo arquivo
                try:
                    local_path.write_bytes(content)
                    updated_files.append(file_path)
                    log_progress(f"✅ Atualizado: {file_path}")
                except Exception as e:
                    errors.append(f"Erro ao escrever {file_path}: {e}")
            
            # Baixa e atualiza version.txt
            version_content = self.download_file("version.txt")
            if version_content:
                self.version_file.write_bytes(version_content)
                updated_files.append("version.txt")
                log_progress(f"✅ Versão atualizada para {remote}")
            
            # Resultado final
            if errors:
                error_msg = "\n".join(errors[:5])  # Limita a 5 erros
                if len(errors) > 5:
                    error_msg += f"\n... e mais {len(errors)-5} erros"
                return {
                    'success': False,
                    'message': f'Atualização parcial. Erros:\n{error_msg}',
                    'updated_files': updated_files
                }
            else:
                return {
                    'success': True,
                    'message': f'✅ Atualização concluída!\n\n{len(updated_files)} arquivos atualizados para versão {remote}\n\nReinicie o aplicativo para aplicar as mudanças.',
                    'updated_files': updated_files
                }
                
        except Exception as e:
            logger.error(f"Erro na atualização: {e}")
            return {
                'success': False,
                'message': f'Erro na atualização: {str(e)}',
                'updated_files': updated_files
            }
    
    def get_changelog(self) -> Optional[str]:
        """Busca changelog do GitHub (se existir)."""
        try:
            response = requests.get(f"{self.raw_url}/CHANGELOG.md", timeout=10)
            if response.status_code == 200:
                return response.text
            return None
        except:
            return None
