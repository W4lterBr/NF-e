# modules/certificate_manager.py
"""
Gerenciador de Certificados Digitais para NFe
Suporte para certificados .pfx/.p12 com validação e configuração
"""

import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import json

# Dependências para certificados
try:
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.exceptions import InvalidSignature
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logging.warning("Cryptography não disponível. Instale com: pip install cryptography")

@dataclass
class CertificateInfo:
    """Informações do certificado digital"""
    file_path: str
    subject_name: str
    issuer_name: str
    serial_number: str
    not_valid_before: datetime
    not_valid_after: datetime
    is_valid: bool
    cn: str  # Common Name
    cnpj: str = ""
    cpf: str = ""
    fingerprint: str = ""
    
    @property
    def is_expired(self) -> bool:
        """Verifica se o certificado está expirado"""
        return datetime.now(timezone.utc) > self.not_valid_after
    
    @property
    def days_until_expiry(self) -> int:
        """Dias até expirar"""
        delta = self.not_valid_after - datetime.now(timezone.utc)
        return max(0, delta.days)
    
    @property
    def friendly_name(self) -> str:
        """Nome amigável do certificado"""
        if self.cnpj:
            return f"{self.cn} (CNPJ: {self.cnpj})"
        elif self.cpf:
            return f"{self.cn} (CPF: {self.cpf})"
        return self.cn

