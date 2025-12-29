"""
Sistema de criptografia portável para distribuição em executáveis.

PROBLEMA:
- Chave de criptografia fica em %USERPROFILE%\.bot_nfe\key.bin
- Cada PC tem chave diferente
- Senhas criptografadas no PC A não funcionam no PC B

SOLUÇÃO IMPLEMENTADA:
- Chave mestre embutida no executável (ofuscada)
- Mesma chave em todos os PCs
- Senhas funcionam em qualquer instalação
"""

from cryptography.fernet import Fernet
from pathlib import Path
import base64
import os
import sys


# ============================================================================
# CHAVE MESTRE PARA DISTRIBUIÇÃO
# ============================================================================
# ATENÇÃO: Em produção, use ofuscação mais forte ou variável de ambiente
# Esta chave permite que o mesmo banco funcione em qualquer PC
_MASTER_KEY_B64 = "UG9ydGFibGVLZXlfQk9UX0J1c2NhX05GRV8yMDI1X1NFQ1JFVA=="  # Base64 ofuscado


def _get_master_key() -> bytes:
    """
    Retorna chave mestre para distribuição portável.
    
    Esta função pode ser modificada para usar diferentes estratégias:
    - Variável de ambiente
    - Chave derivada de hardware (menos portável)
    - Chave em arquivo config externo
    - Chave ofuscada no código
    """
    # Decodifica chave base64
    key_str = base64.b64decode(_MASTER_KEY_B64).decode('utf-8')
    
    # Gera chave Fernet (32 bytes) a partir da string
    # IMPORTANTE: Mesmo input sempre gera mesma chave
    import hashlib
    key_bytes = hashlib.sha256(key_str.encode()).digest()
    return base64.urlsafe_b64encode(key_bytes)


class PortableCryptoManager:
    """
    Gerenciador de criptografia portável para executáveis.
    
    Diferença da CryptoManager original:
    - Usa chave MESTRE fixa (mesma em todos PCs)
    - Não depende de arquivo key.bin no %USERPROFILE%
    - Banco de dados funciona em qualquer PC
    
    Desvantagem:
    - Se o código-fonte for exposto, a chave também será
    - Solução: Ofuscar código com PyArmor antes de distribuir
    """
    
    def __init__(self):
        """Inicializa com chave mestre."""
        self.key = _get_master_key()
        self.cipher = Fernet(self.key)
    
    def encrypt(self, data: str) -> str:
        """
        Criptografa string.
        
        Args:
            data: String em texto claro
            
        Returns:
            String criptografada (base64)
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
        Descriptografa string.
        
        Args:
            encrypted_data: String criptografada (base64)
            
        Returns:
            String em texto claro
        """
        if not encrypted_data:
            return ""
        
        try:
            decrypted_bytes = self.cipher.decrypt(encrypted_data.encode('ascii'))
            return decrypted_bytes.decode('utf-8')
        except Exception:
            # Se falhar, assume texto claro (migração)
            return encrypted_data
    
    def is_encrypted(self, data: str) -> bool:
        """Verifica se string está criptografada."""
        if not data:
            return False
        
        try:
            self.cipher.decrypt(data.encode('ascii'))
            return True
        except Exception:
            return False
    
    def encrypt_if_needed(self, data: str) -> str:
        """Criptografa apenas se ainda não estiver."""
        if self.is_encrypted(data):
            return data
        return self.encrypt(data)


# Singleton global
_portable_crypto_instance = None


def get_portable_crypto() -> PortableCryptoManager:
    """
    Retorna instância singleton do PortableCryptoManager.
    
    Use esta função em vez de get_crypto() quando:
    - Distribuir como executável
    - Quiser que banco funcione em múltiplos PCs
    - Precisar de portabilidade total
    
    Returns:
        PortableCryptoManager: Instância global
    """
    global _portable_crypto_instance
    if _portable_crypto_instance is None:
        _portable_crypto_instance = PortableCryptoManager()
    return _portable_crypto_instance


# ============================================================================
# MIGRAÇÃO: Converte chave local para chave mestre
# ============================================================================

def migrate_to_portable_crypto(db_path: Path):
    """
    Migra senhas criptografadas com chave local para chave mestre.
    
    Execute este script ANTES de gerar o executável.
    
    Args:
        db_path: Caminho do banco de dados
    """
    import sqlite3
    from .crypto_utils import get_crypto  # Chave local antiga
    
    crypto_local = get_crypto()  # Chave antiga (%USERPROFILE%)
    crypto_portable = get_portable_crypto()  # Chave nova (mestre)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("  MIGRAÇÃO: Chave Local → Chave Portável (Mestre)")
    print("="*70 + "\n")
    
    cursor.execute("SELECT id, informante, senha FROM certificados")
    certificados = cursor.fetchall()
    
    migrados = 0
    
    for cert_id, informante, senha_criptografada_local in certificados:
        if not senha_criptografada_local:
            continue
        
        try:
            # 1. Descriptografa com chave LOCAL
            senha_clara = crypto_local.decrypt(senha_criptografada_local)
            
            # 2. Re-criptografa com chave MESTRE
            senha_criptografada_master = crypto_portable.encrypt(senha_clara)
            
            # 3. Atualiza no banco
            cursor.execute(
                "UPDATE certificados SET senha = ? WHERE id = ?",
                (senha_criptografada_master, cert_id)
            )
            
            print(f"✅ ID {cert_id:3d} | {informante:20s} | Migrado para chave mestre")
            migrados += 1
        
        except Exception as e:
            print(f"❌ ID {cert_id:3d} | {informante:20s} | ERRO: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*70}")
    print(f"  ✅ {migrados} senhas migradas para chave mestre")
    print(f"  Agora o banco pode ser usado em qualquer PC!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    # Teste
    print("🔒 Teste do PortableCryptoManager\n")
    
    crypto = get_portable_crypto()
    
    # Teste de criptografia
    original = "senha_teste_123"
    encrypted = crypto.encrypt(original)
    decrypted = crypto.decrypt(encrypted)
    
    print(f"Original:       {original}")
    print(f"Criptografado:  {encrypted[:50]}...")
    print(f"Descriptografado: {decrypted}")
    print(f"✅ Match: {original == decrypted}\n")
    
    # Teste de portabilidade
    print("📦 Teste de Portabilidade:")
    print(f"   Chave usada: {crypto.key[:20].decode()}...")
    print(f"   ✅ Mesma chave será usada em TODOS os PCs")
    print(f"   ✅ Banco de dados é totalmente portável\n")
