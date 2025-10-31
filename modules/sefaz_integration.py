# modules/sefaz_integration.py
"""
Integração entre o Sistema de Certificados e SEFAZ
Adaptador que conecta o novo sistema de gestão de certificados com as consultas SEFAZ
"""

import logging
import sqlite3
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from .certificate_manager import CertificateManager

logger = logging.getLogger(__name__)

class SefazCertificateAdapter:
    """
    Adaptador que integra o sistema moderno de certificados com o sistema de busca SEFAZ
    """
    
    def __init__(self, db_path: str = "nfe_data.db"):
        self.db_path = db_path
        self.cert_manager = CertificateManager()
        self._ensure_database()
    
    def _ensure_database(self):
        """Garante que as tabelas necessárias existem"""
        with sqlite3.connect(self.db_path) as conn:
            # Atualiza/cria tabela de certificados com novos campos
            conn.execute('''
                CREATE TABLE IF NOT EXISTS certificados_sefaz (
                    id INTEGER PRIMARY KEY,
                    cnpj_cpf TEXT UNIQUE,
                    caminho TEXT,
                    senha TEXT,
                    informante TEXT,
                    cUF_autor TEXT,
                    ativo BOOLEAN DEFAULT 1,
                    nome_certificado TEXT,
                    data_validade TEXT,
                    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Migra dados da tabela antiga se existir
            self._migrate_old_certificates(conn)
            conn.commit()
    
    def _migrate_old_certificates(self, conn):
        """Migra certificados da tabela antiga para a nova"""
        try:
            # Verifica se tabela antiga existe
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='certificados'"
            )
            if cursor.fetchone():
                # Copia dados da tabela antiga
                conn.execute('''
                    INSERT OR IGNORE INTO certificados_sefaz 
                    (cnpj_cpf, caminho, senha, informante, cUF_autor)
                    SELECT cnpj_cpf, caminho, senha, informante, cUF_autor 
                    FROM certificados
                ''')
                logger.info("Certificados migrados da tabela antiga")
        except sqlite3.Error as e:
            logger.warning(f"Erro na migração de certificados: {e}")
    
    def sync_certificates_from_manager(self) -> int:
        """
        Sincroniza certificados do CertificateManager com a base SEFAZ
        Retorna o número de certificados sincronizados
        """
        certificates = self.cert_manager.get_certificates()
        synced_count = 0
        
        with sqlite3.connect(self.db_path) as conn:
            for cert_data in certificates:
                if not cert_data.get('enabled', True):
                    continue
                
                file_path = cert_data['file_path']
                password = cert_data.get('password', '')
                
                # Obter informações detalhadas do certificado
                cert_info = self.cert_manager.get_certificate_details(file_path, password)
                if not cert_info:
                    logger.warning(f"Não foi possível obter detalhes do certificado: {file_path}")
                    continue
                
                # Determinar CNPJ/CPF e informante
                cnpj_cpf = cert_info.cnpj or cert_info.cpf
                if not cnpj_cpf:
                    logger.warning(f"Certificado sem CNPJ/CPF válido: {file_path}")
                    continue
                
                # Determinar UF (padrão Rio Grande do Sul - 43)
                cuf_autor = "43"  # Pode ser configurado posteriormente
                
                try:
                    conn.execute('''
                        INSERT OR REPLACE INTO certificados_sefaz 
                        (cnpj_cpf, caminho, senha, informante, cUF_autor, 
                         nome_certificado, data_validade, atualizado_em)
                        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (
                        cnpj_cpf,
                        file_path,
                        password,
                        cnpj_cpf,  # informante = cnpj_cpf
                        cuf_autor,
                        cert_info.subject_name,
                        cert_info.not_valid_after.isoformat()
                    ))
                    synced_count += 1
                    logger.debug(f"Certificado sincronizado: {cnpj_cpf}")
                    
                except sqlite3.Error as e:
                    logger.error(f"Erro ao sincronizar certificado {cnpj_cpf}: {e}")
            
            conn.commit()
        
        logger.info(f"Sincronizados {synced_count} certificados com SEFAZ")
        return synced_count
    
    def get_certificados_for_sefaz(self) -> List[Tuple[str, str, str, str, str]]:
        """
        Retorna certificados no formato esperado pelo sistema SEFAZ
        Retorna: Lista de (cnpj_cpf, caminho, senha, informante, cUF_autor)
        """
        # Primeiro sincroniza
        self.sync_certificates_from_manager()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT cnpj_cpf, caminho, senha, informante, cUF_autor 
                FROM certificados_sefaz 
                WHERE ativo = 1
                ORDER BY atualizado_em DESC
            ''')
            certificates = cursor.fetchall()
            
        logger.debug(f"Carregados {len(certificates)} certificados para SEFAZ")
        return certificates
    
    def get_active_certificates_info(self) -> List[Dict]:
        """
        Retorna informações detalhadas dos certificados ativos
        """
        certificates_info = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT cnpj_cpf, caminho, senha, nome_certificado, data_validade, ativo
                FROM certificados_sefaz 
                ORDER BY atualizado_em DESC
            ''')
            
            for row in cursor.fetchall():
                cnpj_cpf, caminho, senha, nome, validade, ativo = row
                
                # Obter informações atualizadas do certificado
                cert_info = self.cert_manager.get_certificate_details(caminho, senha)
                
                certificates_info.append({
                    'cnpj_cpf': cnpj_cpf,
                    'file_path': caminho,
                    'subject_name': nome or (cert_info.subject_name if cert_info else 'N/A'),
                    'valid_until': validade,
                    'is_active': bool(ativo),
                    'is_valid': cert_info.is_valid if cert_info else False,
                    'days_until_expiry': cert_info.days_until_expiry if cert_info else 0
                })
        
        return certificates_info
    
    def toggle_certificate(self, cnpj_cpf: str, active: bool) -> bool:
        """
        Ativa/desativa um certificado para uso no SEFAZ
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE certificados_sefaz 
                    SET ativo = ?, atualizado_em = CURRENT_TIMESTAMP
                    WHERE cnpj_cpf = ?
                ''', (active, cnpj_cpf))
                conn.commit()
                
            logger.info(f"Certificado {cnpj_cpf} {'ativado' if active else 'desativado'}")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Erro ao alterar status do certificado {cnpj_cpf}: {e}")
            return False
    
    def remove_certificate(self, cnpj_cpf: str) -> bool:
        """
        Remove um certificado da base SEFAZ
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('DELETE FROM certificados_sefaz WHERE cnpj_cpf = ?', (cnpj_cpf,))
                conn.commit()
                
            logger.info(f"Certificado {cnpj_cpf} removido da base SEFAZ")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Erro ao remover certificado {cnpj_cpf}: {e}")
            return False
    
    def configure_certificate_uf(self, cnpj_cpf: str, cuf_autor: str) -> bool:
        """
        Configura a UF de um certificado específico
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE certificados_sefaz 
                    SET cUF_autor = ?, atualizado_em = CURRENT_TIMESTAMP
                    WHERE cnpj_cpf = ?
                ''', (cuf_autor, cnpj_cpf))
                conn.commit()
                
            logger.info(f"UF do certificado {cnpj_cpf} configurada para {cuf_autor}")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Erro ao configurar UF do certificado {cnpj_cpf}: {e}")
            return False


# Funcão utilitária para usar no nfe_search.py
def get_certificados_sefaz() -> List[Tuple[str, str, str, str, str]]:
    """
    Função compatível com o sistema antigo
    Retorna certificados no formato esperado: (cnpj_cpf, caminho, senha, informante, cUF_autor)
    """
    adapter = SefazCertificateAdapter()
    return adapter.get_certificados_for_sefaz()