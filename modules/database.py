from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class DatabaseManager:
    """Database manager for NFe system - UI compatible."""
    
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._initialize()
    
    def _connect(self):
        return sqlite3.connect(str(self.db_path))
    
    def _initialize(self):
        """Initialize database tables."""
        with self._connect() as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS certificados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cnpj_cpf TEXT,
                caminho TEXT,
                senha TEXT,
                informante TEXT,
                cUF_autor TEXT,
                ativo INTEGER DEFAULT 1
            )''')
            
            # Adiciona coluna criado_em se não existir (migração)
            try:
                conn.execute("ALTER TABLE certificados ADD COLUMN criado_em TEXT")
                conn.commit()
            except Exception:
                # Coluna já existe, ignora
                pass
            
            conn.execute('''CREATE TABLE IF NOT EXISTS xmls_baixados (
                chave TEXT PRIMARY KEY,
                cnpj_cpf TEXT,
                caminho_arquivo TEXT,
                baixado_em TEXT
            )''')
            conn.execute('''CREATE TABLE IF NOT EXISTS nf_status (
                chNFe TEXT PRIMARY KEY,
                cStat TEXT,
                xMotivo TEXT
            )''')
            conn.execute('''CREATE TABLE IF NOT EXISTS nsu (
                informante TEXT PRIMARY KEY,
                ult_nsu TEXT
            )''')
            conn.execute('''CREATE TABLE IF NOT EXISTS nsu_cte (
                informante TEXT PRIMARY KEY,
                ult_nsu TEXT
            )''')
            conn.execute('''CREATE TABLE IF NOT EXISTS erro_656 (
                informante TEXT PRIMARY KEY,
                ultimo_erro TIMESTAMP,
                nsu_bloqueado TEXT
            )''')
            conn.execute('''CREATE TABLE IF NOT EXISTS config (
                chave TEXT PRIMARY KEY,
                valor TEXT
            )''')
            conn.execute('''CREATE TABLE IF NOT EXISTS notas_detalhadas (
                chave TEXT PRIMARY KEY,
                ie_tomador TEXT,
                nome_emitente TEXT,
                cnpj_emitente TEXT,
                numero TEXT,
                data_emissao TEXT,
                tipo TEXT,
                valor TEXT,
                cfop TEXT,
                vencimento TEXT,
                ncm TEXT,
                status TEXT,
                natureza TEXT,
                uf TEXT,
                base_icms TEXT,
                valor_icms TEXT,
                informante TEXT,
                xml_status TEXT,
                atualizado_em TEXT
            )''')
            conn.commit()
    
    def load_notes(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Load notes from database."""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM notas_detalhadas ORDER BY data_emissao DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def load_certificates(self) -> List[Dict[str, Any]]:
        """Load certificates from database."""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM certificados ORDER BY informante")
            return [dict(row) for row in cursor.fetchall()]
    
    def save_certificate(self, data: Dict[str, Any]) -> bool:
        """Save certificate to database. Returns True if successful."""
        try:
            with self._connect() as conn:
                # Check for duplicates by informante
                existing = conn.execute(
                    "SELECT id, informante, caminho FROM certificados WHERE informante = ?",
                    (data.get('informante'),)
                ).fetchone()
                
                if existing and not data.get('id'):
                    # Sempre remove o registro antigo se for tentativa de novo cadastro
                    print(f"[DEBUG] Removendo registro existente do certificado: {existing[1]}")
                    conn.execute("DELETE FROM certificados WHERE id = ?", (existing[0],))
                    conn.commit()
                    # Agora pode inserir o novo normalmente
                
                if data.get('id'):
                    # Update existing
                    conn.execute('''UPDATE certificados 
                        SET cnpj_cpf = ?, caminho = ?, senha = ?, 
                            cUF_autor = ?, ativo = ?
                        WHERE id = ?''',
                        (data.get('cnpj_cpf'), data.get('caminho'), 
                         data.get('senha'), data.get('cUF_autor'),
                         data.get('ativo', 1), data.get('id'))
                    )
                else:
                    # Insert new
                    conn.execute('''INSERT INTO certificados 
                        (informante, cnpj_cpf, caminho, senha, cUF_autor, ativo, criado_em)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                        (data.get('informante'), data.get('cnpj_cpf'),
                         data.get('caminho'), data.get('senha'),
                         data.get('cUF_autor'), data.get('ativo', 1),
                         datetime.now().isoformat())
                    )
                conn.commit()
                return True
        except Exception as e:
            print(f"[DEBUG] Erro ao salvar certificado: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def save_note(self, data: Dict[str, Any]) -> bool:
        """Save note to database with anti-downgrade logic."""
        try:
            with self._connect() as conn:
                chave = data.get('chave')
                if not chave:
                    return False
                
                new_status = (data.get('xml_status') or 'RESUMO').upper()
                
                # Validação: não salvar resumos/eventos sem dados essenciais
                if new_status in ['RESUMO', 'EVENTO']:
                    numero = data.get('numero') or ''
                    nome = data.get('nome_emitente') or ''
                    if not numero.strip() and not nome.strip():
                        # Resumo/evento sem dados válidos - não salva
                        return False
                
                # Check existing status
                existing = conn.execute(
                    "SELECT xml_status FROM notas_detalhadas WHERE chave = ?",
                    (chave,)
                ).fetchone()
                
                if existing:
                    old_status = (existing[0] or 'RESUMO').upper()
                    # Anti-downgrade: don't replace COMPLETO with RESUMO
                    if old_status == 'COMPLETO' and new_status == 'RESUMO':
                        return False
                    
                    # Update
                    conn.execute('''UPDATE notas_detalhadas 
                        SET ie_tomador = ?, nome_emitente = ?, cnpj_emitente = ?,
                            numero = ?, data_emissao = ?, tipo = ?, valor = ?,
                            cfop = ?, vencimento = ?, ncm = ?, status = ?,
                            natureza = ?, uf = ?, base_icms = ?, valor_icms = ?,
                            informante = ?, xml_status = ?, atualizado_em = ?
                        WHERE chave = ?''',
                        (data.get('ie_tomador'), data.get('nome_emitente'),
                         data.get('cnpj_emitente'), data.get('numero'),
                         data.get('data_emissao'), data.get('tipo'),
                         data.get('valor'), data.get('cfop'),
                         data.get('vencimento'), data.get('ncm'),
                         data.get('status'), data.get('natureza'),
                         data.get('uf'), data.get('base_icms'),
                         data.get('valor_icms'), data.get('informante'),
                         new_status, datetime.now().isoformat(), chave)
                    )
                else:
                    # Insert
                    conn.execute('''INSERT INTO notas_detalhadas
                        (chave, ie_tomador, nome_emitente, cnpj_emitente,
                         numero, data_emissao, tipo, valor, cfop, vencimento,
                         ncm, status, natureza, uf, base_icms, valor_icms,
                         informante, xml_status, atualizado_em)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (chave, data.get('ie_tomador'), data.get('nome_emitente'),
                         data.get('cnpj_emitente'), data.get('numero'),
                         data.get('data_emissao'), data.get('tipo'),
                         data.get('valor'), data.get('cfop'),
                         data.get('vencimento'), data.get('ncm'),
                         data.get('status'), data.get('natureza'),
                         data.get('uf'), data.get('base_icms'),
                         data.get('valor_icms'), data.get('informante'),
                         new_status, datetime.now().isoformat())
                    )
                conn.commit()
                return True
        except Exception:
            return False
    
    def deletar_nota_detalhada(self, chave: str) -> bool:
        """Delete note from notas_detalhadas table."""
        try:
            with self._connect() as conn:
                conn.execute("DELETE FROM notas_detalhadas WHERE chave = ?", (chave,))
                conn.commit()
                return True
        except Exception:
            return False
    
    def register_xml_download(self, chave: str, caminho: str, cnpj_cpf: str = "") -> bool:
        """Register downloaded XML in xmls_baixados table."""
        try:
            with self._connect() as conn:
                conn.execute('''INSERT OR REPLACE INTO xmls_baixados
                    (chave, cnpj_cpf, caminho_arquivo, baixado_em)
                    VALUES (?, ?, ?, ?)''',
                    (chave, cnpj_cpf, caminho, datetime.now().isoformat())
                )
                conn.commit()
                return True
        except Exception:
            return False
    
    def get_last_search_time(self) -> Optional[str]:
        """Get the last search execution time."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT valor FROM config WHERE chave = 'ultima_busca'"
                ).fetchone()
                return row[0] if row else None
        except Exception:
            return None
    
    def set_last_search_time(self, timestamp: str) -> bool:
        """Set the last search execution time."""
        try:
            with self._connect() as conn:
                conn.execute(
                    '''INSERT OR REPLACE INTO config (chave, valor)
                       VALUES ('ultima_busca', ?)''',
                    (timestamp,)
                )
                conn.commit()
                return True
        except Exception:
            return False
    
    def atualizar_status_por_evento(self, chave: str, novo_status: str) -> bool:
        """Atualiza o status de uma nota baseado em evento (cancelamento, etc)."""
        try:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE notas_detalhadas SET status = ? WHERE chave = ?",
                    (novo_status, chave)
                )
                conn.commit()
                return True
        except Exception:
            return False
    
    def get_next_search_interval(self) -> Optional[int]:
        """Get the search interval in minutes (default 65)."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT valor FROM config WHERE chave = 'intervalo_busca'"
                ).fetchone()
                return int(row[0]) if row else 65
        except Exception:
            return 65
