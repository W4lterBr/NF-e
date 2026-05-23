# 💻 Exemplos Práticos de Código

## Python - Busca Básica de NF-e

### Exemplo 1: Buscar Documentos por NSU

```python
from nfe_search import (
    DatabaseManager,
    consultar_ultimo_nsu_sefaz,
    baixar_documentos_dfe,
    processar_nfe
)

def buscar_nfes_automatico():
    """
    Busca automática de NF-e usando DFe Distribution
    """
    # Inicializa banco de dados
    db = DatabaseManager('notas.db')
    
    # Dados do certificado
    cnpj = "33251845000109"
    caminho_pfx = "certificado.pfx"
    senha = "senha123"
    cuf = 50  # MS = Mato Grosso do Sul
    
    # 1. Consulta último NSU processado
    ultimo_nsu = db.get_last_nsu(cnpj)
    if not ultimo_nsu:
        ultimo_nsu = "000000000000000"  # Inicia do zero
    
    print(f"Último NSU processado: {ultimo_nsu}")
    
    # 2. Consulta NSU máximo disponível na SEFAZ
    max_nsu_response = consultar_ultimo_nsu_sefaz(
        cnpj=cnpj,
        caminho_certificado=caminho_pfx,
        senha_certificado=senha,
        cuf=cuf
    )
    
    max_nsu = max_nsu_response.get('maxNSU', ultimo_nsu)
    print(f"NSU máximo na SEFAZ: {max_nsu}")
    
    # 3. Baixa documentos
    resultado = baixar_documentos_dfe(
        ultimo_nsu=ultimo_nsu,
        cnpj=cnpj,
        caminho_certificado=caminho_pfx,
        senha_certificado=senha,
        max_nsu=max_nsu,
        cuf=cuf
    )
    
    # 4. Processa documentos
    if resultado.get('documentos'):
        for doc in resultado['documentos']:
            nsu = doc['nsu']
            schema = doc['schema']
            xml = doc['xml']
            
            print(f"Processando NSU {nsu} ({schema})")
            
            # Salva e processa conforme o tipo
            if 'NFe' in schema:
                # Extrai dados da NF-e
                from nfe_search import extrair_nota_detalhada, XMLProcessor
                
                nota_dados = extrair_nota_detalhada(
                    xml_txt=xml,
                    parser=XMLProcessor(),
                    db=db,
                    chave=doc['chave'],
                    informante=cnpj,
                    nsu_documento=nsu
                )
                
                # Salva no banco
                db.salvar_nota_detalhada(nota_dados)
                
                print(f"  ✓ NF-e {nota_dados['numero']} - {nota_dados['nome_emitente']}")
                print(f"    Valor: R$ {nota_dados['valor']}")
        
        # 5. Atualiza NSU no banco
        novo_nsu = resultado.get('ultNSU', ultimo_nsu)
        db.update_nsu(cnpj, novo_nsu)
        
        print(f"\nNSU atualizado para: {novo_nsu}")
    
    return resultado

# Executar
if __name__ == "__main__":
    resultado = buscar_nfes_automatico()
    print(f"\nTotal processado: {len(resultado.get('documentos', []))}")
```

### Exemplo 2: Buscar NF-e por Chave de Acesso

