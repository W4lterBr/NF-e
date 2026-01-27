"""
Gerenciador de Quota de Consultas SEFAZ
Controla o limite de 20 consultas por chave por hora por certificado
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional

class QuotaManager:
    """Gerencia quotas de consulta à SEFAZ por certificado"""
    
    # Limite da SEFAZ: 20 consultas por chave por hora
    LIMITE_HORA = 20
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Args:
            storage_path: Caminho para arquivo de persistência das quotas
        """
        if storage_path is None:
            storage_path = Path(__file__).parent.parent / "quota_cache.json"
        
        self.storage_path = Path(storage_path)
        self.quotas: Dict[str, dict] = {}
        self._load()
    
    def _load(self):
        """Carrega quotas do arquivo"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Limpa registros antigos (mais de 1 hora)
                    now = datetime.now()
                    self.quotas = {}
                    for cnpj, info in data.items():
                        consultas_validas = []
                        for timestamp_str in info.get('consultas', []):
                            timestamp = datetime.fromisoformat(timestamp_str)
                            # Mantém apenas consultas da última hora
                            if now - timestamp < timedelta(hours=1):
                                consultas_validas.append(timestamp_str)
                        
                        if consultas_validas:
                            self.quotas[cnpj] = {'consultas': consultas_validas}
            except Exception as e:
                print(f"[QUOTA] Erro ao carregar quotas: {e}")
                self.quotas = {}
    
    def _save(self):
        """Salva quotas no arquivo"""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.quotas, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[QUOTA] Erro ao salvar quotas: {e}")
    
    def registrar_consulta(self, cnpj: str):
        """
        Registra uma consulta realizada
        
        Args:
            cnpj: CNPJ do certificado usado
        """
        now = datetime.now()
        
        if cnpj not in self.quotas:
            self.quotas[cnpj] = {'consultas': []}
        
        # Adiciona timestamp
        self.quotas[cnpj]['consultas'].append(now.isoformat())
        
        # Limpa consultas antigas (mais de 1 hora)
        consultas_validas = []
        for timestamp_str in self.quotas[cnpj]['consultas']:
            timestamp = datetime.fromisoformat(timestamp_str)
            if now - timestamp < timedelta(hours=1):
                consultas_validas.append(timestamp_str)
        
        self.quotas[cnpj]['consultas'] = consultas_validas
        self._save()
    
    def consultas_disponiveis(self, cnpj: str) -> int:
        """
        Retorna quantas consultas ainda podem ser feitas
        
        Args:
            cnpj: CNPJ do certificado
            
        Returns:
            Número de consultas disponíveis (0-20)
        """
        if cnpj not in self.quotas:
            return self.LIMITE_HORA
        
        # Limpa consultas antigas
        now = datetime.now()
        consultas_validas = []
        for timestamp_str in self.quotas[cnpj]['consultas']:
            timestamp = datetime.fromisoformat(timestamp_str)
            if now - timestamp < timedelta(hours=1):
                consultas_validas.append(timestamp_str)
        
        self.quotas[cnpj]['consultas'] = consultas_validas
        
        usadas = len(consultas_validas)
        disponiveis = max(0, self.LIMITE_HORA - usadas)
        
        return disponiveis
    
    def pode_consultar(self, cnpj: str) -> bool:
        """
        Verifica se ainda pode consultar (não atingiu o limite)
        
        Args:
            cnpj: CNPJ do certificado
            
        Returns:
            True se pode consultar, False se atingiu limite
        """
        return self.consultas_disponiveis(cnpj) > 0
    
    def tempo_para_proxima_disponivel(self, cnpj: str) -> Optional[timedelta]:
        """
        Retorna quanto tempo falta para a próxima consulta ficar disponível
        
        Args:
            cnpj: CNPJ do certificado
            
        Returns:
            timedelta até próxima disponível, ou None se já tem disponíveis
        """
        if self.pode_consultar(cnpj):
            return None
        
        if cnpj not in self.quotas or not self.quotas[cnpj]['consultas']:
            return None
        
        # Pega a consulta mais antiga
        oldest_str = min(self.quotas[cnpj]['consultas'])
        oldest = datetime.fromisoformat(oldest_str)
        
        # Ela ficará disponível após 1 hora
        disponivel_em = oldest + timedelta(hours=1)
        now = datetime.now()
        
        if disponivel_em <= now:
            return timedelta(0)
        
        return disponivel_em - now
    
    def get_status_todos_certificados(self, certificados: list) -> dict:
        """
        Retorna status de quota para todos os certificados
        
        Args:
            certificados: Lista de dicts com certificados (deve ter 'cnpj_cpf')
            
        Returns:
            Dict com CNPJ -> {'disponiveis': int, 'usadas': int, 'limite': int}
        """
        status = {}
        for cert in certificados:
            cnpj = cert.get('cnpj_cpf', '')
            if cnpj:
                disponiveis = self.consultas_disponiveis(cnpj)
                usadas = self.LIMITE_HORA - disponiveis
                status[cnpj] = {
                    'disponiveis': disponiveis,
                    'usadas': usadas,
                    'limite': self.LIMITE_HORA,
                    'percentual': (disponiveis / self.LIMITE_HORA) * 100
                }
        
        return status
    
    def reset_certificado(self, cnpj: str):
        """
        Reseta o contador de um certificado (usar apenas para testes)
        
        Args:
            cnpj: CNPJ do certificado
        """
        if cnpj in self.quotas:
            del self.quotas[cnpj]
            self._save()
    
    def reset_todos(self):
        """Reseta todos os contadores (usar apenas para testes)"""
        self.quotas = {}
        self._save()
