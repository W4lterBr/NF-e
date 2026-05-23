#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Exemplo Avançado - Busca em Múltiplos Municípios
=================================================

Este exemplo demonstra como buscar NFS-e em múltiplos municípios
de forma automatizada, usando as configurações armazenadas no banco de dados.

Casos de uso:
-------------
- Empresas que prestam serviços em várias cidades
- Consolidação de NFS-e de diferentes municípios
- Processamento em batch (lote)

"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict

# Adiciona o diretório 'codigo' ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'codigo'))

from nfse_search import NFSeService, NFSeDatabase


class ProcessadorMultiplasNFSe:
    """
    Classe para processar buscas de NFS-e em múltiplos municípios.
    """
    
    def __init__(self, certificado_path: str, senha: str, cnpj: str):
        """
        Inicializa o processador.
        
        Args:
            certificado_path: Caminho para o certificado .pfx
            senha: Senha do certificado
            cnpj: CNPJ do prestador
        """
        self.certificado_path = certificado_path
        self.senha = senha
        self.cnpj = cnpj
        self.db = NFSeDatabase()
        self.service = None
        
        # Estatísticas
        self.stats = {
            'total_municipios': 0,
            'municipios_sucesso': 0,
            'municipios_erro': 0,
            'total_notas': 0,
            'valor_total': 0.0
        }
    
    def inicializar(self):
        """Inicializa o serviço NFS-e"""
        try:
            self.service = NFSeService(
                certificado_path=self.certificado_path,
                senha=self.senha,
                cnpj=self.cnpj
            )
            return True
        except Exception as e:
            print(f"❌ Erro ao inicializar serviço: {e}")
            return False
    
    def obter_configuracoes(self) -> List[tuple]:
        """
        Busca todas as configurações ativas do CNPJ no banco.
        
        Returns:
            Lista de tuplas (provedor, cod_municipio, inscricao_municipal, url)
        """
        configuracoes = self.db.get_config_nfse(self.cnpj)
        return configuracoes
    
    def buscar_municipio(
        self,
        provedor: str,
        cod_municipio: str,
        inscricao_municipal: str,
        url_customizada: str,
        data_inicial: str,
        data_final: str
    ) -> Dict:
        """
        Busca NFS-e de um município específico.
        
        Args:
            provedor: Nome do provedor (GINFES, ISS.NET, etc)
            cod_municipio: Código IBGE do município
            inscricao_municipal: Inscrição municipal do prestador
            url_customizada: URL customizada (opcional)
            data_inicial: Data inicial (DD/MM/YYYY)
            data_final: Data final (DD/MM/YYYY)
        
        Returns:
            Dicionário com resultado da busca
        """
        print(f"  🔍 Município {cod_municipio} ({provedor})...")
        
        try:
            # Seleciona método de busca baseado no provedor
            if provedor.upper() in ['GINFES', 'ISS.NET', 'BETHA', 'EISS', 'WEBISS', 'SIMPLISS']:
                resultado = self.service.buscar_ginfes(
                    cod_municipio=cod_municipio,
                    inscricao_municipal=inscricao_municipal,
                    data_inicial=data_inicial,
                    data_final=data_final,
                    url_customizada=url_customizada
                )
            
            elif provedor.upper() == 'NUVEM_FISCAL':
                # Converte datas para formato ISO
                data_ini_iso = datetime.strptime(data_inicial, "%d/%m/%Y").strftime("%Y-%m-%d")
                data_fim_iso = datetime.strptime(data_final, "%d/%m/%Y").strftime("%Y-%m-%d")
                
                resultado = self.service.buscar_nuvemfiscal(
                    cpf_cnpj=self.cnpj,
                    data_inicial=data_ini_iso,
                    data_final=data_fim_iso,
                    codigo_municipio=cod_municipio
                )
            
            else:
                # Provedor não suportado
                return {
                    'sucesso': False,
                    'mensagem': f'Provedor {provedor} não suportado',
                    'notas': []
                }
            
            return resultado
        
        except Exception as e:
            return {
                'sucesso': False,
                'mensagem': str(e),
                'notas': []
            }
    
    def salvar_notas(self, notas: List[Dict], cod_municipio: str):
        """
        Salva lista de notas no banco de dados.
        
        Args:
            notas: Lista de notas fiscais
            cod_municipio: Código do município
        """
        for nota in notas:
            try:
                self.db.salvar_nfse(
                    numero=nota['numero'],
                    cnpj_prestador=self.cnpj,
                    cnpj_tomador=nota.get('tomador_cnpj'),
                    data_emissao=nota['data_emissao'],
                    valor=nota['valor'],
                    xml_content=nota.get('xml', '')
                )
            except Exception as e:
                print(f"    ⚠️  Erro ao salvar nota {nota['numero']}: {e}")
    
    def processar_todos(self, data_inicial: str, data_final: str, salvar_automatico: bool = True):
        """
        Processa busca de NFS-e em todos os municípios configurados.
        
        Args:
            data_inicial: Data inicial (DD/MM/YYYY)
            data_final: Data final (DD/MM/YYYY)
            salvar_automatico: Se True, salva automaticamente no banco
        """
        print("=" * 70)
        print("  PROCESSAMENTO EM MÚLTIPLOS MUNICÍPIOS")
        print("=" * 70)
        print()
        
        # Obtém configurações
        configuracoes = self.obter_configuracoes()
        
        if not configuracoes:
            print(f"❌ Nenhuma configuração encontrada para CNPJ {self.cnpj}")
            return
        
        self.stats['total_municipios'] = len(configuracoes)
        
        print(f"📋 {len(configuracoes)} municípios configurados")
        print(f"📅 Período: {data_inicial} até {data_final}")
        print()
        
        # Processa cada município
        for i, (provedor, cod_municipio, inscricao_municipal, url) in enumerate(configuracoes, 1):
            print(f"[{i}/{len(configuracoes)}] ", end="")
            
            resultado = self.buscar_municipio(
                provedor=provedor,
                cod_municipio=cod_municipio,
                inscricao_municipal=inscricao_municipal,
                url_customizada=url,
                data_inicial=data_inicial,
                data_final=data_final
            )
            
            if resultado['sucesso']:
                notas = resultado['notas']
                qtd_notas = len(notas)
                valor_municipio = sum(float(n['valor']) for n in notas)
                
                print(f"    ✅ {qtd_notas} notas - R$ {valor_municipio:,.2f}")
                
                # Atualiza estatísticas
                self.stats['municipios_sucesso'] += 1
                self.stats['total_notas'] += qtd_notas
                self.stats['valor_total'] += valor_municipio
                
                # Salva no banco
                if salvar_automatico and qtd_notas > 0:
                    self.salvar_notas(notas, cod_municipio)
                    print(f"    💾 Salvas no banco de dados")
            
            else:
                print(f"    ❌ Erro: {resultado['mensagem']}")
                self.stats['municipios_erro'] += 1
            
            print()
        
        # Exibe resumo final
        self.exibir_resumo()
    
    def exibir_resumo(self):
        """Exibe resumo estatístico do processamento"""
        print("=" * 70)
        print("  RESUMO DO PROCESSAMENTO")
        print("=" * 70)
        print()
        print(f"📊 Total de municípios processados: {self.stats['total_municipios']}")
        print(f"   ✅ Sucesso: {self.stats['municipios_sucesso']}")
        print(f"   ❌ Erro: {self.stats['municipios_erro']}")
        print()
        print(f"📄 Total de NFS-e encontradas: {self.stats['total_notas']}")
        print(f"💰 Valor total: R$ {self.stats['valor_total']:,.2f}")
        print()
        print("=" * 70)