```python
from nfe_search import consultar_nfe_por_chave, extrair_nota_detalhada, XMLProcessor, DatabaseManager

def buscar_nfe_por_chave(chave):
    """
    Busca NF-e específica pela chave de acesso
    
    Args:
        chave: Chave de 44 dígitos
    
    Returns:
        dict: Dados completos da NF-e ou None se não encontrada
    """
    db = DatabaseManager('notas.db')
    
    # Certificado
    cnpj_cert = "33251845000109"
    caminho_pfx = "certificado.pfx"
    senha = "senha123"
    cuf = 50
    
    print(f"Buscando chave: {chave}")
    
    # 1. Consulta SEFAZ
    xml_response = consultar_nfe_por_chave(
        chave=chave,
        caminho_pfx=caminho_pfx,
        senha=senha,
        cnpj_cert=cnpj_cert,
        cuf=cuf
    )
    
    if not xml_response:
        print("❌ Nota não encontrada na SEFAZ")
        return None
    
    # 2. Verifica se foi autorizada
    from lxml import etree
    tree = etree.fromstring(xml_response.encode('utf-8'))
    
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    cStat = tree.findtext('.//nfe:cStat', namespaces=ns)
    xMotivo = tree.findtext('.//nfe:xMotivo', namespaces=ns)
    
    print(f"Status: {cStat} - {xMotivo}")
    
    if cStat not in ['100', '101', '110', '150']:
        print("❌ Nota não autorizada")
        return None
    
    # 3. Extrai dados (se XML completo)
    if '<nfeProc' in xml_response or '<NFe' in xml_response:
        nota_dados = extrair_nota_detalhada(
            xml_txt=xml_response,
            parser=XMLProcessor(),
            db=db,
            chave=chave,
            informante=cnpj_cert,
            nsu_documento=""
        )
        
        # 4. Salva no banco
        db.salvar_nota_detalhada(nota_dados)
        
        # 5. Salva XML em disco
        from nfe_search import salvar_xml_por_certificado
        
        caminho_xml = salvar_xml_por_certificado(
            xml=xml_response,
            cnpj_cpf=cnpj_cert,
            pasta_base="xmls"
        )
        
        print(f"✅ NF-e {nota_dados['numero']} salva")
        print(f"   Emitente: {nota_dados['nome_emitente']}")
        print(f"   Valor: R$ {nota_dados['valor']}")
        print(f"   Arquivo: {caminho_xml}")
        
        return nota_dados
    else:
        print("⚠️ Retornou apenas protocolo (sem dados completos)")
        return {'chave': chave, 'status': cStat, 'motivo': xMotivo}

# Executar
if __name__ == "__main__":
    resultado = buscar_nfe_por_chave("50260101773924000193550010000173831950403658")
```

### Exemplo 3: Listar Documentos com Filtros

```python
from nfe_search import DatabaseManager
from datetime import datetime, timedelta

def listar_documentos(data_inicio=None, data_fim=None, tipo=None, cnpj_emitente=None):
    """
    Lista documentos com filtros
    
    Args:
        data_inicio: Data inicial (YYYY-MM-DD)
        data_fim: Data final (YYYY-MM-DD)
        tipo: Tipo do documento (NFe, CTe, NFSe)
        cnpj_emitente: CNPJ do emitente
    
    Returns:
        list: Lista de documentos
    """
    db = DatabaseManager('notas.db')
    
    # Monta query SQL
    query = "SELECT * FROM notas_detalhadas WHERE 1=1"
    params = []
    
    if data_inicio:
        query += " AND data_emissao >= ?"
        params.append(data_inicio)
    
    if data_fim:
        query += " AND data_emissao <= ?"
        params.append(data_fim)
    
    if tipo:
        query += " AND tipo = ?"
        params.append(tipo)
    
    if cnpj_emitente:
        query += " AND cnpj_emitente = ?"
        params.append(cnpj_emitente)
    
    query += " ORDER BY data_emissao DESC, numero DESC"
    
    # Executa query
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    
    cursor.execute(query, params)
    colunas = [desc[0] for desc in cursor.description]
    
    documentos = []
    for row in cursor.fetchall():
        doc = dict(zip(colunas, row))
        documentos.append(doc)
    
    conn.close()
    
    return documentos

# Exemplo de uso
if __name__ == "__main__":
    # Listar NF-e dos últimos 7 dias
    hoje = datetime.now()
    data_inicio = (hoje - timedelta(days=7)).strftime('%Y-%m-%d')
    data_fim = hoje.strftime('%Y-%m-%d')
    
    docs = listar_documentos(
        data_inicio=data_inicio,
        data_fim=data_fim,
        tipo='NFe'
    )
    
    print(f"Encontradas {len(docs)} NF-e nos últimos 7 dias\n")
    
    for doc in docs[:10]:  # Mostra primeiras 10
        print(f"NF-e {doc['numero']} - {doc['data_emissao']}")
        print(f"  Emitente: {doc['nome_emitente']}")
        print(f"  Valor: R$ {doc['valor']}")
        print()
```

