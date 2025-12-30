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
    
    def get_file_list(self) -> List[str]:
        """
        Retorna lista de arquivos Python para atualizar.
        Busca recursivamente no repositório.
        """
        files_to_update = [
            "nfe_search.py",
            "interface_pyqt5.py",
            "modules/__init__.py",
            "modules/database.py",
            "modules/cte_service.py",
            "modules/updater.py",
            "modules/sandbox_worker.py",
            "modules/sandbox_task.py",
            "modules/sandbox_task_runner.py",  # ADICIONADO - worker isolado para PDFs/SEFAZ
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
