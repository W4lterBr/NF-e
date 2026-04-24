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
            conn.execute('''CREATE TABLE IF NOT EXISTS nsu_nfse (
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
                
                # Migração: Adiciona coluna pdf_path para cache de caminho do PDF
                if 'pdf_path' not in columns:
                    print("[MIGRAÇÃO] Adicionando coluna pdf_path para cache de PDFs...")
                    conn.execute("ALTER TABLE notas_detalhadas ADD COLUMN pdf_path TEXT")
                    print("[MIGRAÇÃO] ✅ Coluna pdf_path adicionada com sucesso")
                    print("[INFO] PDFs serão indexados automaticamente conforme forem acessados")
                
                # Migração: Adiciona coluna pdf_tipo ('OFICIAL', 'GENERICO', NULL=desconhecido)
                if 'pdf_tipo' not in columns:
                    print("[MIGRAÇÃO] Adicionando coluna pdf_tipo para controle de qualidade de PDFs...")
                    conn.execute("ALTER TABLE notas_detalhadas ADD COLUMN pdf_tipo TEXT")
                    print("[MIGRAÇÃO] ✅ Coluna pdf_tipo adicionada com sucesso")
                
                # Migração: Adiciona colunas IBS e CBS (Reforma Tributária)
                if 'v_ibs' not in columns:
                    print("[MIGRAÇÃO] Adicionando coluna v_ibs (Imposto sobre Bens e Serviços)...")
                    conn.execute("ALTER TABLE notas_detalhadas ADD COLUMN v_ibs TEXT")
                    print("[MIGRAÇÃO] ✅ Coluna v_ibs adicionada com sucesso")
                if 'v_cbs' not in columns:
                    print("[MIGRAÇÃO] Adicionando coluna v_cbs (Contribuição sobre Bens e Serviços)...")
                    conn.execute("ALTER TABLE notas_detalhadas ADD COLUMN v_cbs TEXT")
                    print("[MIGRAÇÃO] ✅ Coluna v_cbs adicionada com sucesso")

                # Reparo: preenche nome_destinatario em NFS-e ADN que foram salvas sem esse campo
                try:
                    conn.execute("""
                        UPDATE notas_detalhadas
                        SET nome_destinatario = (
                            SELECT d.tom_xnome FROM nfse_docs d
                            WHERE d.prest_cnpj = notas_detalhadas.cnpj_emitente
                              AND d.n_nfse = notas_detalhadas.numero
                              AND d.tom_xnome IS NOT NULL AND d.tom_xnome != ''
                            LIMIT 1
                        )
                        WHERE tipo = 'NFS-e'
                          AND (nome_destinatario IS NULL OR nome_destinatario = '')
                          AND EXISTS (
                            SELECT 1 FROM nfse_docs d
                            WHERE d.prest_cnpj = notas_detalhadas.cnpj_emitente
                              AND d.n_nfse = notas_detalhadas.numero
                              AND d.tom_xnome IS NOT NULL AND d.tom_xnome != ''
                          )
                    """)
                    if conn.execute("SELECT changes()").fetchone()[0]:
                        print("[MIGRAÇÃO] ✅ nome_destinatario preenchido para NFS-e ADN existentes")
                except Exception as _e:
                    print(f"[MIGRAÇÃO] Aviso ao reparar nome_destinatario: {_e}")
            except Exception as e:
                print(f"[MIGRAÇÃO] Erro ao adicionar colunas: {e}")

            # ------------------------------------------------------------------
            # Tabela nfe_docs — campos completos extraídos do XML NF-e
            # ------------------------------------------------------------------
            conn.execute('''CREATE TABLE IF NOT EXISTS nfe_docs (
                chave          TEXT PRIMARY KEY,
                informante     TEXT,
                caminho_xml    TEXT,
                caminho_pdf    TEXT,
                xml_status     TEXT,
                -- ide
                c_uf           TEXT,
                nat_op         TEXT,
                mod            TEXT,
                serie          TEXT,
                n_nf           TEXT,
                dh_emi         TEXT,
                dh_sai_ent     TEXT,
                tp_nf          TEXT,
                id_dest        TEXT,
                c_mun_fg       TEXT,
                tp_imp         TEXT,
                tp_emis        TEXT,
                fin_nfe        TEXT,
                ind_final      TEXT,
                ind_pres       TEXT,
                -- emitente
                emit_cnpj      TEXT,
                emit_cpf       TEXT,
                emit_ie        TEXT,
                emit_xnome     TEXT,
                emit_xfant     TEXT,
                emit_xlgr      TEXT,
                emit_nro       TEXT,
                emit_xbairro   TEXT,
                emit_cmun      TEXT,
                emit_xmun      TEXT,
                emit_uf        TEXT,
                emit_cep       TEXT,
                emit_crt       TEXT,
                -- destinatário
                dest_cnpj      TEXT,
                dest_cpf       TEXT,
                dest_ie        TEXT,
                dest_xnome     TEXT,
                dest_xlgr      TEXT,
                dest_nro       TEXT,
                dest_xbairro   TEXT,
                dest_cmun      TEXT,
                dest_xmun      TEXT,
                dest_uf        TEXT,
                dest_cep       TEXT,
                -- totais ICMSTot
                v_bc           TEXT,
                v_icms         TEXT,
                v_icms_deson   TEXT,
                v_fcp          TEXT,
                v_bc_st        TEXT,
                v_st           TEXT,
                v_fcp_st       TEXT,
                v_prod         TEXT,
                v_frete        TEXT,
                v_seg          TEXT,
                v_desc         TEXT,
                v_ii           TEXT,
                v_ipi          TEXT,
                v_pis          TEXT,
                v_cofins       TEXT,
                v_outro        TEXT,
                v_nf           TEXT,
                v_tot_trib     TEXT,
                -- IBS/CBS (Reforma Tributária)
                v_ibs          TEXT,
                v_cbs          TEXT,
                v_bc_ibscbs    TEXT,
                -- transporte
                mod_frete      TEXT,
                transp_cnpj    TEXT,
                transp_xnome   TEXT,
                -- pagamento
                t_pag          TEXT,
                v_pag          TEXT,
                -- protocolo
                n_prot         TEXT,
                dh_recbto      TEXT,
                c_stat         TEXT,
                x_motivo       TEXT,
                -- controle
                indexado_em    TEXT
            )''')
            try:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_nfe_docs_informante ON nfe_docs(informante)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_nfe_docs_emit_cnpj ON nfe_docs(emit_cnpj)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_nfe_docs_dest_cnpj ON nfe_docs(dest_cnpj)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_nfe_docs_dh_emi ON nfe_docs(dh_emi)")
            except Exception:
                pass

            # ------------------------------------------------------------------
            # Tabela cte_docs — campos completos extraídos do XML CT-e
            # ------------------------------------------------------------------
            conn.execute('''CREATE TABLE IF NOT EXISTS cte_docs (
                chave          TEXT PRIMARY KEY,
                informante     TEXT,
                caminho_xml    TEXT,
                caminho_pdf    TEXT,
                xml_status     TEXT,
                -- ide
                c_uf           TEXT,
                c_ct           TEXT,
                cfop           TEXT,
                nat_op         TEXT,
                mod            TEXT,
                serie          TEXT,
                n_ct           TEXT,
                dh_emi         TEXT,
                tp_imp         TEXT,
                tp_emis        TEXT,
                tp_amb         TEXT,
                tp_cte         TEXT,
                modal          TEXT,
                tp_serv        TEXT,
                c_mun_ini      TEXT,
                x_mun_ini      TEXT,
                uf_ini         TEXT,
                c_mun_fim      TEXT,
                x_mun_fim      TEXT,
                uf_fim         TEXT,
                -- emitente
                emit_cnpj      TEXT,
                emit_ie        TEXT,
                emit_xnome     TEXT,
                emit_xfant     TEXT,
                emit_uf        TEXT,
                emit_xmun      TEXT,
                emit_cep       TEXT,
                -- remetente
                rem_cnpj       TEXT,
                rem_cpf        TEXT,
                rem_ie         TEXT,
                rem_xnome      TEXT,
                rem_uf         TEXT,
                rem_xmun       TEXT,
                rem_cep        TEXT,
                -- destinatário
                dest_cnpj      TEXT,
                dest_cpf       TEXT,
                dest_ie        TEXT,
                dest_xnome     TEXT,
                dest_uf        TEXT,
                dest_xmun      TEXT,
                dest_cep       TEXT,
                -- tomador
                tom_cnpj       TEXT,
                tom_cpf        TEXT,
                tom_ie         TEXT,
                tom_xnome      TEXT,
                -- valores prestação
                v_tprest       TEXT,
                v_rec          TEXT,
                -- impostos
                v_tot_trib     TEXT,
                cst_icms       TEXT,
                v_bc_icms      TEXT,
                v_icms         TEXT,
                -- carga
                v_carga        TEXT,
                pro_pred       TEXT,
                v_carga_averb  TEXT,
                -- NF-e vinculadas (JSON array de chaves)
                nfe_vinculadas TEXT,
                -- modal rodoviário
                rntrc          TEXT,
                veic_placa     TEXT,
                -- protocolo
                n_prot         TEXT,
                dh_recbto      TEXT,
                c_stat         TEXT,
                x_motivo       TEXT,
                -- controle
                indexado_em    TEXT
            )''')
            try:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_cte_docs_informante ON cte_docs(informante)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_cte_docs_emit_cnpj ON cte_docs(emit_cnpj)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_cte_docs_rem_cnpj ON cte_docs(rem_cnpj)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_cte_docs_dest_cnpj ON cte_docs(dest_cnpj)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_cte_docs_dh_emi ON cte_docs(dh_emi)")
            except Exception:
                pass

            # ------------------------------------------------------------------
            # Tabela nfse_docs — campos completos extraídos do XML NFS-e
            # ------------------------------------------------------------------
            conn.execute('''CREATE TABLE IF NOT EXISTS nfse_docs (
                chave          TEXT PRIMARY KEY,
                informante     TEXT,
                caminho_xml    TEXT,
                caminho_pdf    TEXT,
                xml_status     TEXT,
                -- identificação
                n_nfse         TEXT,
                n_dfse         TEXT,
                n_dps          TEXT,
                serie          TEXT,
                dh_proc        TEXT,
                dh_emi         TEXT,
                d_compet       TEXT,
                c_stat         TEXT,
                x_motivo       TEXT,
                tp_emis        TEXT,
                tp_amb         TEXT,
                ver_aplic      TEXT,
                -- localização
                c_loc_incid    TEXT,
                x_loc_incid    TEXT,
                x_trib_nac     TEXT,
                x_trib_mun     TEXT,
                x_nbs          TEXT,
                c_loc_prestacao TEXT,
                -- prestador (emitente)
                prest_cnpj     TEXT,
                prest_cpf      TEXT,
                prest_im       TEXT,
                prest_xnome    TEXT,
                prest_xfant    TEXT,
                prest_cmun     TEXT,
                prest_uf       TEXT,
                prest_cep      TEXT,
                prest_email    TEXT,
                -- regime tributário
                op_simp_nac    TEXT,
                reg_esp_trib   TEXT,
                -- tomador
                tom_cnpj       TEXT,
                tom_cpf        TEXT,
                tom_xnome      TEXT,
                tom_cmun       TEXT,
                tom_uf         TEXT,
                tom_cep        TEXT,
                tom_email      TEXT,
                -- serviço
                c_trib_nac     TEXT,
                c_trib_mun     TEXT,
                x_desc_serv    TEXT,
                c_nbs          TEXT,
                -- valores
                v_serv         TEXT,
                v_bc           TEXT,
                p_aliq         TEXT,
                v_issqn        TEXT,
                v_total_ret    TEXT,
                v_liq          TEXT,
                v_calc_dr      TEXT,
                -- controle
                indexado_em    TEXT
            )''')
            try:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_nfse_docs_informante ON nfse_docs(informante)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_nfse_docs_prest_cnpj ON nfse_docs(prest_cnpj)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_nfse_docs_tom_cnpj ON nfse_docs(tom_cnpj)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_nfse_docs_dh_emi ON nfse_docs(dh_emi)")
            except Exception:
                pass

            # Tabela nfce_docs — campos completos extraídos do XML NFC-e (modelo 65)
            # ------------------------------------------------------------------
            conn.execute('''CREATE TABLE IF NOT EXISTS nfce_docs (
                chave          TEXT PRIMARY KEY,
                informante     TEXT,
                caminho_xml    TEXT,
                caminho_pdf    TEXT,
                xml_status     TEXT,
                -- identificação
                c_uf           TEXT,
                nat_op         TEXT,
                mod            TEXT,
                serie          TEXT,
                n_nf           TEXT,
                dh_emi         TEXT,
                tp_nf          TEXT,
                c_mun_fg       TEXT,
                tp_emis        TEXT,
                fin_nfe        TEXT,
                -- emitente
                emit_cnpj      TEXT,
                emit_cpf       TEXT,
                emit_ie        TEXT,
                emit_xnome     TEXT,
                emit_xfant     TEXT,
                emit_xlgr      TEXT,
                emit_nro       TEXT,
                emit_xbairro   TEXT,
                emit_cmun      TEXT,
                emit_xmun      TEXT,
                emit_uf        TEXT,
                emit_cep       TEXT,
                emit_crt       TEXT,
                -- destinatário (opcional na NFC-e)
                dest_cnpj      TEXT,
                dest_cpf       TEXT,
                dest_xnome     TEXT,
                -- produtos (JSON array)
                produtos       TEXT,
                qt_itens       INTEGER,
                -- totais ICMSTot
                v_prod         TEXT,
                v_desc         TEXT,
                v_frete        TEXT,
                v_seg          TEXT,
                v_outro        TEXT,
                v_pis          TEXT,
                v_cofins       TEXT,
                v_nf           TEXT,
                v_bc           TEXT,
                v_icms         TEXT,
                v_icms_deson   TEXT,
                v_tot_trib     TEXT,
                -- pagamento
                t_pag          TEXT,
                v_pag          TEXT,
                v_troco        TEXT,
                -- QR Code / suplementar
                qr_code        TEXT,
                url_chave      TEXT,
                -- protocolo
                n_prot         TEXT,
                dh_recbto      TEXT,
                c_stat         TEXT,
                x_motivo       TEXT,
                -- controle
                indexado_em    TEXT
            )''')
            try:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_nfce_docs_informante ON nfce_docs(informante)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_nfce_docs_emit_cnpj ON nfce_docs(emit_cnpj)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_nfce_docs_dh_emi ON nfce_docs(dh_emi)")
            except Exception:
                pass

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
                    # Anti-downgrade: protege hierarquia EVENTO > COMPLETO > RESUMO
                    # EVENTO nunca pode virar COMPLETO ou RESUMO (é evento, não nota)
                    if old_status == 'EVENTO':
                        return False  # Nunca sobrescreve EVENTO
                    # COMPLETO não pode virar RESUMO (downgrade)
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
    
    def atualizar_pdf_path(self, chave: str, pdf_path: str, pdf_tipo: str = None) -> bool:
        """
        Update PDF path cache in notas_detalhadas table.
        
        This dramatically speeds up PDF opening by avoiding filesystem searches.
        The system will auto-heal: when a PDF is found via search, the path is cached.
        
        Args:
            chave: Document key (44 digits)
            pdf_path: Absolute path to the PDF file
            pdf_tipo: 'OFICIAL' (from ADN/ABRASF API) or 'GENERICO' (locally generated)
        
        Returns:
            True if updated successfully
        """
        try:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE notas_detalhadas SET pdf_path = ?, pdf_tipo = ?, atualizado_em = ? WHERE chave = ?",
                    (pdf_path, pdf_tipo, datetime.now().isoformat(), chave)
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"[ERRO] Falha ao atualizar pdf_path para {chave}: {e}")
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
    
    def get_nf_status(self, chave: str) -> Optional[tuple]:
        """
        Busca status de uma NF-e/CT-e pelo chave na tabela nf_status.
        
        Args:
            chave: Chave de 44 dígitos do documento
            
        Returns:
            tuple(cStat, xMotivo) ou None se não encontrado
        """
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    "SELECT cStat, xMotivo FROM nf_status WHERE chNFe = ?",
                    (chave,)
                )
                return cursor.fetchone()
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

    def get_nota_by_chave(self, chave: str) -> Optional[Dict[str, Any]]:
        """Busca uma única nota pela chave usando o índice PRIMARY KEY (O(1))."""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM notas_detalhadas WHERE chave = ?", (chave,)
            ).fetchone()
            return dict(row) if row else None

    def atualizar_data_emissao_se_vazia(self, chave: str, data_emissao: str) -> bool:
        """Atualiza data_emissao de uma nota somente se estiver vazia ou nula.
        
        Usado ao processar eventos (cancelamento, carta correção) para garantir que
        notas que chegaram como RESUMO/INDISPONIVEL sempre tenham uma data visível.
        """
        try:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE notas_detalhadas SET data_emissao = ? WHERE chave = ? AND (data_emissao IS NULL OR data_emissao = '')",
                    (data_emissao, chave)
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
    
    def get_manifestacoes_by_chave(self, chave: str) -> list:
        """
        Busca todas as manifestações de uma chave específica.
        
        Args:
            chave: Chave de acesso do documento (44 dígitos)
        
        Returns:
            list: Lista de manifestações encontradas
        """
        try:
            with self._connect() as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    '''SELECT tipo_evento, informante, data_manifestacao as enviado_em, 
                              status, protocolo 
                       FROM manifestacoes 
                       WHERE chave = ? 
                       ORDER BY data_manifestacao DESC''',
                    (chave,)
                ).fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"[DEBUG] Erro ao buscar manifestações: {e}")
            return []
    
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
    
    def get_config(self, chave: str, default=None) -> Optional[str]:
        """Busca valor de configuração.
        
        Args:
            chave: Chave da configuração
            default: Valor padrão se não existir
            
        Returns:
            Valor da configuração ou default
        """
        try:
            with self._connect() as conn:
                cursor = conn.execute("SELECT valor FROM config WHERE chave = ?", (chave,))
                row = cursor.fetchone()
                return row[0] if row else default
        except Exception:
            return default
    
    def set_config(self, chave: str, valor: str):
        """Define valor de configuração.
        
        Args:
            chave: Chave da configuração
            valor: Valor a ser armazenado
        """
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO config (chave, valor) VALUES (?, ?)",
                    (chave, valor)
                )
                conn.commit()
        except Exception as e:
            print(f"Erro ao salvar config: {e}")
    
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

    # ------------------------------------------------------------------
    # Métodos upsert para as tabelas de documentos indexados
    # ------------------------------------------------------------------

    def upsert_nfe_doc(self, data: Dict[str, Any]) -> bool:
        """Insere ou atualiza um documento NF-e na tabela nfe_docs."""
        try:
            fields = [
                "chave", "informante", "caminho_xml", "caminho_pdf", "xml_status",
                "c_uf", "nat_op", "mod", "serie", "n_nf", "dh_emi", "dh_sai_ent",
                "tp_nf", "id_dest", "c_mun_fg", "tp_imp", "tp_emis", "fin_nfe",
                "ind_final", "ind_pres",
                "emit_cnpj", "emit_cpf", "emit_ie", "emit_xnome", "emit_xfant",
                "emit_xlgr", "emit_nro", "emit_xbairro", "emit_cmun", "emit_xmun",
                "emit_uf", "emit_cep", "emit_crt",
                "dest_cnpj", "dest_cpf", "dest_ie", "dest_xnome",
                "dest_xlgr", "dest_nro", "dest_xbairro", "dest_cmun", "dest_xmun",
                "dest_uf", "dest_cep",
                "v_bc", "v_icms", "v_icms_deson", "v_fcp", "v_bc_st", "v_st",
                "v_fcp_st", "v_prod", "v_frete", "v_seg", "v_desc", "v_ii",
                "v_ipi", "v_pis", "v_cofins", "v_outro", "v_nf", "v_tot_trib",
                "v_ibs", "v_cbs", "v_bc_ibscbs",
                "mod_frete", "transp_cnpj", "transp_xnome",
                "t_pag", "v_pag",
                "n_prot", "dh_recbto", "c_stat", "x_motivo",
                "indexado_em",
            ]
            cols = ", ".join(fields)
            placeholders = ", ".join(["?"] * len(fields))
            values = [data.get(f) for f in fields]
            with self._connect() as conn:
                conn.execute(
                    f"INSERT OR REPLACE INTO nfe_docs ({cols}) VALUES ({placeholders})",
                    values,
                )
                conn.commit()
            return True
        except Exception as e:
            print(f"[DB] Erro upsert_nfe_doc: {e}")
            return False

    def upsert_cte_doc(self, data: Dict[str, Any]) -> bool:
        """Insere ou atualiza um documento CT-e na tabela cte_docs."""
        try:
            fields = [
                "chave", "informante", "caminho_xml", "caminho_pdf", "xml_status",
                "c_uf", "c_ct", "cfop", "nat_op", "mod", "serie", "n_ct", "dh_emi",
                "tp_imp", "tp_emis", "tp_amb", "tp_cte", "modal", "tp_serv",
                "c_mun_ini", "x_mun_ini", "uf_ini", "c_mun_fim", "x_mun_fim", "uf_fim",
                "emit_cnpj", "emit_ie", "emit_xnome", "emit_xfant",
                "emit_uf", "emit_xmun", "emit_cep",
                "rem_cnpj", "rem_cpf", "rem_ie", "rem_xnome",
                "rem_uf", "rem_xmun", "rem_cep",
                "dest_cnpj", "dest_cpf", "dest_ie", "dest_xnome",
                "dest_uf", "dest_xmun", "dest_cep",
                "tom_cnpj", "tom_cpf", "tom_ie", "tom_xnome",
                "v_tprest", "v_rec",
                "v_tot_trib", "cst_icms", "v_bc_icms", "v_icms",
                "v_carga", "pro_pred", "v_carga_averb",
                "nfe_vinculadas",
                "rntrc", "veic_placa",
                "n_prot", "dh_recbto", "c_stat", "x_motivo",
                "indexado_em",
            ]
            cols = ", ".join(fields)
            placeholders = ", ".join(["?"] * len(fields))
            values = [data.get(f) for f in fields]
            with self._connect() as conn:
                conn.execute(
                    f"INSERT OR REPLACE INTO cte_docs ({cols}) VALUES ({placeholders})",
                    values,
                )
                conn.commit()
            return True
        except Exception as e:
            print(f"[DB] Erro upsert_cte_doc: {e}")
            return False

    def upsert_nfse_doc(self, data: Dict[str, Any]) -> bool:
        """Insere ou atualiza um documento NFS-e na tabela nfse_docs."""
        try:
            fields = [
                "chave", "informante", "caminho_xml", "caminho_pdf", "xml_status",
                "n_nfse", "n_dfse", "n_dps", "serie", "dh_proc", "dh_emi",
                "d_compet", "c_stat", "x_motivo", "tp_emis", "tp_amb", "ver_aplic",
                "c_loc_incid", "x_loc_incid", "x_trib_nac", "x_trib_mun", "x_nbs",
                "c_loc_prestacao",
                "prest_cnpj", "prest_cpf", "prest_im", "prest_xnome", "prest_xfant",
                "prest_cmun", "prest_uf", "prest_cep", "prest_email",
                "op_simp_nac", "reg_esp_trib",
                "tom_cnpj", "tom_cpf", "tom_xnome",
                "tom_cmun", "tom_uf", "tom_cep", "tom_email",
                "c_trib_nac", "c_trib_mun", "x_desc_serv", "c_nbs",
                "v_serv", "v_bc", "p_aliq", "v_issqn", "v_total_ret", "v_liq", "v_calc_dr",
                "indexado_em",
            ]
            cols = ", ".join(fields)
            placeholders = ", ".join(["?"] * len(fields))
            values = [data.get(f) for f in fields]
            with self._connect() as conn:
                conn.execute(
                    f"INSERT OR REPLACE INTO nfse_docs ({cols}) VALUES ({placeholders})",
                    values,
                )
                conn.commit()
            return True
        except Exception as e:
            print(f"[DB] Erro upsert_nfse_doc: {e}")
            return False

    def upsert_nfce_doc(self, data: Dict[str, Any]) -> bool:
        """Insere ou atualiza um documento NFC-e na tabela nfce_docs."""
        try:
            fields = [
                "chave", "informante", "caminho_xml", "caminho_pdf", "xml_status",
                "c_uf", "nat_op", "mod", "serie", "n_nf", "dh_emi", "tp_nf",
                "c_mun_fg", "tp_emis", "fin_nfe",
                "emit_cnpj", "emit_cpf", "emit_ie", "emit_xnome", "emit_xfant",
                "emit_xlgr", "emit_nro", "emit_xbairro", "emit_cmun", "emit_xmun",
                "emit_uf", "emit_cep", "emit_crt",
                "dest_cnpj", "dest_cpf", "dest_xnome",
                "produtos", "qt_itens",
                "v_prod", "v_desc", "v_frete", "v_seg", "v_outro",
                "v_pis", "v_cofins", "v_nf", "v_bc", "v_icms", "v_icms_deson", "v_tot_trib",
                "t_pag", "v_pag", "v_troco",
                "qr_code", "url_chave",
                "n_prot", "dh_recbto", "c_stat", "x_motivo",
                "indexado_em",
            ]
            cols = ", ".join(fields)
            placeholders = ", ".join(["?"] * len(fields))
            values = [data.get(f) for f in fields]
            with self._connect() as conn:
                conn.execute(
                    f"INSERT OR REPLACE INTO nfce_docs ({cols}) VALUES ({placeholders})",
                    values,
                )
                conn.commit()
            return True
        except Exception as e:
            print(f"[DB] Erro upsert_nfce_doc: {e}")
            return False

    def atualizar_caminho_pdf_doc(self, chave: str, caminho_pdf: str, tipo_doc: str) -> bool:
        """Atualiza o caminho do PDF nas tabelas de documentos indexados (nfe_docs / cte_docs / nfse_docs / nfce_docs)."""
        tabelas = {
            "NFe": "nfe_docs",
            "CTe": "cte_docs",
            "NFSe": "nfse_docs",
            "NFCe": "nfce_docs",
        }
        tabela = tabelas.get(tipo_doc)
        if not tabela:
            return False
        try:
            with self._connect() as conn:
                conn.execute(
                    f"UPDATE {tabela} SET caminho_pdf = ? WHERE chave = ?",
                    (caminho_pdf, chave),
                )
                conn.commit()
            return True
        except Exception as e:
            print(f"[DB] Erro atualizar_caminho_pdf_doc: {e}")
            return False
