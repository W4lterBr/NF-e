# modules/database.py
"""
Gerenciador de banco de dados para o sistema BOT NFe
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gerenciador do banco de dados SQLite"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Garante que todas as tabelas necessárias existam"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Tabela de certificados
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS certificados (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        cnpj_cpf TEXT NOT NULL,
                        caminho TEXT NOT NULL,
                        senha TEXT NOT NULL,
                        informante TEXT NOT NULL,
                        cUF_autor TEXT NOT NULL,
                        criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                        ativo BOOLEAN DEFAULT 1
                    )
                ''')
                
                # Tabela de notas detalhadas
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS notas_detalhadas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chave TEXT UNIQUE NOT NULL,
                        numero TEXT,
                        data_emissao TEXT,
                        cnpj_emitente TEXT,
                        nome_emitente TEXT,
                        cnpj_destinatario TEXT,
                        nome_destinatario TEXT,
                        valor TEXT,
                        cfop TEXT,
                        tipo TEXT DEFAULT 'NFe',
                        vencimento TEXT,
                        status TEXT DEFAULT 'Pendente',
                        natureza TEXT,
                        ie_tomador TEXT,
                        uf TEXT,
                        -- Campos adicionais para gerenciamento de resumo/completo e origem
                        xml_status TEXT DEFAULT 'RESUMO', -- RESUMO | COMPLETO
                        informante TEXT,                  -- CNPJ do certificado que trouxe o documento
                        nsu TEXT,                         -- NSU do documento (se disponível)
                        atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                        criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Tabela de NSU
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS nsu (
                        informante TEXT PRIMARY KEY,
                        ult_nsu TEXT NOT NULL,
                        atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Tabela de XMLs baixados
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS xmls_baixados (
                        chave TEXT PRIMARY KEY,
                        cnpj_cpf TEXT NOT NULL,
                        caminho_arquivo TEXT,
                        baixado_em DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Tabela de status das NF-e
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS nf_status (
                        chNFe TEXT PRIMARY KEY,
                        cStat TEXT,
                        xMotivo TEXT,
                        atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Índices para melhor performance
                conn.execute('CREATE INDEX IF NOT EXISTS idx_notas_chave ON notas_detalhadas(chave)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_notas_data ON notas_detalhadas(data_emissao)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_notas_cnpj_emit ON notas_detalhadas(cnpj_emitente)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_certificados_informante ON certificados(informante)')
                
                conn.commit()
                logger.info("Estrutura do banco de dados verificada/criada com sucesso")
                
        except Exception as e:
            logger.error(f"Erro ao criar estrutura do banco: {e}")
            raise

        # Migrações leves: adiciona colunas se faltarem
        try:
            with sqlite3.connect(self.db_path) as conn:
                def ensure_col(table: str, col: str, ddl: str):
                    try:
                        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
                        conn.commit()
                        logger.debug(f"Coluna adicionada: {table}.{col}")
                    except sqlite3.OperationalError:
                        # Já existe
                        pass

                ensure_col('notas_detalhadas', 'xml_status', "TEXT DEFAULT 'RESUMO'")
                ensure_col('notas_detalhadas', 'informante', 'TEXT')
                ensure_col('notas_detalhadas', 'nsu', 'TEXT')
                # Garante colunas novas em xmls_baixados (compatibilidade com esquema antigo)
                ensure_col('xmls_baixados', 'caminho_arquivo', 'TEXT')
                ensure_col('xmls_baixados', 'baixado_em', 'DATETIME DEFAULT CURRENT_TIMESTAMP')
        except Exception as e:
            logger.warning(f"Falha ao aplicar migrações leves: {e}")
    
    def load_notes(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Carrega notas do banco de dados
        
        Args:
            limit: Limite de registros a retornar (None para todos)
            
        Returns:
            Lista de dicionários com dados das notas
        """
        notes = []
        seen_keys = set()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row  # Para acessar colunas por nome
                
                query = "SELECT * FROM notas_detalhadas ORDER BY data_emissao DESC"
                if limit:
                    query += f" LIMIT {limit}"
                
                cursor = conn.execute(query)
                
                for row in cursor.fetchall():
                    chave = row['chave']
                    if not chave or chave in seen_keys:
                        continue
                    seen_keys.add(chave)
                    
                    # Converte Row para dict
                    note_dict = dict(row)
                    notes.append(note_dict)
                
                logger.info(f"Carregadas {len(notes)} notas do banco")
                
        except Exception as e:
            logger.error(f"Erro ao carregar notas: {e}")
            raise
        
        return notes
    
    def load_certificates(self) -> List[Dict[str, Any]]:
        """
        Carrega certificados ativos do banco
        
        Returns:
            Lista de dicionários com dados dos certificados
        """
        certificates = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                cursor = conn.execute('''
                    SELECT * FROM certificados 
                    WHERE ativo = 1 
                    ORDER BY criado_em DESC
                ''')
                
                for row in cursor.fetchall():
                    cert_dict = dict(row)
                    certificates.append(cert_dict)
                
                logger.info(f"Carregados {len(certificates)} certificados ativos")
                
        except Exception as e:
            logger.error(f"Erro ao carregar certificados: {e}")
            raise
        
        return certificates
    
    def save_note(self, note_data: Dict[str, Any]) -> bool:
        """
        Salva ou atualiza uma nota no banco
        
        Args:
            note_data: Dicionário com dados da nota
            
        Returns:
            True se salvou com sucesso, False caso contrário
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Verifica se já existe
                existing = conn.execute(
                    "SELECT id FROM notas_detalhadas WHERE chave = ?",
                    (note_data.get('chave'),)
                ).fetchone()
                
                note_data['atualizado_em'] = datetime.now().isoformat()
                
                if existing:
                    # Atualiza registro existente
                    set_clause = ', '.join([f"{k} = ?" for k in note_data.keys() if k != 'chave'])
                    values = [v for k, v in note_data.items() if k != 'chave']
                    values.append(note_data['chave'])
                    
                    conn.execute(
                        f"UPDATE notas_detalhadas SET {set_clause} WHERE chave = ?",
                        values
                    )
                    logger.debug(f"Nota atualizada: {note_data.get('chave')}")
                else:
                    # Insere novo registro
                    note_data['criado_em'] = datetime.now().isoformat()
                    columns = ', '.join(note_data.keys())
                    placeholders = ', '.join(['?' for _ in note_data])
                    
                    conn.execute(
                        f"INSERT INTO notas_detalhadas ({columns}) VALUES ({placeholders})",
                        list(note_data.values())
                    )
                    logger.debug(f"Nova nota inserida: {note_data.get('chave')}")
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Erro ao salvar nota: {e}")
            return False

    def update_xml_status(self, chave: str, status: str) -> bool:
        """
        Atualiza o status do XML (RESUMO/COMPLETO) para a nota informada.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE notas_detalhadas SET xml_status = ?, atualizado_em = ? WHERE chave = ?",
                    (status, datetime.now().isoformat(), chave)
                )
                conn.commit()
                logger.debug(f"xml_status atualizado para {chave}: {status}")
                return True
        except Exception as e:
            logger.error(f"Erro ao atualizar xml_status: {e}")
            return False

    def get_note_by_chave(self, chave: str) -> Optional[Dict[str, Any]]:
        """
        Retorna os dados da nota pela chave.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM notas_detalhadas WHERE chave = ?",
                    (chave,)
                ).fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Erro ao buscar nota por chave: {e}")
            return None
    
    def save_certificate(self, cert_data: Dict[str, Any]) -> bool:
        """
        Salva um novo certificado no banco
        
        Args:
            cert_data: Dicionário com dados do certificado
            
        Returns:
            True se salvou com sucesso, False se já existe ou erro
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Verifica se já existe certificado para este informante
                existing = conn.execute(
                    "SELECT id FROM certificados WHERE informante = ? AND ativo = 1",
                    (cert_data.get('informante'),)
                ).fetchone()
                
                if existing:
                    logger.warning(f"Certificado já existe para informante: {cert_data.get('informante')}")
                    return False
                
                # Insere novo certificado
                cert_data['criado_em'] = datetime.now().isoformat()
                cert_data['ativo'] = 1
                
                columns = ', '.join(cert_data.keys())
                placeholders = ', '.join(['?' for _ in cert_data])
                
                conn.execute(
                    f"INSERT INTO certificados ({columns}) VALUES ({placeholders})",
                    list(cert_data.values())
                )
                
                conn.commit()
                logger.info(f"Certificado salvo: {cert_data.get('informante')}")
                return True
                
        except Exception as e:
            logger.error(f"Erro ao salvar certificado: {e}")
            return False
    
    def get_last_nsu(self, informante: str) -> str:
        """
        Obtém o último NSU para um informante
        
        Args:
            informante: CNPJ/CPF do informante
            
        Returns:
            Último NSU ou '000000000000000' se não encontrado
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute(
                    "SELECT ult_nsu FROM nsu WHERE informante = ?",
                    (informante,)
                ).fetchone()
                
                return result[0] if result else "000000000000000"
                
        except Exception as e:
            logger.error(f"Erro ao obter último NSU: {e}")
            return "000000000000000"
    
    def set_last_nsu(self, informante: str, nsu: str) -> bool:
        """
        Define o último NSU para um informante
        
        Args:
            informante: CNPJ/CPF do informante
            nsu: Valor do NSU
            
        Returns:
            True se salvou com sucesso
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    '''INSERT OR REPLACE INTO nsu (informante, ult_nsu, atualizado_em) 
                       VALUES (?, ?, ?)''',
                    (informante, nsu, datetime.now().isoformat())
                )
                conn.commit()
                logger.debug(f"NSU atualizado para {informante}: {nsu}")
                return True
                
        except Exception as e:
            logger.error(f"Erro ao definir último NSU: {e}")
            return False
    
    def get_nf_status(self, chave: str) -> Optional[Tuple[str, str]]:
        """
        Obtém status de uma NF-e
        
        Args:
            chave: Chave da NF-e
            
        Returns:
            Tupla (cStat, xMotivo) ou None se não encontrado
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute(
                    "SELECT cStat, xMotivo FROM nf_status WHERE chNFe = ?",
                    (chave,)
                ).fetchone()
                
                return result if result else None
                
        except Exception as e:
            logger.error(f"Erro ao obter status da NF-e: {e}")
            return None
    
    def set_nf_status(self, chave: str, cstat: str, xmotivo: str) -> bool:
        """
        Define status de uma NF-e
        
        Args:
            chave: Chave da NF-e
            cstat: Código de status
            xmotivo: Motivo/descrição
            
        Returns:
            True se salvou com sucesso
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    '''INSERT OR REPLACE INTO nf_status (chNFe, cStat, xMotivo, atualizado_em) 
                       VALUES (?, ?, ?, ?)''',
                    (chave, cstat, xmotivo, datetime.now().isoformat())
                )
                conn.commit()
                logger.debug(f"Status atualizado para {chave}: {cstat}")
                return True
                
        except Exception as e:
            logger.error(f"Erro ao definir status da NF-e: {e}")
            return False
    
    def register_xml_download(self, chave: str, cnpj: str, arquivo_path: Optional[str] = None) -> bool:
        """
        Registra download de XML com detecção dinâmica das colunas disponíveis,
        para compatibilidade com bancos antigos sem colunas novas.

        Args:
            chave: Chave da NF-e
            cnpj: CNPJ/CPF relacionado
            arquivo_path: Caminho do arquivo salvo

        Returns:
            True se registrou com sucesso
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Descobre colunas existentes na tabela
                cols = {row[1] for row in conn.execute("PRAGMA table_info(xmls_baixados)")}

                fields = ["chave", "cnpj_cpf"]
                values = [chave, cnpj]
                if "caminho_arquivo" in cols:
                    fields.append("caminho_arquivo")
                    values.append(arquivo_path)
                if "baixado_em" in cols:
                    fields.append("baixado_em")
                    values.append(datetime.now().isoformat())

                placeholders = ", ".join(["?"] * len(fields))
                sql = f"INSERT OR REPLACE INTO xmls_baixados ({', '.join(fields)}) VALUES ({placeholders})"
                conn.execute(sql, values)
                conn.commit()
                logger.debug(f"Download registrado: {chave}")
                return True

        except Exception as e:
            logger.error(f"Erro ao registrar download: {e}")
            return False
    
    def get_missing_status_keys(self) -> List[Tuple[str, str]]:
        """
        Obtém chaves que ainda não têm status consultado
        
        Returns:
            Lista de tuplas (chave, cnpj_cpf)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT x.chave, x.cnpj_cpf
                    FROM xmls_baixados x
                    LEFT JOIN nf_status n ON x.chave = n.chNFe
                    WHERE n.chNFe IS NULL
                ''')
                
                return cursor.fetchall()
                
        except Exception as e:
            logger.error(f"Erro ao obter chaves sem status: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Obtém estatísticas do banco de dados
        
        Returns:
            Dicionário com estatísticas
        """
        stats = {
            'total_notas': 0,
            'notas_autorizadas': 0,
            'notas_canceladas': 0,
            'notas_rejeitadas': 0,
            'certificados_ativos': 0,
            'ultimo_update': None
        }
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total de notas
                result = conn.execute("SELECT COUNT(*) FROM notas_detalhadas").fetchone()
                stats['total_notas'] = result[0] if result else 0
                
                # Notas por status
                result = conn.execute(
                    "SELECT COUNT(*) FROM notas_detalhadas WHERE status LIKE '%autorizado%'"
                ).fetchone()
                stats['notas_autorizadas'] = result[0] if result else 0
                
                result = conn.execute(
                    "SELECT COUNT(*) FROM notas_detalhadas WHERE status LIKE '%cancelad%'"
                ).fetchone()
                stats['notas_canceladas'] = result[0] if result else 0
                
                result = conn.execute(
                    "SELECT COUNT(*) FROM notas_detalhadas WHERE status LIKE '%rejeitad%'"
                ).fetchone()
                stats['notas_rejeitadas'] = result[0] if result else 0
                
                # Certificados ativos
                result = conn.execute("SELECT COUNT(*) FROM certificados WHERE ativo = 1").fetchone()
                stats['certificados_ativos'] = result[0] if result else 0
                
                # Última atualização
                result = conn.execute(
                    "SELECT MAX(atualizado_em) FROM notas_detalhadas"
                ).fetchone()
                stats['ultimo_update'] = result[0] if result and result[0] else None
                
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
        
        return stats
    
    def cleanup_old_data(self, days: int = 365) -> int:
        """
        Remove dados antigos do banco
        
        Args:
            days: Número de dias para manter os dados
            
        Returns:
            Número de registros removidos
        """
        removed_count = 0
        
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                # Remove notas antigas
                cursor = conn.execute(
                    "DELETE FROM notas_detalhadas WHERE criado_em < ?",
                    (cutoff_date,)
                )
                removed_count += cursor.rowcount
                
                # Remove XMLs baixados antigos
                cursor = conn.execute(
                    "DELETE FROM xmls_baixados WHERE baixado_em < ?",
                    (cutoff_date,)
                )
                removed_count += cursor.rowcount
                
                conn.commit()
                logger.info(f"Removidos {removed_count} registros antigos (>{days} dias)")
                
        except Exception as e:
            logger.error(f"Erro ao limpar dados antigos: {e}")
        
        return removed_count