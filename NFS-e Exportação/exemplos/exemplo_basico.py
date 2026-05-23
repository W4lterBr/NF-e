#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Exemplo Básico - Busca de NFS-e
================================

Este exemplo demonstra como usar o módulo nfse_search para realizar
uma busca simples de NFS-e em um município específico.

Requisitos:
-----------
- Certificado digital A1 (.pfx) com senha
- CNPJ do prestador
- Inscrição municipal configurada
- Código do município (IBGE - 7 dígitos)

"""

import sys
import os
from datetime import datetime, timedelta

# Adiciona o diretório 'codigo' ao path para importar nfse_search
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'codigo'))

from nfse_search import NFSeService, NFSeDatabase


def main():
    """Exemplo básico de busca de NFS-e"""
    
    print("=" * 60)
    print("  EXEMPLO BÁSICO - BUSCA DE NFS-e")
    print("=" * 60)
    print()
    
    # =========================================================================
    # CONFIGURAÇÃO
    # =========================================================================
    
    # Caminho para o certificado digital A1 (.pfx)
    CERTIFICADO_PATH = "caminho/para/certificado.pfx"
    CERTIFICADO_SENHA = "senha_do_certificado"
    
    # Dados do prestador
    CNPJ_PRESTADOR = "12345678000199"
    INSCRICAO_MUNICIPAL = "12345"
    
    # Código do município (IBGE - 7 dígitos)
    # Exemplo: 5002704 = Campo Grande/MS
    CODIGO_MUNICIPIO = "5002704"
    
    # Período de busca (últimos 30 dias)
    data_final = datetime.now()
    data_inicial = data_final - timedelta(days=30)
    
    data_ini_str = data_inicial.strftime("%d/%m/%Y")
    data_fim_str = data_final.strftime("%d/%m/%Y")
    
    # =========================================================================
    # VALIDAÇÃO
    # =========================================================================
    
    if not os.path.exists(CERTIFICADO_PATH):
        print(f"❌ ERRO: Certificado não encontrado em: {CERTIFICADO_PATH}")
        print()
        print("Por favor, ajuste a variável CERTIFICADO_PATH com o caminho correto.")
        return 1
    
    print(f"📄 Certificado: {CERTIFICADO_PATH}")
    print(f"🏢 CNPJ Prestador: {CNPJ_PRESTADOR}")
    print(f"🏛️  Inscrição Municipal: {INSCRICAO_MUNICIPAL}")
    print(f"📍 Município: {CODIGO_MUNICIPIO}")
    print(f"📅 Período: {data_ini_str} até {data_fim_str}")
    print()
    
    # =========================================================================
    # INICIALIZAÇÃO DO SERVIÇO
    # =========================================================================
    
    try:
        print("🔧 Inicializando serviço NFS-e...")
        service = NFSeService(
            certificado_path=CERTIFICADO_PATH,
            senha=CERTIFICADO_SENHA,
            cnpj=CNPJ_PRESTADOR
        )
        print("✅ Serviço inicializado com sucesso!")
        print()
    except Exception as e:
        print(f"❌ ERRO ao inicializar serviço: {e}")
        return 1
    
    # =========================================================================
    # BUSCA DE NFS-e (GINFES)
    # =========================================================================
    
    print("🔍 Buscando NFS-e no provedor GINFES...")
    print()
    
    try:
        resultado = service.buscar_ginfes(
            cod_municipio=CODIGO_MUNICIPIO,
            inscricao_municipal=INSCRICAO_MUNICIPAL,
            data_inicial=data_ini_str,
            data_final=data_fim_str
        )
        
        # Verifica se houve sucesso
        if resultado['sucesso']:
            notas = resultado['notas']
            print(f"✅ Busca concluída com sucesso!")
            print(f"📊 Total de NFS-e encontradas: {len(notas)}")
            print()
            
            if len(notas) > 0:
                # =====================================================
                # EXIBIR RESULTADOS
                # =====================================================
                print("-" * 60)
                print("  NOTAS FISCAIS ENCONTRADAS")
                print("-" * 60)
                print()
                
                total_valor = 0
                
                for i, nota in enumerate(notas, 1):
                    numero = nota.get('numero', 'N/A')
                    data_emissao = nota.get('data_emissao', 'N/A')
                    valor = nota.get('valor', 0)
                    tomador_cnpj = nota.get('tomador_cnpj', 'N/A')
                    tomador_nome = nota.get('tomador_nome', 'N/A')
                    
                    print(f"📄 Nota #{i}")
                    print(f"   Número: {numero}")
                    print(f"   Data Emissão: {data_emissao}")
                    print(f"   Valor: R$ {valor:,.2f}")
                    print(f"   Tomador: {tomador_nome} ({tomador_cnpj})")
                    print()
                    
                    total_valor += float(valor)
                
                print("-" * 60)
                print(f"   VALOR TOTAL: R$ {total_valor:,.2f}")
                print("-" * 60)
                print()
                
                # =====================================================
                # SALVAR NO BANCO DE DADOS (OPCIONAL)
                # =====================================================
                
                salvar = input("💾 Deseja salvar as notas no banco de dados? (s/n): ")
                
                if salvar.lower() == 's':
                    try:
                        db = NFSeDatabase()
                        
                        for nota in notas:
                            db.salvar_nfse(
                                numero=nota['numero'],
                                cnpj_prestador=CNPJ_PRESTADOR,
                                cnpj_tomador=nota.get('tomador_cnpj'),
                                data_emissao=nota['data_emissao'],
                                valor=nota['valor'],
                                xml_content=nota.get('xml', '')
                            )
                        
                        print(f"✅ {len(notas)} notas salvas no banco de dados!")
                        print()
                    
                    except Exception as e:
                        print(f"❌ ERRO ao salvar no banco: {e}")
                        print()
            
            else:
                print("ℹ️  Nenhuma NFS-e encontrada no período especificado.")
                print()
        
        else:
            # Erro na busca
            print(f"❌ ERRO na busca: {resultado['mensagem']}")
            print()
            
            if 'detalhes' in resultado:
                print("Detalhes:")
                print(resultado['detalhes'])
                print()
    
    except Exception as e:
        print(f"❌ ERRO durante a busca: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # =========================================================================
    # FINALIZAÇÃO
    # =========================================================================
    
    print("=" * 60)
    print("  FIM DO EXEMPLO")
    print("=" * 60)
    
    return 0


def exemplo_consulta_banco():
    """
    Exemplo adicional: Consultar NFS-e salvas no banco de dados
    """
    print()
    print("📊 Consultando NFS-e no banco de dados...")
    print()
    
    try:
        db = NFSeDatabase()
        
        # Busca todas as NFS-e de um prestador
        cnpj = "12345678000199"
        
        # Usando SQL direto (exemplo)
        query = """
            SELECT numero_nfse, data_emissao, valor_servico, cnpj_tomador
            FROM nfse_baixadas
            WHERE cnpj_prestador = ?
            ORDER BY data_emissao DESC
            LIMIT 10
        """
        
        cursor = db.conn.cursor()
        cursor.execute(query, (cnpj,))
        
        notas = cursor.fetchall()
        
        if notas:
            print(f"✅ {len(notas)} notas encontradas no banco:")
            print()
            
            for numero, data, valor, tomador in notas:
                print(f"  • Nota {numero} - {data} - R$ {valor:,.2f} - Tomador: {tomador}")
            
            print()
        else:
            print("ℹ️  Nenhuma nota encontrada no banco de dados.")
            print()
    
    except Exception as e:
        print(f"❌ ERRO ao consultar banco: {e}")


if __name__ == '__main__':
    # Executa exemplo principal
    exit_code = main()
    
    # Exemplo adicional: consultar banco (descomente se desejar)
    # exemplo_consulta_banco()
    
    sys.exit(exit_code)