---

## JavaScript/Node.js - Integração Web

### Exemplo 1: API REST com Express

```javascript
const express = require('express');
const { spawn } = require('child_process');
const app = express();

app.use(express.json());

// Endpoint: Buscar NF-e por chave
app.post('/api/nfe/buscar-chave', async (req, res) => {
    const { chave, cnpj_certificado } = req.body;
    
    if (!chave || chave.length !== 44) {
        return res.status(400).json({
            success: false,
            error: 'Chave inválida'
        });
    }
    
    try {
        // Chama script Python
        const python = spawn('python', [
            'buscar_nfe_wrapper.py',
            '--chave', chave,
            '--cnpj', cnpj_certificado
        ]);
        
        let stdout = '';
        let stderr = '';
        
        python.stdout.on('data', (data) => {
            stdout += data.toString();
        });
        
        python.stderr.on('data', (data) => {
            stderr += data.toString();
        });
        
        python.on('close', (code) => {
            if (code === 0) {
                try {
                    const resultado = JSON.parse(stdout);
                    res.json({
                        success: true,
                        data: resultado
                    });
                } catch (e) {
                    res.status(500).json({
                        success: false,
                        error: 'Erro ao processar resposta'
                    });
                }
            } else {
                res.status(500).json({
                    success: false,
                    error: stderr || 'Erro ao buscar NF-e'
                });
            }
        });
        
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Endpoint: Listar documentos
app.get('/api/documentos', async (req, res) => {
    const { 
        data_inicio, 
        data_fim, 
        tipo, 
        cnpj_emitente,
        limite = 50,
        pagina = 1
    } = req.query;
    
    try {
        const python = spawn('python', [
            'listar_documentos_wrapper.py',
            '--data-inicio', data_inicio || '',
            '--data-fim', data_fim || '',
            '--tipo', tipo || '',
            '--cnpj-emitente', cnpj_emitente || '',
            '--limite', limite,
            '--pagina', pagina
        ]);
        
        let stdout = '';
        
        python.stdout.on('data', (data) => {
            stdout += data.toString();
        });
        
        python.on('close', (code) => {
            if (code === 0) {
                const resultado = JSON.parse(stdout);
                res.json({
                    success: true,
                    total: resultado.total,
                    pagina: parseInt(pagina),
                    limite: parseInt(limite),
                    documentos: resultado.documentos
                });
            } else {
                res.status(500).json({
                    success: false,
                    error: 'Erro ao listar documentos'
                });
            }
        });
        
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Endpoint: Download XML
app.get('/api/documento/:chave/xml', async (req, res) => {
    const { chave } = req.params;
    const fs = require('fs');
    const path = require('path');
    
    // Busca arquivo XML no banco de dados
    const sqlite3 = require('sqlite3').verbose();
    const db = new sqlite3.Database('./notas.db');
    
    db.get(
        'SELECT caminho_arquivo FROM xmls_baixados WHERE chave = ?',
        [chave],
        (err, row) => {
            if (err) {
                return res.status(500).json({
                    success: false,
                    error: 'Erro ao buscar XML'
                });
            }
            
            if (!row || !row.caminho_arquivo) {
                return res.status(404).json({
                    success: false,
                    error: 'XML não encontrado'
                });
            }
            
            const caminhoXml = row.caminho_arquivo;
            
            if (!fs.existsSync(caminhoXml)) {
                return res.status(404).json({
                    success: false,
                    error: 'Arquivo XML não existe'
                });
            }
            
            res.setHeader('Content-Type', 'application/xml');
            res.setHeader('Content-Disposition', `attachment; filename="${chave}.xml"`);
            
            const fileStream = fs.createReadStream(caminhoXml);
            fileStream.pipe(res);
        }
    );
    
    db.close();
});

// Inicia servidor
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`API rodando na porta ${PORT}`);
});
```

### Exemplo 2: Script Python Wrapper para Web

