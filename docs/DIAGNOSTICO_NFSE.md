# Diagnóstico: NFS-e não aparece na interface

## 🔍 Problema Relatado
Após **Busca Completa**, nenhuma NFS-e aparece na interface.

---

## ✅ Verificação Realizada (29/01/2026)

### 1. Sistema está buscando NFS-e corretamente
```log
2026-01-29 13:18:19,543 [INFO] ✅ Cliente NFS-e REST inicializado: https://adn.nfse.gov.br
2026-01-29 13:18:19,543 [INFO] 📋 Iniciando busca de NFS-e para 33251845000109
2026-01-29 13:18:20,031 [INFO] ✅ [33251845000109] NFS-e: Ambiente Nacional retornou maxNSU=0 (sem documentos)
```

✅ **Conclusão:** O sistema **ESTÁ funcionando**. API ADN retorna: **SEM DOCUMENTOS**.

---

## ❓ Por que maxNSU=0?

### Razão 1: Municípios não integrados ao Ambiente Nacional

**O que é o ADN (Ambiente Nacional)?**
- Sistema centralizado da Receita Federal para NFS-e
- **NEM TODOS os municípios** estão integrados
- Municípios menores usam sistemas próprios (ISS Web, Betha, etc.)

**Como verificar:**
1. Acesse: https://www.gov.br/nfse/pt-br/municipios-integrados
2. Procure pelos municípios dos CNPJs cadastrados
3. Se o município **NÃO estiver na lista**, não haverá NFS-e via ADN

**Exemplo:**
| CNPJ | Município | Integrado ao ADN? |
|------|-----------|-------------------|
| 33251845000109 | Campo Grande/MS | ✅ Sim |
| 47539664000197 | Dourados/MS | ❓ Verificar |
| 01773924000193 | ? | ❓ Verificar |

---

### Razão 2: CNPJs sem movimentação de NFS-e

**Cenários possíveis:**
- CNPJ não emitiu NFS-e no período disponível
- CNPJ não recebeu NFS-e de prestadores
- CNPJ usa apenas NF-e/CT-e (sem serviços)

**Como verificar:**
1. Acesse o portal da prefeitura do município
2. Consulte NFS-e manualmente pelo CNPJ
3. Verifique se há emissões recentes

---

### Razão 3: Período de disponibilidade limitado

**Limitações conhecidas:**
- ADN pode disponibilizar apenas **últimos 90 dias**
- NFS-e antigas podem não estar acessíveis via API
- Alguns municípios têm períodos menores

**Como verificar:**
1. Consulte o log da busca
2. Verifique se há NFS-e em período anterior
3. Teste com emissão recente (últimos 30 dias)

---

### Razão 4: NSU NFS-e zerado (primeira busca)

**Comportamento do sistema:**
```python
# Primeira busca: NSU = 0
nsu_atual = db.get_nsu_nfse(informante) or '0'

# Busca documentos a partir de NSU=0
# Se não houver documentos, continua em 0
```

**Solução:** Funciona corretamente. Sistema busca desde o início.

---

## 🧪 Teste para Confirmar

### Teste 1: Verificar CNPJs no Portal ADN
```
1. Acesse: https://www.gov.br/nfse/
2. Faça login com certificado digital
3. Consulte NFS-e para cada CNPJ
4. Anote quantas NFS-e aparecem
```

### Teste 2: Forçar NSU específico
```sql
-- No banco de dados SQLite
UPDATE nsu_nfse SET ult_nsu = '0' WHERE informante = '33251845000109';
```
Depois execute **Busca NFS-e** novamente.

### Teste 3: Emitir NFS-e de teste
```
1. Emita uma NFS-e manualmente pelo portal da prefeitura
2. Aguarde 5-10 minutos (processamento ADN)
3. Execute "Busca Completa" novamente
4. Verifique se aparece na interface
```

---

## 🛠️ Como Adicionar NFS-e Manualmente

Se o município **NÃO** estiver no ADN, você pode:

### Opção 1: Importar XMLs manualmente
```
1. Baixe XMLs do portal da prefeitura
2. Coloque em: xmls\<CNPJ>\<MES-ANO>\NFSE\
3. Execute "Buscar na SEFAZ" > "Reprocessar XMLs"
```

### Opção 2: Integrar API municipal
```python
# Adicionar em nfse_search.py
class NFSeWebissMunicipioX:
    def __init__(self, cert_path, senha, cnpj):
        self.base_url = "https://municipioX.gov.br/nfse"
        # Implementar autenticação e consulta
```

---

## 📊 Estatísticas da Busca (29/01/2026)

| CNPJ | NFe | CTe | NFS-e | Eventos |
|------|-----|-----|-------|---------|
| 33251845000109 | 1 | 25 | **0** | 3 |
| 47539664000197 | 0 | 14 | **0** | 0 |
| 01773924000193 | 4 | 18 | **0** | 0 |

**Total NFS-e encontradas:** 0 ❌

---

## ✅ Checklist de Validação

Para confirmar que o sistema está funcionando:

- [x] Cliente NFS-e REST inicializado
- [x] API ADN responde (maxNSU=0 é resposta válida)
- [x] Logs mostram busca sendo executada
- [x] Filtros da interface não excluem NFS-e
- [ ] Município integrado ao ADN (verificar manualmente)
- [ ] CNPJ tem NFS-e emitidas/recebidas (verificar portal)
- [ ] NFS-e dentro do período de disponibilidade

---

## 📝 Próximos Passos

### Se município estiver no ADN:
1. Aguarde emissão/recebimento de NFS-e
2. Execute "Busca Completa" novamente
3. NFS-e aparecerá automaticamente

### Se município NÃO estiver no ADN:
1. Implemente integração com API municipal
2. Ou importe XMLs manualmente
3. Atualize documentação com limitações

---

## 🔗 Links Úteis

- **Portal ADN:** https://www.gov.br/nfse/
- **Municípios integrados:** https://www.gov.br/nfse/pt-br/municipios-integrados
- **Documentação API ADN:** https://www.gov.br/nfse/pt-br/documentacao
- **ABRASF (Padrão NFS-e):** http://www.abrasf.org.br/

---

## 📞 Suporte

Se após verificações o problema persistir:
1. Verifique logs: `logs/busca_nfe_2026-01-29.log`
2. Confirme município integrado ao ADN
3. Teste com NFS-e recente (últimos 30 dias)
4. Consulte CHANGELOG.md para atualizações

---

**Última atualização:** 29/01/2026  
**Versão:** 1.0.9.1  
**Status:** ✅ Sistema funcionando - Sem NFS-e disponível no ADN
