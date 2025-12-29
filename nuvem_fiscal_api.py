#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integração com Nuvem Fiscal API para consulta de NFS-e

Documentação: https://dev.nuvemfiscal.com.br/
"""
import requests
import json
import csv
from datetime import datetime
from pathlib import Path

class NuvemFiscalAPI:
    """Cliente para API Nuvem Fiscal"""
    
    def __init__(self, client_id=None, client_secret=None):
        """
        Inicializa cliente da API
        
        Args:
            client_id: Client ID da API (opcional, lê do CSV se não fornecido)
            client_secret: Client Secret da API (opcional, lê do CSV se não fornecido)
        """
        if client_id and client_secret:
            self.client_id = client_id
            self.client_secret = client_secret
        else:
            self._load_credentials()
        
        self.base_url = "https://api.nuvemfiscal.com.br"
        self.auth_url = "https://auth.nuvemfiscal.com.br/oauth/token"
        self.access_token = None
        self.token_expires_at = None
    
    def _load_credentials(self):
        """Carrega credenciais do arquivo CSV"""
        csv_path = Path(__file__).parent / "api_credentials.csv"
        
        if not csv_path.exists():
            raise FileNotFoundError(f"Arquivo de credenciais não encontrado: {csv_path}")
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row = next(reader)
            self.client_id = row['Client ID']
            self.client_secret = row['Client Secret']
        
        print(f"✅ Credenciais carregadas: Client ID {self.client_id[:10]}...")
    
    def authenticate(self):
        """
        Autentica na API e obtém access token
        
        Returns:
            str: Access token
        """
        url = self.auth_url
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        # Escopos necessários para NFS-e
        scopes = 'empresa cep cnpj nfse nfe nfce cte mdfe'
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': scopes
        }
        
        print(f"🔐 Autenticando na API Nuvem Fiscal...")
        print(f"   URL: {url}")
        print(f"   Escopos: {scopes}")
        
        response = requests.post(url, headers=headers, data=data, timeout=30)
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 3600)
            
            from datetime import datetime, timedelta
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            print(f"✅ Autenticado com sucesso!")
            print(f"   Token válido até: {self.token_expires_at.strftime('%d/%m/%Y %H:%M:%S')}")
            
            return self.access_token
        else:
            raise Exception(f"Erro na autenticação: {response.status_code} - {response.text}")
    
    def _ensure_authenticated(self):
        """Garante que há um token válido"""
        if not self.access_token or (self.token_expires_at and datetime.now() >= self.token_expires_at):
            self.authenticate()
    
    def consultar_nfse(self, cpf_cnpj, data_inicial=None, data_final=None, 
                       codigo_municipio=None, ambiente='producao', top=50, skip=0):
        """
        Consulta NFS-e emitidas
        
        Args:
            cpf_cnpj: CPF/CNPJ do prestador
            data_inicial: Data inicial (YYYY-MM-DD ou datetime)
            data_final: Data final (YYYY-MM-DD ou datetime)
            codigo_municipio: Código IBGE do município (7 dígitos)
            ambiente: 'producao' ou 'homologacao'
            top: Número máximo de registros (padrão 50)
            skip: Número de registros a pular (paginação)
        
        Returns:
            dict: Resposta da API com lista de NFS-e
        """
        self._ensure_authenticated()
        
        url = f"{self.base_url}/nfse"
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }
        
        # Formatar datas
        if isinstance(data_inicial, datetime):
            data_inicial = data_inicial.strftime('%Y-%m-%d')
        if isinstance(data_final, datetime):
            data_final = data_final.strftime('%Y-%m-%d')
        
        # Montar parâmetros
        params = {
            '$top': top,
            '$skip': skip
        }
        
        if cpf_cnpj:
            params['cpf_cnpj'] = cpf_cnpj.replace('.', '').replace('-', '').replace('/', '')
        
        if data_inicial:
            params['data_emissao_inicio'] = data_inicial
        
        if data_final:
            params['data_emissao_fim'] = data_final
        
        if codigo_municipio:
            params['codigo_municipio'] = codigo_municipio
        
        if ambiente:
            params['ambiente'] = ambiente
        
        print(f"\n🔍 Consultando NFS-e na Nuvem Fiscal...")
        print(f"   CPF/CNPJ: {cpf_cnpj}")
        if data_inicial and data_final:
            print(f"   Período: {data_inicial} a {data_final}")
        if codigo_municipio:
            print(f"   Município: {codigo_municipio}")
        print(f"   Ambiente: {ambiente}")
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            total = data.get('count', 0)
            notas = data.get('data', [])
            
            print(f"✅ Consulta realizada com sucesso!")
            print(f"   Total de registros: {total}")
            print(f"   Retornados nesta página: {len(notas)}")
            
            return data
        else:
            raise Exception(f"Erro na consulta: {response.status_code} - {response.text}")
    
    def baixar_xml_nfse(self, nfse_id):
        """
        Baixa XML de uma NFS-e específica
        
        Args:
            nfse_id: ID da NFS-e na Nuvem Fiscal
        
        Returns:
            str: Conteúdo XML da NFS-e
        """
        self._ensure_authenticated()
        
        url = f"{self.base_url}/nfse/{nfse_id}/xml"
        
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return response.text
        else:
            raise Exception(f"Erro ao baixar XML: {response.status_code} - {response.text}")
    
    def consultar_nfse_numero(self, numero, codigo_municipio, cpf_cnpj_prestador=None):
        """
        Consulta NFS-e por número
        
        Args:
            numero: Número da NFS-e
            codigo_municipio: Código IBGE do município
            cpf_cnpj_prestador: CPF/CNPJ do prestador (opcional)
        
        Returns:
            dict: Dados da NFS-e
        """
        self._ensure_authenticated()
        
        url = f"{self.base_url}/nfse"
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }
        
        params = {
            'numero': numero,
            'codigo_municipio': codigo_municipio
        }
        
        if cpf_cnpj_prestador:
            params['cpf_cnpj_prestador'] = cpf_cnpj_prestador.replace('.', '').replace('-', '').replace('/', '')
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Erro na consulta: {response.status_code} - {response.text}")


# Teste rápido
if __name__ == "__main__":
    try:
        # Criar cliente
        api = NuvemFiscalAPI()
        
        # Autenticar
        api.authenticate()
        
        # Consultar NFS-e (exemplo com Campo Grande)
        print("\n" + "="*80)
        print("TESTE DE CONSULTA NFS-e")
        print("="*80)
        
        resultado = api.consultar_nfse(
            cpf_cnpj="33251845000109",
            data_inicial="2025-05-01",
            data_final="2025-12-18",
            codigo_municipio="5002704",
            ambiente="producao",
            top=10
        )
        
        print(f"\n📊 Resultado:")
        print(f"   Total: {resultado.get('count', 0)}")
        
        notas = resultado.get('data', [])
        if notas:
            print(f"\n📄 NFS-e encontradas:")
            for nota in notas[:5]:  # Primeiras 5
                numero = nota.get('numero', 'N/A')
                data_emissao = nota.get('data_emissao', 'N/A')
                valor = nota.get('valor_servicos', 0)
                tomador = nota.get('tomador', {}).get('razao_social', 'N/A')
                print(f"      • NFS-e {numero} - {data_emissao} - R$ {valor:.2f}")
                print(f"        Tomador: {tomador}")
        else:
            print("\nℹ️  Nenhuma NFS-e encontrada no período")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
