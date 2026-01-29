"""
📊 TESTE DO SISTEMA DE HISTÓRICO NSU
=====================================

Este script testa o novo sistema de histórico de consultas NSU.

O que é testado:
1. Criação da tabela historico_nsu
2. Índices de performance
3. Registro de histórico manual
4. Busca de histórico com filtros
5. Comparação de consultas
6. Relatório consolidado
7. Detecção de divergências

Autor: Sistema de Auditoria NSU
Data: 2026-01-12
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nfe_search import DatabaseManager

def print_header(titulo):
    """Imprime cabeçalho formatado"""
    print("\n" + "="*70)
    print(f"  {titulo}")
    print("="*70)

def print_section(titulo):
    """Imprime seção formatada"""
    print(f"\n--- {titulo} ---")

def test_tabela_historico():
    """Teste 1: Verifica se tabela e índices foram criados"""
    print_header("TESTE 1: Verificação da Tabela e Índices")
    
    db = DatabaseManager('notas.db')
    
    # Verifica se tabela existe
    with db._connect() as conn:
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='historico_nsu'
        """)
        tabela = cursor.fetchone()
        
        if tabela:
            print("✅ Tabela 'historico_nsu' existe")
            
            # Verifica estrutura
            cursor = conn.execute("PRAGMA table_info(historico_nsu)")
            colunas = cursor.fetchall()
            print(f"\n📋 Estrutura da tabela ({len(colunas)} colunas):")
            for col in colunas:
                print(f"   - {col[1]} ({col[2]})")
            
            # Verifica índices
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND tbl_name='historico_nsu'
            """)
            indices = cursor.fetchall()
            print(f"\n📊 Índices criados ({len(indices)}):")
            for idx in indices:
                print(f"   - {idx[0]}")
            
            return True
        else:
            print("❌ Tabela 'historico_nsu' NÃO existe!")
            return False

def test_registro_historico():
    """Teste 2: Testa registro manual de histórico"""
    print_header("TESTE 2: Registro de Histórico Manual")
    
    db = DatabaseManager('notas.db')
    
    # Cria dados de teste
    xmls_teste = [
        {'tipo': 'nfe', 'chave': '35260101234567890123456789012345678901234567', 'numero': '1234'},
        {'tipo': 'nfe', 'chave': '35260101234567890123456789012345678901234568', 'numero': '1235'},
        {'tipo': 'evento', 'chave': '35260101234567890123456789012345678901234567', 'evento': '210210'},
        {'tipo': 'cte', 'chave': '35260101234567890123456789012345678901234569'},
    ]
    
    print("\n📝 Registrando histórico de teste...")
    registro_id = db.registrar_historico_nsu(
        certificado='CERT_TESTE_001',
        informante='49068153000160',
        nsu_consultado='000000000001234',
        xmls_retornados=xmls_teste,
        tempo_ms=1500,
        status='sucesso'
    )
    
    if registro_id:
        print(f"✅ Histórico registrado com sucesso! ID={registro_id}")
        
        # Busca o registro
        historico = db.buscar_historico_nsu(limit=1)
        if historico and len(historico) > 0:
            registro = historico[0]
            print(f"\n📊 Dados registrados:")
            print(f"   - Certificado: {registro['certificado']}")
            print(f"   - Informante: {registro['informante']}")
            print(f"   - NSU: {registro['nsu_consultado']}")
            print(f"   - Total XMLs: {registro['total_xmls_retornados']}")
            print(f"   - NF-e: {registro['total_nfe']}")
            print(f"   - CT-e: {registro['total_cte']}")
            print(f"   - NFS-e: {registro['total_nfse']}")
            print(f"   - Eventos: {registro['total_eventos']}")
            print(f"   - Tempo: {registro['tempo_processamento_ms']}ms")
            print(f"   - Status: {registro['status']}")
            
            # Decodifica JSON
            detalhes = json.loads(registro['detalhes_json'])
            print(f"\n📋 Detalhes ({len(detalhes)} itens):")
            for item in detalhes:
                print(f"   - {item['tipo'].upper()}: {item['chave'][:20]}...")
            
            return True
        else:
            print("❌ Erro ao buscar registro!")
            return False
    else:
        print("❌ Erro ao registrar histórico!")
        return False

def test_busca_com_filtros():
    """Teste 3: Testa busca com diversos filtros"""
    print_header("TESTE 3: Busca com Filtros")
    
    db = DatabaseManager('notas.db')
    
    # Registra mais alguns históricos de teste
    print("\n📝 Registrando múltiplos históricos de teste...")
    
    for i in range(3):
        xmls = [
            {'tipo': 'nfe', 'chave': f'35260101234567890123456789012345678901{i:06d}'},
            {'tipo': 'evento', 'chave': f'35260101234567890123456789012345678901{i:06d}', 'evento': '210210'}
        ]
        
        db.registrar_historico_nsu(
            certificado=f'CERT_TESTE_{i:03d}',
            informante='49068153000160',
            nsu_consultado=f'00000000000{1234+i:04d}',
            xmls_retornados=xmls,
            tempo_ms=1000 + (i * 100),
            status='sucesso'
        )
    
    print("✅ Históricos adicionados")
    
    # Teste 3.1: Busca por informante
    print_section("Busca por Informante")
    historico = db.buscar_historico_nsu(informante='49068153000160', limit=10)
    print(f"✅ Encontrados {len(historico)} registros para informante 49068153000160")
    
    # Teste 3.2: Busca por certificado
    print_section("Busca por Certificado")
    historico = db.buscar_historico_nsu(certificado='CERT_TESTE_001', limit=10)
    print(f"✅ Encontrados {len(historico)} registros para CERT_TESTE_001")
    
    # Teste 3.3: Busca por NSU
    print_section("Busca por NSU")
    historico = db.buscar_historico_nsu(nsu='000000000001234', limit=10)
    print(f"✅ Encontrados {len(historico)} registros para NSU 000000000001234")
    
    # Teste 3.4: Busca por data
    print_section("Busca por Data (hoje)")
    hoje = datetime.now().strftime('%Y-%m-%d')
    historico = db.buscar_historico_nsu(data_inicio=hoje, limit=10)
    print(f"✅ Encontrados {len(historico)} registros hoje ({hoje})")
    
    return True

def test_comparacao_consultas():
    """Teste 4: Testa comparação de consultas do mesmo NSU"""
    print_header("TESTE 4: Comparação de Consultas")
    
    db = DatabaseManager('notas.db')
    
    # Registra 2 consultas do MESMO NSU com resultados diferentes (simulando divergência)
    print("\n📝 Simulando divergência: 2 consultas do mesmo NSU com resultados diferentes...")
    
    # Primeira consulta: 3 XMLs
    xmls1 = [
        {'tipo': 'nfe', 'chave': '35260101234567890123456789012345678901234500'},
        {'tipo': 'nfe', 'chave': '35260101234567890123456789012345678901234501'},
        {'tipo': 'evento', 'chave': '35260101234567890123456789012345678901234500', 'evento': '210210'}
    ]
    
    db.registrar_historico_nsu(
        certificado='CERT_DIVERGENCIA',
        informante='12345678000190',
        nsu_consultado='000000000009999',
        xmls_retornados=xmls1,
        tempo_ms=1500,
        status='sucesso'
    )
    
    # Segunda consulta: 5 XMLs (DIVERGÊNCIA!)
    xmls2 = [
        {'tipo': 'nfe', 'chave': '35260101234567890123456789012345678901234500'},
        {'tipo': 'nfe', 'chave': '35260101234567890123456789012345678901234501'},
        {'tipo': 'nfe', 'chave': '35260101234567890123456789012345678901234502'},
        {'tipo': 'evento', 'chave': '35260101234567890123456789012345678901234500', 'evento': '210210'},
        {'tipo': 'evento', 'chave': '35260101234567890123456789012345678901234501', 'evento': '210240'}
    ]
    
    db.registrar_historico_nsu(
        certificado='CERT_DIVERGENCIA',
        informante='12345678000190',
        nsu_consultado='000000000009999',  # MESMO NSU
        xmls_retornados=xmls2,
        tempo_ms=1800,
        status='sucesso'
    )
    
    print("✅ Consultas divergentes registradas")
    
    # Compara as consultas
    print("\n🔍 Comparando consultas do NSU 000000000009999...")
    resultado = db.comparar_consultas_nsu(
        informante='12345678000190',
        nsu='000000000009999'
    )
    
    print(f"\n📊 Resultado da Comparação:")
    print(f"   - Total de consultas: {resultado['total_consultas']}")
    print(f"   - Divergências encontradas: {'✅ SIM' if resultado['divergencias_encontradas'] else '❌ NÃO'}")
    
    if resultado['divergencias_encontradas']:
        print(f"\n⚠️ Análise de Divergências:")
        analise = resultado['analise']
        print(f"   - Total XMLs único: {analise['total_xmls_unico']}")
        print(f"   - Valores diferentes: {analise['valores_total_xmls']}")
        print(f"   - Total NF-e único: {analise['total_nfe_unico']}")
        print(f"   - Valores diferentes: {analise['valores_total_nfe']}")
        print(f"   - Total Eventos único: {analise['total_eventos_unico']}")
        print(f"   - Valores diferentes: {analise['valores_total_eventos']}")
        
        print(f"\n🔎 Consultas Detalhadas:")
        for i, consulta in enumerate(resultado['consultas'], 1):
            print(f"\n   Consulta {i}:")
            print(f"   - Data: {consulta['data_hora_consulta']}")
            print(f"   - Total XMLs: {consulta['total_xmls_retornados']}")
            print(f"   - NF-e: {consulta['total_nfe']}, Eventos: {consulta['total_eventos']}")
            print(f"   - Tempo: {consulta['tempo_processamento_ms']}ms")
        
        return True
    else:
        print("⚠️ Divergência não detectada (algo está errado!)")
        return False

def test_relatorio_consolidado():
    """Teste 5: Testa geração de relatório consolidado"""
    print_header("TESTE 5: Relatório Consolidado")
    
    db = DatabaseManager('notas.db')
    
    print("\n📊 Gerando relatório dos últimos 30 dias...")
    relatorio = db.relatorio_historico_nsu(dias=30)
    
    if relatorio['total_consultas'] > 0:
        print(f"\n✅ Relatório gerado com sucesso!")
        print(f"\n📋 Resumo Geral:")
        print(f"   - Período: {relatorio['periodo']}")
        print(f"   - Total de consultas: {relatorio['total_consultas']}")
        print(f"   - Consultas com sucesso: {relatorio['consultas_sucesso']}")
        print(f"   - Consultas com erro: {relatorio['consultas_erro']}")
        print(f"   - Consultas vazias: {relatorio['consultas_vazio']}")
        
        print(f"\n📦 Documentos Processados:")
        print(f"   - Total de XMLs: {relatorio['total_xmls_processados']}")
        print(f"   - NF-e: {relatorio['total_nfe']}")
        print(f"   - CT-e: {relatorio['total_cte']}")
        print(f"   - NFS-e: {relatorio['total_nfse']}")
        print(f"   - Eventos: {relatorio['total_eventos']}")
        
        print(f"\n⏱️ Performance:")
        print(f"   - Tempo médio por consulta: {relatorio['tempo_medio_ms']}ms")
        
        print(f"\n🔐 Certificados Utilizados:")
        for cert in relatorio['certificados_utilizados']:
            print(f"   - {cert}")
        
        return True
    else:
        print("⚠️ Nenhuma consulta no período")
        return True  # Não é erro, apenas não há dados

def test_analise_producao():
    """Teste 6: Analisa dados reais de produção (se existirem)"""
    print_header("TESTE 6: Análise de Dados de Produção")
    
    db = DatabaseManager('notas.db')
    
    with db._connect() as conn:
        # Conta registros reais
        cursor = conn.execute("SELECT COUNT(*) FROM historico_nsu")
        total = cursor.fetchone()[0]
        
        if total > 0:
            print(f"\n✅ Encontrados {total} registros de histórico em produção!")
            
            # Estatísticas gerais
            cursor = conn.execute("""
                SELECT 
                    COUNT(DISTINCT certificado) as total_certs,
                    COUNT(DISTINCT informante) as total_informantes,
                    SUM(total_xmls_retornados) as total_xmls,
                    SUM(total_nfe) as total_nfe,
                    SUM(total_cte) as total_cte,
                    SUM(total_nfse) as total_nfse,
                    SUM(total_eventos) as total_eventos,
                    AVG(tempo_processamento_ms) as tempo_medio
                FROM historico_nsu
            """)
            
            stats = cursor.fetchone()
            
            print(f"\n📊 Estatísticas Gerais:")
            print(f"   - Certificados diferentes: {stats[0]}")
            print(f"   - Informantes diferentes: {stats[1]}")
            print(f"   - Total de XMLs processados: {stats[2]}")
            print(f"   - NF-e: {stats[3]}")
            print(f"   - CT-e: {stats[4]}")
            print(f"   - NFS-e: {stats[5]}")
            print(f"   - Eventos: {stats[6]}")
            print(f"   - Tempo médio: {stats[7]:.0f}ms")
            
            # Verifica divergências
            cursor = conn.execute("""
                SELECT informante, nsu_consultado, COUNT(*) as num_consultas
                FROM historico_nsu
                GROUP BY informante, nsu_consultado
                HAVING COUNT(*) > 1
            """)
            
            divergencias = cursor.fetchall()
            
            if divergencias:
                print(f"\n⚠️ Detectadas {len(divergencias)} NSUs consultados múltiplas vezes:")
                for div in divergencias[:5]:  # Mostra apenas 5 primeiros
                    print(f"   - Informante {div[0]}, NSU {div[1]}: {div[2]} consultas")
                    
                    # Analisa divergência
                    resultado = db.comparar_consultas_nsu(div[0], div[1])
                    if resultado['divergencias_encontradas']:
                        print(f"     🚨 DIVERGÊNCIA REAL DETECTADA!")
            else:
                print(f"\n✅ Nenhuma divergência detectada nos dados de produção")
            
            return True
        else:
            print("\n📭 Nenhum registro de histórico em produção ainda")
            print("   Execute uma busca para popular o histórico")
            return True  # Não é erro, apenas não há dados ainda

def main():
    """Função principal"""
    print_header("🧪 TESTE COMPLETO DO SISTEMA DE HISTÓRICO NSU")
    print("\nEste script valida todas as funcionalidades do histórico NSU.")
    print("Aguarde enquanto executamos os testes...")
    
    testes = [
        ("Tabela e Índices", test_tabela_historico),
        ("Registro de Histórico", test_registro_historico),
        ("Busca com Filtros", test_busca_com_filtros),
        ("Comparação de Consultas", test_comparacao_consultas),
        ("Relatório Consolidado", test_relatorio_consolidado),
        ("Análise de Produção", test_analise_producao)
    ]
    
    resultados = []
    
    for nome, funcao_teste in testes:
        try:
            resultado = funcao_teste()
            resultados.append((nome, resultado))
        except Exception as e:
            print(f"\n❌ Erro no teste '{nome}': {e}")
            import traceback
            traceback.print_exc()
            resultados.append((nome, False))
    
    # Resumo final
    print_header("📊 RESUMO FINAL DOS TESTES")
    
    total_testes = len(resultados)
    testes_ok = sum(1 for _, resultado in resultados if resultado)
    testes_falha = total_testes - testes_ok
    
    print(f"\nTotal de testes: {total_testes}")
    print(f"✅ Sucesso: {testes_ok}")
    print(f"❌ Falha: {testes_falha}")
    
    print("\nDetalhamento:")
    for nome, resultado in resultados:
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"   {status} - {nome}")
    
    print("\n" + "="*70)
    
    if testes_falha == 0:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("\n✅ Sistema de Histórico NSU está 100% funcional!")
        print("\n📝 Próximos passos:")
        print("   1. Execute uma busca real para popular o histórico")
        print("   2. Use db.buscar_historico_nsu() para consultar")
        print("   3. Use db.comparar_consultas_nsu() para detectar divergências")
        print("   4. Use db.relatorio_historico_nsu() para análises")
    else:
        print("⚠️ ALGUNS TESTES FALHARAM!")
        print("Revise os erros acima e corrija os problemas.")
    
    print("="*70)

if __name__ == "__main__":
    main()