class CertificateManager:
    """Gerenciador de certificados digitais"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "certificates.json"
        self.logger = logging.getLogger(__name__)
        
        # Configurações dos certificados
        self.certificates: List[Dict] = []
        self.active_certificate: Optional[str] = None
        self.load_config()
    
    def load_config(self):
        """Carrega configuração dos certificados"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.certificates = config.get('certificates', [])
                    self.active_certificate = config.get('active_certificate')
        except Exception as e:
            self.logger.error(f"Erro ao carregar configuração: {e}")
            self.certificates = []
            self.active_certificate = None
    
    def save_config(self):
        """Salva configuração dos certificados"""
        try:
            config = {
                'certificates': self.certificates,
                'active_certificate': self.active_certificate
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Erro ao salvar configuração: {e}")
    
    def validate_certificate(self, file_path: str, password: str = "") -> Tuple[bool, Optional[CertificateInfo]]:
        """
        Valida um certificado digital
        
        Args:
            file_path: Caminho para o arquivo .pfx/.p12
            password: Senha do certificado
            
        Returns:
            Tuple (is_valid, certificate_info)
        """
        if not CRYPTO_AVAILABLE:
            return False, None
        
        try:
            # Verifica se o arquivo existe
            if not os.path.exists(file_path):
                self.logger.error(f"Arquivo não encontrado: {file_path}")
                return False, None
            
            # Lê o arquivo do certificado
            with open(file_path, 'rb') as f:
                pfx_data = f.read()
            
            # Verifica se o arquivo não está vazio
            if len(pfx_data) == 0:
                self.logger.error(f"Arquivo vazio: {file_path}")
                return False, None
            
            # Carrega o certificado PKCS#12
            try:
                private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                    pfx_data, 
                    password.encode('utf-8') if password else None
                )
            except ValueError as e:
                if "could not deserialize key data" in str(e).lower():
                    self.logger.error(f"Senha incorreta para certificado: {file_path}")
                    return False, None
                elif "invalid" in str(e).lower():
                    self.logger.error(f"Arquivo de certificado inválido: {file_path}")
                    return False, None
                else:
                    self.logger.error(f"Erro ao carregar certificado {file_path}: {e}")
                    return False, None
            except Exception as e:
                self.logger.error(f"Erro inesperado ao carregar certificado {file_path}: {e}")
                return False, None
            
            if not certificate:
                self.logger.error(f"Nenhum certificado encontrado no arquivo: {file_path}")
                return False, None
            
            # Extrai informações do certificado
            subject = certificate.subject
            issuer = certificate.issuer
            
            # Busca CN (Common Name) e outros atributos
            cn = ""
            cnpj = ""
            cpf = ""
            
            for attribute in subject:
                try:
                    if attribute.oid._name == 'commonName':
                        cn = attribute.value
                        # Tenta extrair CNPJ/CPF do CN também
                        import re
                        # Busca por padrões de CNPJ/CPF no CN
                        cnpj_pattern = re.search(r'(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})', cn)
                        cpf_pattern = re.search(r'(\d{3}\.?\d{3}\.?\d{3}-?\d{2})', cn)
                        if cnpj_pattern:
                            cnpj = ''.join(filter(str.isdigit, cnpj_pattern.group(1)))
                        elif cpf_pattern:
                            cpf = ''.join(filter(str.isdigit, cpf_pattern.group(1)))
                    elif attribute.oid._name == 'serialNumber':
                        # Extrai CNPJ/CPF do serialNumber
                        serial = str(attribute.value)
                        # Remove caracteres não numéricos
                        serial_clean = ''.join(filter(str.isdigit, serial))
                        if len(serial_clean) == 14:
                            cnpj = serial_clean
                        elif len(serial_clean) == 11:
                            cpf = serial_clean
                        # Também tenta buscar padrões no serial completo
                        elif not cnpj and not cpf:
                            import re
                            cnpj_match = re.search(r'(\d{14})', serial)
                            cpf_match = re.search(r'(\d{11})', serial)
                            if cnpj_match:
                                cnpj = cnpj_match.group(1)
                            elif cpf_match:
                                cpf = cpf_match.group(1)
                except Exception as e:
                    self.logger.warning(f"Erro ao processar atributo {attribute.oid._name}: {e}")
                    continue
            
            # Se ainda não encontrou CNPJ/CPF, tenta buscar no subject completo
            if not cnpj and not cpf:
                import re
                subject_str = str(subject)
                self.logger.debug(f"Subject completo para análise: {subject_str}")
                
                # Busca por padrões mais flexíveis
                cnpj_patterns = [
                    r'(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})',  # CNPJ formatado
                    r'(\d{14})',  # CNPJ sem formatação
                ]
                cpf_patterns = [
                    r'(\d{3}\.?\d{3}\.?\d{3}-?\d{2})',  # CPF formatado
                    r'(\d{11})',  # CPF sem formatação
                ]
                
                for pattern in cnpj_patterns:
                    match = re.search(pattern, subject_str)
                    if match:
                        potential_cnpj = ''.join(filter(str.isdigit, match.group(1)))
                        if len(potential_cnpj) == 14:
                            cnpj = potential_cnpj
                            break
                
                if not cnpj:
                    for pattern in cpf_patterns:
                        match = re.search(pattern, subject_str)
                        if match:
                            potential_cpf = ''.join(filter(str.isdigit, match.group(1)))
                            if len(potential_cpf) == 11:
                                cpf = potential_cpf
                                break
            
            # Cria fingerprint SHA-256
            try:
                from cryptography.hazmat.primitives import hashes
                fingerprint = certificate.fingerprint(hashes.SHA256()).hex()
            except Exception as e:
                self.logger.warning(f"Erro ao gerar fingerprint: {e}")
                fingerprint = "N/A"
            
            # Monta informações do certificado
            try:
                # Verifica validade considerando timezone
                now_utc = datetime.now(timezone.utc)
                
                # Usar as propriedades UTC para evitar warnings de depreciação
                try:
                    # Tentar usar as novas propriedades UTC (cryptography >= 41.0.0)
                    not_valid_before = certificate.not_valid_before_utc
                    not_valid_after = certificate.not_valid_after_utc
                except AttributeError:
                    # Fallback para versões antigas do cryptography
                    not_valid_before = certificate.not_valid_before
                    not_valid_after = certificate.not_valid_after
                    
                    # Garante que as datas têm timezone se usando propriedades antigas
                    if not_valid_before.tzinfo is None:
                        not_valid_before = not_valid_before.replace(tzinfo=timezone.utc)
                    if not_valid_after.tzinfo is None:
                        not_valid_after = not_valid_after.replace(tzinfo=timezone.utc)
                
                is_valid = now_utc < not_valid_after and now_utc > not_valid_before
                
                cert_info = CertificateInfo(
                    file_path=file_path,
                    subject_name=str(subject),
                    issuer_name=str(issuer),
                    serial_number=str(certificate.serial_number),
                    not_valid_before=not_valid_before,
                    not_valid_after=not_valid_after,
                    is_valid=is_valid,
                    cn=cn or "Nome não encontrado",
                    cnpj=cnpj,
                    cpf=cpf,
                    fingerprint=fingerprint
                )
                
                return True, cert_info
                
            except Exception as e:
                self.logger.error(f"Erro ao montar informações do certificado: {e}")
                return False, None
            
        except Exception as e:
            self.logger.error(f"Erro ao validar certificado {file_path}: {e}")
            return False, None
    
    def add_certificate(self, file_path: str, password: str = "", alias: str = "") -> bool:
        """
        Adiciona um certificado à lista
        
        Args:
            file_path: Caminho para o certificado
            password: Senha do certificado
            alias: Nome amigável (opcional)
            
        Returns:
            True se adicionado com sucesso
        """
        # Valida o certificado
        is_valid, cert_info = self.validate_certificate(file_path, password)
        
        if not is_valid or not cert_info:
            return False
        
        # Verifica se já existe
        for cert in self.certificates:
            if cert['file_path'] == file_path:
                # Atualiza certificado existente
                cert.update({
                    'alias': alias or cert_info.friendly_name,
                    'password': password,  # Em produção, criptografar!
                    'cn': cert_info.cn,
                    'cnpj': cert_info.cnpj,
                    'cpf': cert_info.cpf,
                    'not_valid_after': cert_info.not_valid_after.isoformat(),
                    'is_valid': cert_info.is_valid,
                    'fingerprint': cert_info.fingerprint
                })
                self.save_config()
                return True
        
        # Adiciona novo certificado
        self.certificates.append({
            'file_path': file_path,
            'alias': alias or cert_info.friendly_name,
            'password': password,  # Em produção, criptografar!
            'cn': cert_info.cn,
            'cnpj': cert_info.cnpj,
            'cpf': cert_info.cpf,
            'not_valid_after': cert_info.not_valid_after.isoformat(),
            'is_valid': cert_info.is_valid,
            'fingerprint': cert_info.fingerprint,
            'added_at': datetime.now().isoformat()
        })
        
        # Se é o primeiro certificado, define como ativo
        if len(self.certificates) == 1:
            self.active_certificate = file_path
        
        self.save_config()
        return True
    
    def remove_certificate(self, file_path: str) -> bool:
        """Remove um certificado da lista"""
        original_count = len(self.certificates)
        self.certificates = [c for c in self.certificates if c['file_path'] != file_path]
        
        # Se removeu o certificado ativo, limpa
        if self.active_certificate == file_path:
            self.active_certificate = None
            if self.certificates:
                self.active_certificate = self.certificates[0]['file_path']
        
        if len(self.certificates) < original_count:
            self.save_config()
            return True
        return False
    
    def set_active_certificate(self, file_path: str) -> bool:
        """Define o certificado ativo"""
        for cert in self.certificates:
            if cert['file_path'] == file_path:
                self.active_certificate = file_path
                self.save_config()
                return True
        return False
    
    def get_active_certificate(self) -> Optional[Dict]:
        """Retorna o certificado ativo"""
        if not self.active_certificate:
            return None
        
        for cert in self.certificates:
            if cert['file_path'] == self.active_certificate:
                return cert
        return None
    
    def get_certificates(self) -> List[Dict]:
        """Retorna lista de certificados com status atualizado"""
        updated_certs = []
        
        for cert in self.certificates:
            # Verifica se arquivo ainda existe
            if not os.path.exists(cert['file_path']):
                continue
            
            # Verifica validade atual
            try:
                expiry_date = datetime.fromisoformat(cert['not_valid_after'].replace('Z', '+00:00'))
                is_valid = datetime.now(timezone.utc) < expiry_date
                cert['is_valid'] = is_valid
                cert['days_until_expiry'] = max(0, (expiry_date - datetime.now(timezone.utc)).days)
            except:
                cert['is_valid'] = False
                cert['days_until_expiry'] = 0
            
            updated_certs.append(cert)
        
        return updated_certs
    
    def scan_certificates_directory(self, directory: str) -> List[str]:
        """
        Escaneia um diretório em busca de certificados
        
        Args:
            directory: Diretório para escanear
            
        Returns:
            Lista de caminhos de certificados encontrados
        """
        cert_files = []
        extensions = ['.pfx', '.p12', '.crt', '.cer']
        
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in extensions):
                        cert_files.append(os.path.join(root, file))
        except Exception as e:
            self.logger.error(f"Erro ao escanear diretório {directory}: {e}")
        
        return cert_files
    
    def get_certificate_for_cnpj(self, cnpj: str) -> Optional[Dict]:
        """Retorna certificado específico para um CNPJ"""
        cnpj_clean = ''.join(filter(str.isdigit, cnpj))
        
        for cert in self.get_certificates():
            if cert.get('cnpj') == cnpj_clean and cert.get('is_valid'):
                return cert
        
        return None
    
    def validate_certificate_password(self, file_path: str, password: str) -> bool:
        """Valida apenas a senha de um certificado"""
        is_valid, _ = self.validate_certificate(file_path, password)
        return is_valid
    
    def get_certificate_details(self, file_path: str, password: str = "") -> Optional[CertificateInfo]:
        """Retorna detalhes completos de um certificado"""
        is_valid, cert_info = self.validate_certificate(file_path, password)
        return cert_info if is_valid else None

# Instância global do gerenciador
certificate_manager = CertificateManager()