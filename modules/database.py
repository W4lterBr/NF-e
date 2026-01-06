from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Importa módulo de criptografia PORTÁVEL (para distribuição em .exe)
try:
    from .crypto_portable import get_portable_crypto as get_crypto
    CRYPTO_AVAILABLE = True
except ImportError:
    # Fallback para chave local (desenvolvimento)
    try:
        from .crypto_utils import get_crypto
        CRYPTO_AVAILABLE = True
    except ImportError:
        CRYPTO_AVAILABLE = False
        print("⚠️ Módulo de criptografia não disponível")


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
            
            # Adiciona coluna ativo se não existir (migração)
            try:
                conn.execute("ALTER TABLE certificados ADD COLUMN ativo INTEGER DEFAULT 1")
                conn.commit()
            except Exception:
                # Coluna já existe, ignora
                pass
            
            # Adiciona coluna criado_em se não existir (migração)
            try:
                conn.execute("ALTER TABLE certificados ADD COLUMN criado_em TEXT")
                conn.commit()
            except Exception:
                # Coluna já existe, ignora
                pass
            
            # Adiciona coluna razao_social se não existir (migração)
            try:
                conn.execute("ALTER TABLE certificados ADD COLUMN razao_social TEXT")
                conn.commit()
            except Exception:
                # Coluna já existe, ignora
                pass
            
            # Adiciona coluna nome_certificado se não existir (migração)
            try:
                conn.execute("ALTER TABLE certificados ADD COLUMN nome_certificado TEXT")
                conn.commit()
            except Exception:
                # Coluna já existe, ignora
                pass
            
            conn.execute('''CREATE TABLE IF NOT EXISTS xmls_baixados (
                chave TEXT PRIMARY KEY,
                cnpj_cpf TEXT,
                caminho_arquivo TEXT,
                xml_completo TEXT,
                baixado_em TEXT
            )''')
            # Migração: adicionar coluna xml_completo se não existir
            try:
                conn.execute("ALTER TABLE xmls_baixados ADD COLUMN xml_completo TEXT")
            except:
                pass  # Coluna já existe
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
                nome_destinatario TEXT,
                cnpj_destinatario TEXT,
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
            
            # Tabela de manifestações registradas
            conn.execute('''CREATE TABLE IF NOT EXISTS manifestacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chave TEXT NOT NULL,
                tipo_evento TEXT NOT NULL,
                informante TEXT NOT NULL,
                data_manifestacao TEXT NOT NULL,
                status TEXT,
                protocolo TEXT,
                UNIQUE(chave, tipo_evento, informante)
            )''')            
            
            # Tabela de chaves canceladas (para não buscar mais eventos)
            conn.execute('''CREATE TABLE IF NOT EXISTS chaves_canceladas (
                chave TEXT PRIMARY KEY,
                data_cancelamento TEXT NOT NULL,
                motivo TEXT
            )''')
            
            # Tabela de estado de sincronização (para retomar após interrupção)
            conn.execute('''CREATE TABLE IF NOT EXISTS sync_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                ultima_chave TEXT,
                total_docs INTEGER,
                docs_processados INTEGER,
                data_inicio TEXT,
                status TEXT
            )''')
            
            # Índice para busca rápida
            try:
                conn.execute('''CREATE INDEX IF NOT EXISTS idx_manifestacoes_chave 
                             ON manifestacoes(chave)''')
                conn.execute('''CREATE INDEX IF NOT EXISTS idx_manifestacoes_informante 
                             ON manifestacoes(informante)''')
            except Exception:
                pass
            
            # Migração: Adiciona colunas destinatário se não existirem
            try:
                cursor = conn.execute("PRAGMA table_info(notas_detalhadas)")
                columns = [row[1] for row in cursor.fetchall()]
                if 'nome_destinatario' not in columns:
                    print("[MIGRAÇÃO] Adicionando coluna nome_destinatario...")
                    conn.execute("ALTER TABLE notas_detalhadas ADD COLUMN nome_destinatario TEXT")
                    print("[MIGRAÇÃO] Coluna nome_destinatario adicionada com sucesso")
                if 'cnpj_destinatario' not in columns:
                    print("[MIGRAÇÃO] Adicionando coluna cnpj_destinatario...")
                    conn.execute("ALTER TABLE notas_detalhadas ADD COLUMN cnpj_destinatario TEXT")
                    print("[MIGRAÇÃO] Coluna cnpj_destinatario adicionada com sucesso")
            except Exception as e:
                print(f"[MIGRAÇÃO] Erro ao adicionar colunas destinatário: {e}")
            
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
            certificates = [dict(row) for row in cursor.fetchall()]
            
            # Descriptografa senhas e corrige senhas em texto plano
            if CRYPTO_AVAILABLE:
                crypto = get_crypto()
                for cert in certificates:
                    if cert.get('senha'):
                        try:
                            # Verifica se senha está criptografada
                            if crypto.is_encrypted(cert['senha']):
                                # Descriptografa normalmente
                                cert['senha'] = crypto.decrypt(cert['senha'])
                            else:
                                # Senha em texto plano - precisa ser criptografada
                                print(f"⚠️ Senha do certificado {cert.get('informante')} está em texto plano. Criptografando...")
                                senha_plain = cert['senha']
                                senha_encrypted = crypto.encrypt(senha_plain)
                                
                                # Atualiza no banco de dados
                                with self._connect() as conn_update:
                                    conn_update.execute(
                                        "UPDATE certificados SET senha = ? WHERE id = ?",
                                        (senha_encrypted, cert['id'])
                                    )
                                    conn_update.commit()
                                
                                # Mantém senha descriptografada em memória
                                cert['senha'] = senha_plain
                                print(f"   ✅ Senha criptografada e salva no banco")
                        except Exception as e:
                            print(f"⚠️ Erro ao processar senha do certificado {cert.get('informante')}: {e}")
                            # Mantém a senha como está em caso de erro
                            pass
            
            return certificates
    
    def save_certificate(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Save certificate to database. 
        
        Returns:
            tuple: (success: bool, error_message: Optional[str])
        """
        try:
            # Validações básicas
            if not data.get('informante'):
                return False, "Campo 'Informante' está vazio"
            
            if not data.get('cnpj_cpf'):
                return False, "Campo 'CNPJ/CPF' está vazio"
            
            if not data.get('caminho'):
                return False, "Caminho do certificado não foi especificado"
            
            import os
            if not os.path.exists(data.get('caminho', '')):
                return False, f"Arquivo do certificado não encontrado:\n{data.get('caminho')}"
            
            if not data.get('cUF_autor'):
                return False, "Campo 'UF Autor' está vazio"
            
            # Criptografa senha antes de salvar
            senha_to_save = data.get('senha', '')
            if senha_to_save and CRYPTO_AVAILABLE:
                try:
                    crypto = get_crypto()
                    senha_to_save = crypto.encrypt(senha_to_save)
                except Exception as e:
                    print(f"[DEBUG] Erro ao criptografar senha: {e}")
                    return False, f"Erro ao criptografar senha: {e}"
            
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
                            cUF_autor = ?, ativo = ?, razao_social = ?
                        WHERE id = ?''',
                        (data.get('cnpj_cpf'), data.get('caminho'), 
                         senha_to_save, data.get('cUF_autor'),
                         data.get('ativo', 1), data.get('razao_social'),
                         data.get('id'))
                    )
                else:
                    # Insert new
                    # ⚠️ VALIDAÇÃO: informante deve ser CNPJ/CPF (11 ou 14 dígitos), NUNCA a senha
                    informante_value = data.get('informante')
                    if not informante_value or not str(informante_value).replace('.', '').replace('-', '').replace('/', '').isdigit():
                        # Se informante inválido, usa cnpj_cpf como fallback
                        print(f"[SEGURANÇA] Informante inválido detectado! Usando cnpj_cpf como fallback.")
                        informante_value = data.get('cnpj_cpf')
                    
                    conn.execute('''INSERT INTO certificados 
                        (informante, cnpj_cpf, caminho, senha, cUF_autor, ativo, criado_em, razao_social, nome_certificado)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (informante_value, data.get('cnpj_cpf'),
                         data.get('caminho'), senha_to_save,
                         data.get('cUF_autor'), data.get('ativo', 1),
                         datetime.now().isoformat(), data.get('razao_social'),
                         data.get('nome_certificado'))
                    )
                conn.commit()
                print(f"[DEBUG] Certificado salvo com sucesso: {informante_value}")
                return True, None
        except sqlite3.IntegrityError as e:
            error_msg = f"Erro de integridade do banco de dados: {e}"
            print(f"[DEBUG] {error_msg}")
            import traceback
            traceback.print_exc()
            return False, error_msg
        except sqlite3.OperationalError as e:
            error_msg = f"Erro operacional do banco: {e}"
            print(f"[DEBUG] {error_msg}")
            import traceback
            traceback.print_exc()
            return False, error_msg
        except Exception as e:
            error_msg = f"Erro inesperado: {type(e).__name__}: {e}"
            print(f"[DEBUG] Erro ao salvar certificado: {e}")
            import traceback
            traceback.print_exc()
            return False, error_msg
    
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
                            nome_destinatario = ?, cnpj_destinatario = ?, numero = ?, data_emissao = ?, tipo = ?, valor = ?,
                            cfop = ?, vencimento = ?, ncm = ?, status = ?,
                            natureza = ?, uf = ?, base_icms = ?, valor_icms = ?,
                            informante = ?, xml_status = ?, atualizado_em = ?
                        WHERE chave = ?''',
                        (data.get('ie_tomador'), data.get('nome_emitente'),
                         data.get('cnpj_emitente'), data.get('nome_destinatario'),
                         data.get('cnpj_destinatario'), data.get('numero'), data.get('data_emissao'), data.get('tipo'),
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
                         nome_destinatario, cnpj_destinatario, numero, data_emissao, tipo, valor, cfop, vencimento,
                         ncm, status, natureza, uf, base_icms, valor_icms,
                         informante, xml_status, atualizado_em)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (chave, data.get('ie_tomador'), data.get('nome_emitente'),
                         data.get('cnpj_emitente'), data.get('nome_destinatario'),
                         data.get('cnpj_destinatario'), data.get('numero'), data.get('data_emissao'), data.get('tipo'),
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
    
    def atualizar_status_nota(self, chave: str, novo_status: str) -> bool:
        """Update note status in notas_detalhadas table."""
        try:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE notas_detalhadas SET status = ?, atualizado_em = ? WHERE chave = ?",
                    (novo_status, datetime.now().isoformat(), chave)
                )
                conn.commit()
                return True
        except Exception:
            return False
    
    def atualizar_xml_status(self, chave: str, novo_xml_status: str) -> bool:
        """Update XML status in notas_detalhadas table (e.g., RESUMO -> COMPLETO)."""
        try:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE notas_detalhadas SET xml_status = ?, atualizado_em = ? WHERE chave = ?",
                    (novo_xml_status, datetime.now().isoformat(), chave)
                )
                conn.commit()
                return True
        except Exception:
            return False
    
    def get_documento_por_chave(self, chave: str) -> Optional[Dict[str, Any]]:
        """Busca documento completo por chave de acesso."""
        try:
            with self._connect() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM notas_detalhadas WHERE chave = ?",
                    (chave,)
                )
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception:
            return None
    
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
    
    def marcar_chave_cancelada(self, chave: str, motivo: str = 'Cancelamento') -> bool:
        """Marca uma chave como cancelada para não buscar mais eventos."""
        try:
            from datetime import datetime
            with self._connect() as conn:
                conn.execute(
                    '''INSERT OR REPLACE INTO chaves_canceladas (chave, data_cancelamento, motivo)
                       VALUES (?, ?, ?)''',
                    (chave, datetime.now().isoformat(), motivo)
                )
                conn.commit()
                return True
        except Exception:
            return False
    
    def is_chave_cancelada(self, chave: str) -> bool:
        """Verifica se uma chave está marcada como cancelada."""
        try:
            with self._connect() as conn:
                result = conn.execute(
                    "SELECT 1 FROM chaves_canceladas WHERE chave = ?",
                    (chave,)
                ).fetchone()
                return result is not None
        except Exception:
            return False
    
    def save_sync_state(self, ultima_chave: str, total: int, processados: int) -> bool:
        """Salva o estado atual da sincronização."""
        try:
            from datetime import datetime
            with self._connect() as conn:
                # Verifica se já existe um estado
                existing = conn.execute("SELECT id FROM sync_state WHERE id = 1").fetchone()
                
                if existing:
                    conn.execute(
                        '''UPDATE sync_state 
                           SET ultima_chave = ?, total_docs = ?, docs_processados = ?, status = 'em_progresso'
                           WHERE id = 1''',
                        (ultima_chave, total, processados)
                    )
                else:
                    conn.execute(
                        '''INSERT INTO sync_state (id, ultima_chave, total_docs, docs_processados, data_inicio, status)
                           VALUES (1, ?, ?, ?, ?, 'em_progresso')''',
                        (ultima_chave, total, processados, datetime.now().isoformat())
                    )
                conn.commit()
                return True
        except Exception as e:
            print(f"[DB] Erro ao salvar estado da sync: {e}")
            return False
    
    def get_sync_state(self) -> dict:
        """Recupera o estado da sincronização pendente."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT ultima_chave, total_docs, docs_processados, data_inicio, status FROM sync_state WHERE id = 1"
                ).fetchone()
                
                if row and row[4] == 'em_progresso':
                    return {
                        'ultima_chave': row[0],
                        'total_docs': row[1],
                        'docs_processados': row[2],
                        'data_inicio': row[3],
                        'status': row[4]
                    }
                return None
        except Exception:
            return None
    
    def clear_sync_state(self) -> bool:
        """Limpa o estado da sincronização (quando concluída ou cancelada)."""
        try:
            with self._connect() as conn:
                conn.execute("UPDATE sync_state SET status = 'concluida' WHERE id = 1")
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
    
    def check_manifestacao_exists(self, chave: str, tipo_evento: str, informante: str) -> bool:
        """
        Verifica se manifestação já foi registrada.
        
        Args:
            chave: Chave de acesso da NF-e
            tipo_evento: Tipo do evento (ex: '210210' para Ciência da Operação)
            informante: CNPJ/CPF do informante
        
        Returns:
            bool: True se manifestação já existe, False caso contrário
        """
        try:
            with self._connect() as conn:
                result = conn.execute(
                    "SELECT COUNT(*) FROM manifestacoes WHERE chave = ? AND tipo_evento = ? AND informante = ?",
                    (chave, tipo_evento, informante)
                ).fetchone()
                return result[0] > 0
        except Exception:
            return False
    
    def register_manifestacao(self, chave: str, tipo_evento: str, informante: str, 
                             status: str = 'ENVIADA', protocolo: str = None) -> bool:
        """
        Registra manifestação para prevenir duplicatas.
        
        Args:
            chave: Chave de acesso da NF-e
            tipo_evento: Tipo do evento (ex: '210210')
            informante: CNPJ/CPF do informante
            status: Status da manifestação
            protocolo: Número do protocolo SEFAZ
        
        Returns:
            bool: True se registrado com sucesso, False se já existe
        """
        try:
            from datetime import datetime
            with self._connect() as conn:
                conn.execute('''INSERT INTO manifestacoes 
                    (chave, tipo_evento, informante, data_manifestacao, status, protocolo)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                    (chave, tipo_evento, informante, datetime.now().isoformat(), status, protocolo)
                )
                conn.commit()
                return True
        except Exception:
            # Manifestação já existe (UNIQUE constraint violated)
            return False
    
    def get_config(self, chave: str, default: str = None) -> Optional[str]:
        """Get a configuration value."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT valor FROM config WHERE chave = ?", (chave,)
                ).fetchone()
                return row[0] if row else default
        except Exception:
            return default
    
    def set_config(self, chave: str, valor: str) -> bool:
        """Set a configuration value."""
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO config (chave, valor) VALUES (?, ?)",
                    (chave, valor)
                )
                conn.commit()
                return True
        except Exception:
            return False
    
    def set_next_search_interval(self, minutos: int) -> bool:
        """Define o intervalo de busca automática em minutos."""
        return self.set_config('search_interval_minutes', str(minutos))
    
    def get_next_search_interval(self) -> int:
        """Obtém o intervalo de busca automática em minutos. Padrão: 60 minutos (1 hora)."""
        try:
            valor = self.get_config('search_interval_minutes', '60')
            return int(valor)
        except Exception:
            return 60
    
    def get_cert_nome_by_informante(self, informante: str) -> Optional[str]:
        """Busca o nome personalizado do certificado pelo informante.
        
        Args:
            informante: CNPJ/CPF do informante
            
        Returns:
            Nome do certificado ou None se não houver nome personalizado
        """
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    "SELECT nome_certificado FROM certificados WHERE informante = ?",
                    (informante,)
                )
                row = cursor.fetchone()
                if row and row[0]:
                    return row[0]
                return None
        except Exception:
            return None
