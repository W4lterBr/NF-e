#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Exemplo REST API - Nuvem Fiscal
================================

Este exemplo demonstra como buscar NFS-e usando a API REST da Nuvem Fiscal,
que é um agregador de NFS-e de múltiplos provedores.

Vantagens da Nuvem Fiscal:
--------------------------
- ✅ API REST moderna (sem SOAP)
- ✅ OAuth2 (não precisa de certificado A1)
- ✅ Cobertura de múltiplos provedores em uma única API
- ✅ Documentação completa e SDKs disponíveis
- ✅ Suporte a webhooks para notificações

Desvantagens:
-------------
- ❌ Serviço pago (assinatura mensal)
- ❌ Requer cadastro e credenciais OAuth2
- ❌ Não cobre 100% dos municípios (ainda em expansão)

Documentação: https://dev.nuvemfiscal.com.br/

"""

import sys
import os
from datetime import datetime, timedelta
import requests
from typing import Dict, List, Optional

# Adiciona o diretório 'codigo' ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'codigo'))

from nfse_search import NFSeDatabase


class NuvemFiscalAPI:
    """
    Cliente para a API REST da Nuvem Fiscal.
    """
    
    BASE_URL = "https://api.nuvemfiscal.com.br"
    
    def __init__(self, client_id: str, client_secret: str):
        """
        Inicializa o cliente da API.
        
        Args:
            client_id: Client ID do OAuth2
            client_secret: Client Secret do OAuth2
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expires_at = None
    
    def autenticar(self) -> bool:
        """
        Realiza autenticação OAuth2 e obtém access token.
        
        Returns:
            True se autenticação foi bem-sucedida
        """
        print("🔐 Autenticando na API Nuvem Fiscal...")
        
        url = f"{self.BASE_URL}/oauth/token"
        
        payload = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'nfse.read'
        }
        
        try:
            response = requests.post(url, data=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            self.access_token = data['access_token']
            
            # Token geralmente expira em 3600 segundos (1 hora)
            expires_in = data.get('expires_in', 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            print(f"✅ Autenticação bem-sucedida! Token válido por {expires_in} segundos.")
            return True
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro na autenticação: {e}")
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Retorna headers HTTP com Authorization.
        """
        # Renova token se necessário
        if not self.access_token or datetime.now() >= self.token_expires_at:
            self.autenticar()
        
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def buscar_nfse(
        self,
        cpf_cnpj: str,
        data_inicial: str,
        data_final: str,
        codigo_municipio: Optional[str] = None,
        top: int = 50,
        skip: int = 0
    ) -> Dict:
        """
        Busca NFS-e via API REST.
        
        Args:
            cpf_cnpj: CPF/CNPJ do prestador ou tomador
            data_inicial: Data inicial (YYYY-MM-DD)
            data_final: Data final (YYYY-MM-DD)
            codigo_municipio: Código IBGE do município (opcional)
            top: Quantidade de registros por página (padrão: 50)
            skip: Registros a pular (paginação)
        
        Returns:
            Dicionário com resultado da busca
        """
        print(f"🔍 Buscando NFS-e de {cpf_cnpj} no período {data_inicial} a {data_final}...")
        
        url = f"{self.BASE_URL}/nfse"
        
        params = {
            'cpf_cnpj': cpf_cnpj,
            'data_inicial': data_inicial,
            'data_final': data_final,
            '$top': top,
            '$skip': skip
        }
        
        if codigo_municipio:
            params['codigo_municipio'] = codigo_municipio
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=60
            )
            
            response.raise_for_status()
            
            data = response.json()
            
            # Formata resultado
            notas = []
            for item in data.get('data', []):
                notas.append({
                    'numero': item.get('numero'),
                    'data_emissao': item.get('data_emissao'),
                    'valor': item.get('valor_servico'),
                    'tomador_cnpj': item.get('tomador', {}).get('cpf_cnpj'),
                    'tomador_nome': item.get('tomador', {}).get('nome'),
                    'prestador_cnpj': item.get('prestador', {}).get('cpf_cnpj'),
                    'codigo_municipio': item.get('codigo_municipio'),
                    'codigo_verificacao': item.get('codigo_verificacao'),
                    'situacao': item.get('situacao'),
                    'xml': item.get('xml')
                })
            
            total = data.get('count', len(notas))
            
            print(f"✅ {len(notas)} notas encontradas (total: {total})")
            
            return {
                'sucesso': True,
                'notas': notas,
                'total': total,
                'pagina': {
                    'skip': skip,
                    'top': top
                }
            }
        
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            
            if status_code == 401:
                mensagem = "Não autorizado. Verifique credenciais OAuth2."
            elif status_code == 403:
                mensagem = "Acesso proibido. Verifique permissões do OAuth2."
            elif status_code == 429:
                mensagem = "Limite de requisições excedido. Aguarde e tente novamente."
            else:
                mensagem = f"Erro HTTP {status_code}: {e.response.text}"
            
            print(f"❌ {mensagem}")
            
            return {
                'sucesso': False,
                'mensagem': mensagem,
                'notas': []
            }
        
        except Exception as e:
            print(f"❌ Erro na busca: {e}")
            
            return {
                'sucesso': False,
                'mensagem': str(e),
                'notas': []
            }
    
    def buscar_todas_paginas(
        self,
        cpf_cnpj: str,
        data_inicial: str,
        data_final: str,
        codigo_municipio: Optional[str] = None,
        por_pagina: int = 50
    ) -> List[Dict]:
        """
        Busca todas as NFS-e paginando automaticamente.
        
        Args:
            cpf_cnpj: CPF/CNPJ
            data_inicial: Data inicial (YYYY-MM-DD)
            data_final: Data final (YYYY-MM-DD)
            codigo_municipio: Código do município (opcional)
            por_pagina: Quantidade de registros por página
        
        Returns:
            Lista completa de notas fiscais
        """
        todas_notas = []
        skip = 0
        
        while True:
            resultado = self.buscar_nfse(
                cpf_cnpj=cpf_cnpj,
                data_inicial=data_inicial,
                data_final=data_final,
                codigo_municipio=codigo_municipio,
                top=por_pagina,
                skip=skip
            )
            
            if not resultado['sucesso']:
                break
            
            notas = resultado['notas']
            
            if not notas:
                break
            
            todas_notas.extend(notas)
            
            # Verifica se há mais páginas
            if len(notas) < por_pagina:
                break
            
            skip += por_pagina
            print(f"  📄 Página {skip // por_pagina}... ({len(todas_notas)} notas até agora)")
        
        return todas_notas
    
    def baixar_xml(self, numero_nfse: str, codigo_verificacao: str) -> Optional[str]:
        """
        Baixa o XML completo de uma NFS-e específica.
        
        Args:
            numero_nfse: Número da NFS-e
            codigo_verificacao: Código de verificação
        
        Returns:
            String com conteúdo XML ou None se erro
        """
        url = f"{self.BASE_URL}/nfse/{numero_nfse}/xml"
        
        params = {
            'codigo_verificacao': codigo_verificacao
        }
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=30
            )
            
            response.raise_for_status()
            
            return response.text
        
        except Exception as e:
            print(f"❌ Erro ao baixar XML: {e}")
            return None


def main():
    """Função principal"""
    
    print("=" * 70)
    print("  EXEMPLO - API REST NUVEM FISCAL")
    print("=" * 70)
    print()
    
    # =========================================================================
    # CONFIGURAÇÃO
    # =========================================================================
    
    # Credenciais OAuth2 (obtenha em https://app.nuvemfiscal.com.br/)
    CLIENT_ID = "seu_client_id_aqui"
    CLIENT_SECRET = "seu_client_secret_aqui"
    
    # Dados da busca
    CPF_CNPJ = "12345678000199"
    
    # Período: últimos 30 dias
    data_final = datetime.now()
    data_inicial = data_final - timedelta(days=30)
    data_ini_str = data_inicial.strftime("%Y-%m-%d")
    data_fim_str = data_final.strftime("%Y-%m-%d")
    
    # Município específico (opcional)
    CODIGO_MUNICIPIO = "5002704"  # Campo Grande/MS
    
    # =========================================================================
    # VALIDAÇÃO
    # =========================================================================
    
    if CLIENT_ID == "seu_client_id_aqui" or CLIENT_SECRET == "seu_client_secret_aqui":
        print("⚠️  ATENÇÃO: Você precisa configurar CLIENT_ID e CLIENT_SECRET!")
        print()
        print("1. Acesse: https://app.nuvemfiscal.com.br/")
        print("2. Crie uma conta ou faça login")
        print("3. Vá em Configurações > API > OAuth2")
        print("4. Crie um novo Client ID e Secret")
        print("5. Atualize as variáveis no código")
        print()
        return 1
    
    # =========================================================================
    # BUSCA VIA API REST
    # =========================================================================
    
    api = NuvemFiscalAPI(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    
    # Autentica
    if not api.autenticar():
        return 1
    
    print()
    
    # Busca todas as páginas
    notas = api.buscar_todas_paginas(
        cpf_cnpj=CPF_CNPJ,
        data_inicial=data_ini_str,
        data_final=data_fim_str,
        codigo_municipio=CODIGO_MUNICIPIO
    )
    
    print()
    print("-" * 70)
    print(f"  RESULTADO: {len(notas)} NFS-e encontradas")
    print("-" * 70)
    print()
    
    if notas:
        # Exibe primeiras 10 notas
        for i, nota in enumerate(notas[:10], 1):
            print(f"📄 Nota {i}:")
            print(f"   Número: {nota['numero']}")
            print(f"   Data: {nota['data_emissao']}")
            print(f"   Valor: R$ {nota['valor']:,.2f}")
            print(f"   Tomador: {nota['tomador_nome']} ({nota['tomador_cnpj']})")
            print(f"   Município: {nota['codigo_municipio']}")
            print(f"   Situação: {nota['situacao']}")
            print()
        
        if len(notas) > 10:
            print(f"   ... e mais {len(notas) - 10} notas")
            print()
        
        # =====================================================================
        # SALVAR NO BANCO
        # =====================================================================
        
        salvar = input("💾 Salvar notas no banco de dados? (s/n): ")
        
        if salvar.lower() == 's':
            db = NFSeDatabase()
            
            for nota in notas:
                try:
                    db.salvar_nfse(
                        numero=nota['numero'],
                        cnpj_prestador=nota['prestador_cnpj'],
                        cnpj_tomador=nota['tomador_cnpj'],
                        data_emissao=nota['data_emissao'],
                        valor=nota['valor'],
                        xml_content=nota.get('xml', '')
                    )
                except Exception as e:
                    print(f"⚠️  Erro ao salvar nota {nota['numero']}: {e}")
            
            print(f"✅ {len(notas)} notas salvas!")
            print()
    
    else:
        print("ℹ️  Nenhuma NFS-e encontrada no período.")
        print()
    
    print("=" * 70)
    
    return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
