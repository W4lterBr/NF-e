"""
Teste de consulta de evento de CT-e cancelado.
Verifica se o sistema detecta corretamente o cancelamento de CT-es.
"""

from nfe_search import DatabaseManager, NFeService
from pathlib import Path
import logging

# Configura logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Chave do CT-e cancelado
CHAVE_CTE_CANCELADO = "50251203232675000154570010056290311009581385"

print("=" * 80)
print("TESTE: Consulta de Evento de CT-e Cancelado")
print("=" * 80)

# 1. Verifica status atual no banco
print("\n1️⃣ Verificando status atual no banco...")
db = DatabaseManager("notas.db")

import sqlite3
conn = sqlite3.connect("notas.db")
cursor = conn.execute(
    "SELECT numero, tipo, status FROM notas_detalhadas WHERE chave = ?",
    (CHAVE_CTE_CANCELADO,)
)
result = cursor.fetchone()

if result:
    print(f"   Número: {result[0]}")
    print(f"   Tipo: {result[1]}")
    print(f"   Status ANTES: {result[2]}")
else:
    print("   ❌ Chave não encontrada no banco!")
    exit(1)

# 2. Carrega certificado
print("\n2️⃣ Carregando certificados...")
certs = db.get_certificados()
if not certs:
    print("   ❌ Nenhum certificado configurado!")
    conn.close()
    exit(1)

# Converte tuplas em dicts
cert_list = []
for c in certs:
    cert_list.append({
        'cnpj_cpf': c[0],           # [0] = cnpj
        'caminho': c[1],            # [1] = caminho  
        'senha': c[2],              # [2] = senha
        'cUF_autor': c[4] if len(c) > 4 else '50'  # [4] = cuf
    })

# Usa primeiro certificado MS (cUF=50)
cert = None
for c in cert_list:
    if c.get('cUF_autor') == '50':
        cert = c
        break

if not cert:
    cert = cert_list[0]

print(f"   ✅ Certificado: {cert.get('cnpj_cpf')}")

# 3. Cria serviço e consulta eventos
print("\n3️⃣ Consultando eventos na SEFAZ...")
try:
    svc = NFeService(
        cert['caminho'],          # Caminho do certificado
        cert['senha'],            # Senha
        cert['cnpj_cpf'],         # CNPJ (informante)
        cert['cUF_autor']         # UF
    )
    
    xml_resposta = svc.consultar_eventos_chave(CHAVE_CTE_CANCELADO)
    
    if not xml_resposta:
        print("   ❌ Nenhuma resposta da SEFAZ")
        exit(1)
    
    print(f"   ✅ Resposta recebida ({len(xml_resposta)} bytes)")
    
    # Salva resposta para debug
    debug_file = Path("xmls/Debug de notas") / f"test_cte_evento_{CHAVE_CTE_CANCELADO[:15]}.xml"
    debug_file.parent.mkdir(parents=True, exist_ok=True)
    debug_file.write_text(xml_resposta, encoding='utf-8')
    print(f"   💾 Debug salvo: {debug_file}")
    
except Exception as e:
    print(f"   ❌ Erro ao consultar: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# 4. Processa resposta
print("\n4️⃣ Processando resposta...")
from lxml import etree

try:
    root = etree.fromstring(xml_resposta.encode('utf-8'))
    
    # Namespace CT-e
    ns_uri = 'http://www.portalfiscal.inf.br/cte'
    
    # Busca eventos
    eventos = root.findall(f'.//{{{ns_uri}}}infEvento')
    print(f"   Eventos encontrados: {len(eventos)}")
    
    for idx, evento in enumerate(eventos, 1):
        tp_evento = evento.findtext(f'{{{ns_uri}}}tpEvento')
        c_stat = evento.findtext(f'.//{{{ns_uri}}}cStat')
        x_motivo = evento.findtext(f'.//{{{ns_uri}}}xMotivo')
        
        print(f"\n   Evento #{idx}:")
        print(f"     tpEvento: {tp_evento}")
        print(f"     cStat: {c_stat}")
        print(f"     xMotivo: {x_motivo}")
        
        if tp_evento == '110111' and c_stat == '135':
            print("     🎯 CANCELAMENTO DETECTADO!")
            
            # Atualiza banco
            novo_status = "Cancelamento de CT-e homologado"
            db.atualizar_status_por_evento(CHAVE_CTE_CANCELADO, novo_status)
            print(f"     ✅ Status atualizado no banco: {novo_status}")

except Exception as e:
    print(f"   ❌ Erro ao processar: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# 5. Verifica status final no banco
print("\n5️⃣ Verificando status final no banco...")
cursor = conn.execute(
    "SELECT status FROM notas_detalhadas WHERE chave = ?",
    (CHAVE_CTE_CANCELADO,)
)
result = cursor.fetchone()
conn.close()

if result:
    print(f"   Status DEPOIS: {result[0]}")
    
    if 'cancel' in result[0].lower():
        print("\n✅ SUCESSO! CT-e cancelado detectado corretamente!")
    else:
        print("\n❌ FALHA! Status não foi atualizado para cancelamento")
else:
    print("   ❌ Chave não encontrada no banco!")

print("\n" + "=" * 80)