def main():
    """Função principal"""
    
    # =========================================================================
    # CONFIGURAÇÃO
    # =========================================================================
    
    CERTIFICADO_PATH = "caminho/para/certificado.pfx"
    CERTIFICADO_SENHA = "senha_do_certificado"
    CNPJ_PRESTADOR = "12345678000199"
    
    # Período: últimos 30 dias
    data_final = datetime.now()
    data_inicial = data_final - timedelta(days=30)
    data_ini_str = data_inicial.strftime("%d/%m/%Y")
    data_fim_str = data_final.strftime("%d/%m/%Y")
    
    # =========================================================================
    # VALIDAÇÃO
    # =========================================================================
    
    if not os.path.exists(CERTIFICADO_PATH):
        print(f"❌ Certificado não encontrado: {CERTIFICADO_PATH}")
        print()
        print("Ajuste a variável CERTIFICADO_PATH no código.")
        return 1
    
    # =========================================================================
    # PROCESSAMENTO
    # =========================================================================
    
    processador = ProcessadorMultiplasNFSe(
        certificado_path=CERTIFICADO_PATH,
        senha=CERTIFICADO_SENHA,
        cnpj=CNPJ_PRESTADOR
    )
    
    # Inicializa serviço
    if not processador.inicializar():
        return 1
    
    # Processa todos os municípios
    processador.processar_todos(
        data_inicial=data_ini_str,
        data_final=data_fim_str,
        salvar_automatico=True
    )
    
    return 0


def exemplo_processamento_mensal():
    """
    Exemplo adicional: Processar NFS-e de cada mês do ano
    """
    print()
    print("📅 Processamento Mensal - Ano Completo")
    print()
    
    CERTIFICADO_PATH = "caminho/para/certificado.pfx"
    CERTIFICADO_SENHA = "senha_do_certificado"
    CNPJ_PRESTADOR = "12345678000199"
    
    processador = ProcessadorMultiplasNFSe(
        certificado_path=CERTIFICADO_PATH,
        senha=CERTIFICADO_SENHA,
        cnpj=CNPJ_PRESTADOR
    )
    
    if not processador.inicializar():
        return
    
    # Processa cada mês de 2025
    ano = 2025
    for mes in range(1, 13):
        print(f"\n{'='*70}")
        print(f"  MÊS {mes:02d}/{ano}")
        print(f"{'='*70}\n")
        
        # Primeiro e último dia do mês
        data_inicial = datetime(ano, mes, 1)
        
        if mes == 12:
            data_final = datetime(ano, mes, 31)
        else:
            data_final = datetime(ano, mes + 1, 1) - timedelta(days=1)
        
        # Processa
        processador.processar_todos(
            data_inicial=data_inicial.strftime("%d/%m/%Y"),
            data_final=data_final.strftime("%d/%m/%Y"),
            salvar_automatico=True
        )


if __name__ == '__main__':
    # Executa exemplo principal
    exit_code = main()
    
    # Exemplo adicional: processamento mensal (descomente se desejar)
    # exemplo_processamento_mensal()
    
    sys.exit(exit_code)