```python
# buscar_nfe_wrapper.py
# Script para ser chamado pelo Node.js

import sys
import json
import argparse
from nfe_search import DatabaseManager, consultar_nfe_por_chave, extrair_nota_detalhada, XMLProcessor

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--chave', required=True)
    parser.add_argument('--cnpj', required=True)
    args = parser.parse_args()
    
    try:
        db = DatabaseManager('notas.db')
        
        # Busca certificado
        certs = db.get_certificados()
        cert = next((c for c in certs if c[0] == args.cnpj), None)
        
        if not cert:
            print(json.dumps({
                'success': False,
                'error': 'Certificado não encontrado'
            }))
            sys.exit(1)
        
        cnpj, caminho, senha, informante, cuf = cert
        
        # Busca NF-e
        xml_response = consultar_nfe_por_chave(
            chave=args.chave,
            caminho_pfx=caminho,
            senha=senha,
            cnpj_cert=cnpj,
            cuf=cuf
        )
        
        if not xml_response:
            print(json.dumps({
                'success': False,
                'error': 'NF-e não encontrada'
            }))
            sys.exit(1)
        
        # Extrai dados
        nota_dados = extrair_nota_detalhada(
            xml_txt=xml_response,
            parser=XMLProcessor(),
            db=db,
            chave=args.chave,
            informante=cnpj,
            nsu_documento=""
        )
        
        # Salva no banco
        db.salvar_nota_detalhada(nota_dados)
        
        # Retorna JSON
        print(json.dumps({
            'success': True,
            'data': {
                'chave': nota_dados['chave'],
                'numero': nota_dados['numero'],
                'data_emissao': nota_dados['data_emissao'],
                'emitente': {
                    'cnpj': nota_dados['cnpj_emitente'],
                    'nome': nota_dados['nome_emitente']
                },
                'destinatario': {
                    'cnpj': nota_dados['cnpj_destinatario'],
                    'nome': nota_dados['nome_destinatario']
                },
                'valor': float(nota_dados['valor']),
                'status': nota_dados['status']
            }
        }))
        
    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': str(e)
        }))
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

## PHP - Integração com Laravel

```php
<?php

namespace App\Services;

use Illuminate\Support\Facades\Process;

class NFeBuscaService
{
    public function buscarPorChave($chave, $cnpjCertificado)
    {
        $pythonScript = base_path('python/buscar_nfe_wrapper.py');
        
        $result = Process::run([
            'python',
            $pythonScript,
            '--chave', $chave,
            '--cnpj', $cnpjCertificado
        ]);
        
        if ($result->failed()) {
            throw new \Exception('Erro ao buscar NF-e: ' . $result->errorOutput());
        }
        
        $data = json_decode($result->output(), true);
        
        if (!$data['success']) {
            throw new \Exception($data['error'] ?? 'Erro desconhecido');
        }
        
        return $data['data'];
    }
    
    public function listarDocumentos($filtros = [])
    {
        $db = new \SQLite3(base_path('notas.db'));
        
        $query = "SELECT * FROM notas_detalhadas WHERE 1=1";
        $params = [];
        
        if (!empty($filtros['data_inicio'])) {
            $query .= " AND data_emissao >= :data_inicio";
            $params[':data_inicio'] = $filtros['data_inicio'];
        }
        
        if (!empty($filtros['data_fim'])) {
            $query .= " AND data_emissao <= :data_fim";
            $params[':data_fim'] = $filtros['data_fim'];
        }
        
        if (!empty($filtros['tipo'])) {
            $query .= " AND tipo = :tipo";
            $params[':tipo'] = $filtros['tipo'];
        }
        
        $query .= " ORDER BY data_emissao DESC LIMIT 50";
        
        $stmt = $db->prepare($query);
        
        foreach ($params as $key => $value) {
            $stmt->bindValue($key, $value);
        }
        
        $result = $stmt->execute();
        
        $documentos = [];
        while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
            $documentos[] = $row;
        }
        
        return $documentos;
    }
}
```

---

Continua no próximo arquivo...
