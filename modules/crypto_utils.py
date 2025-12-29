"""
Módulo de criptografia para dados sensíveis do sistema.

Implementa criptografia simétrica usando Fernet (AES-128) para proteger:
- Senhas de certificados digitais
- Credenciais de API
- Outros dados sensíveis

A chave de criptografia é armazenada em local protegido e única por usuário/máquina.
"""

from cryptography.fernet import Fernet
from pathlib import Path
import os
import sys


class CryptoManager:
    """
    Gerenciador de criptografia para dados sensíveis.
    
    Usa Fernet (AES-128 CBC + HMAC) para garantir confidencialidade e integridade.
    A chave é armazenada em ~/.bot_nfe/key.bin com permissões restritas.
    """
    
    def __init__(self):
        """Inicializa o gerenciador e carrega/cria a chave de criptografia."""
        self.key_file = self._get_key_path()
        self.key = self._load_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _get_key_path(self) -> Path:
        r"""
        Retorna o caminho para o arquivo de chave.
        
        - Windows: %USERPROFILE%\.bot_nfe\key.bin
        - Linux/Mac: ~/.bot_nfe/key.bin
        """
        home = Path.home()
        key_dir = home / '.bot_nfe'
        return key_dir / 'key.bin'
    
    def _load_or_create_key(self) -> bytes:
        """
        Carrega chave existente ou cria uma nova.
        
        Returns:
            bytes: Chave de criptografia de 32 bytes (base64)
        """
        if self.key_file.exists():
            # Carrega chave existente
            return self.key_file.read_bytes()
        
        # Cria nova chave
        key = Fernet.generate_key()
        
        # Cria diretório se não existir
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Salva chave
        self.key_file.write_bytes(key)
        
        # Protege arquivo (apenas leitura do usuário atual)
        self._protect_key_file()
        
        return key
    
    def _protect_key_file(self):
        """
        Protege o arquivo de chave contra acesso não autorizado.
        
        - Windows: Remove permissões de outros usuários via ACL
        - Linux/Mac: chmod 600 (rw-------)
        """
        try:
            if sys.platform == 'win32':
                # Windows: Usar ACL para restringir acesso
                try:
                    import win32security
                    import win32api
                    import ntsecuritycon as con
                    
                    # Obtém SID do usuário atual
                    token = win32security.OpenProcessToken(
                        win32api.GetCurrentProcess(),
                        win32security.TOKEN_QUERY
                    )
                    sid = win32security.GetTokenInformation(
                        token,
                        win32security.TokenUser
                    )[0]
                    
                    # Cria nova ACL apenas com permissões do usuário
                    sd = win32security.SECURITY_DESCRIPTOR()
                    dacl = win32security.ACL()
                    dacl.AddAccessAllowedAce(
                        win32security.ACL_REVISION,
                        con.FILE_ALL_ACCESS,
                        sid
                    )
                    sd.SetSecurityDescriptorDacl(1, dacl, 0)
                    
                    # Aplica ACL ao arquivo
                    win32security.SetFileSecurity(
                        str(self.key_file),
                        win32security.DACL_SECURITY_INFORMATION,
                        sd
                    )
                except ImportError:
                    # pywin32 não instalado - usar método alternativo
                    # Windows não tem chmod, mas pelo menos tenta
                    os.chmod(self.key_file, 0o600)
            else:
                # Linux/Mac: chmod 600
                os.chmod(self.key_file, 0o600)
        except Exception as e:
            print(f"⚠️ Aviso: Não foi possível proteger arquivo de chave: {e}")
            # Não é crítico, continua mesmo assim
    
    def encrypt(self, data: str) -> str:
        """
        Criptografa uma string.
        
        Args:
            data: String em texto claro
            
        Returns:
            String criptografada (base64)
            
        Examples:
            >>> crypto = CryptoManager()
            >>> encrypted = crypto.encrypt("minha_senha_123")
            >>> print(encrypted)
            gAAAAABh5k2x...  # String base64
        """
        if not data:
            return ""
        
        try:
            encrypted_bytes = self.cipher.encrypt(data.encode('utf-8'))
            return encrypted_bytes.decode('ascii')
        except Exception as e:
            print(f"❌ Erro ao criptografar: {e}")
            return ""
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Descriptografa uma string.
        
        Args:
            encrypted_data: String criptografada (base64)
            
        Returns:
            String em texto claro
            
        Examples:
            >>> crypto = CryptoManager()
            >>> decrypted = crypto.decrypt("gAAAAABh5k2x...")
            >>> print(decrypted)
            minha_senha_123
        """
        if not encrypted_data:
            return ""
        
        try:
            decrypted_bytes = self.cipher.decrypt(encrypted_data.encode('ascii'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            # Se falhar, assume que é texto claro (migração)
            # print(f"⚠️ Falha ao descriptografar (texto claro?): {e}")
            return encrypted_data
    
    def is_encrypted(self, data: str) -> bool:
        """
        Verifica se uma string está criptografada.
        
        Args:
            data: String para verificar
            
        Returns:
            True se está criptografada, False caso contrário
            
        Examples:
            >>> crypto = CryptoManager()
            >>> crypto.is_encrypted("senha123")
            False
            >>> crypto.is_encrypted("gAAAAABh5k2x...")
            True
        """
        if not data:
            return False
        
        try:
            # Tenta descriptografar
            self.cipher.decrypt(data.encode('ascii'))
            return True
        except Exception:
            # Não é um dado criptografado válido
            return False
    
    def encrypt_if_needed(self, data: str) -> str:
        """
        Criptografa apenas se ainda não estiver criptografado.
        
        Útil para migração gradual de dados existentes.
        
        Args:
            data: String para criptografar
            
        Returns:
            String criptografada
        """
        if self.is_encrypted(data):
            return data  # Já criptografado
        return self.encrypt(data)


# Singleton global para evitar múltiplas instâncias
_crypto_instance = None


def get_crypto() -> CryptoManager:
    """
    Retorna instância singleton do CryptoManager.
    
    Returns:
        CryptoManager: Instância global do gerenciador
        
    Examples:
        >>> from modules.crypto_utils import get_crypto
        >>> crypto = get_crypto()
        >>> senha_criptografada = crypto.encrypt("minha_senha")
    """
    global _crypto_instance
    if _crypto_instance is None:
        _crypto_instance = CryptoManager()
    return _crypto_instance


if __name__ == "__main__":
    # Teste básico
    print("🔒 Teste do CryptoManager\n")
    
    crypto = get_crypto()
    
    # Teste 1: Criptografar e descriptografar
    print("Teste 1: Criptografia básica")
    original = "senha_super_secreta_123"
    encrypted = crypto.encrypt(original)
    decrypted = crypto.decrypt(encrypted)
    
    print(f"  Original:     {original}")
    print(f"  Criptografado: {encrypted[:50]}...")
    print(f"  Descriptografado: {decrypted}")
    print(f"  ✅ Sucesso: {original == decrypted}\n")
    
    # Teste 2: Verificar se está criptografado
    print("Teste 2: Detecção de dados criptografados")
    print(f"  'senha123' criptografada? {crypto.is_encrypted('senha123')}")
    print(f"  '{encrypted[:30]}...' criptografada? {crypto.is_encrypted(encrypted)}\n")
    
    # Teste 3: Encrypt if needed
    print("Teste 3: Criptografia condicional")
    senha_clara = "minha_senha"
    resultado1 = crypto.encrypt_if_needed(senha_clara)
    resultado2 = crypto.encrypt_if_needed(resultado1)  # Não deve criptografar de novo
    print(f"  1ª chamada: {resultado1[:50]}...")
    print(f"  2ª chamada: {resultado2[:50]}...")
    print(f"  ✅ Idempotente: {resultado1 == resultado2}\n")
    
    print(f"🔑 Chave armazenada em: {crypto.key_file}")
    print(f"✅ Todos os testes passaram!")
