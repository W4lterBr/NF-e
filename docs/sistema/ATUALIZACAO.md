# 🔄 Sistema de Atualização Automática

## Como Funciona

O sistema permite que usuários atualizem o aplicativo **automaticamente** sem precisar baixar manualmente nenhum arquivo. Basta clicar em **"🔄 Atualizações"** no menu!

## Para Desenvolvedores: Como Publicar uma Atualização

### Método Rápido (Recomendado)

1. **Atualize a versão** em 3 arquivos:
   - `version.txt` → Ex: `1.0.32`
   - `installer.iss` → Linha 5: `#define MyAppVersion "1.0.32"`
   - `app.manifest` → Linha 4: `version="1.0.32.0"`

2. **Execute o deploy automático**:
   ```bash
   deploy.bat
   ```
   
   O script vai:
   - ✅ Compilar o aplicativo
   - ✅ Gerar o instalador
   - ✅ Fazer commit no Git
   - ✅ Criar tag de versão
   - ✅ Enviar para GitHub
   - ✅ Abrir página para criar release

3. **Na página do GitHub que abrir**:
   - Título: `Release v1.0.32`
   - Descrição: Liste as novidades/correções
   - Faça upload de: `Output\Busca_XML_Setup.exe`
   - Clique em **"Publish release"**

**Pronto!** Agora qualquer usuário pode atualizar automaticamente! 🎉

### Método Manual (Se deploy.bat não funcionar)

1. Atualize os 3 arquivos de versão (acima)

2. Compile:
   ```bash
   build.bat
   ```

3. Commit e tag:
   ```bash
   git add .
   git commit -m "Release v1.0.32"
   git tag -a v1.0.32 -m "Release v1.0.32"
   git push origin main
   git push origin v1.0.32
   ```

4. Crie release no GitHub:
   - Vá em: https://github.com/W4lterBr/NF-e/releases/new
   - Tag: `v1.0.32`
   - Título: `Release v1.0.32`
   - Faça upload: `Output\Busca_XML_Setup.exe`
   - Publique

## Para Usuários: Como Atualizar

1. Abra o aplicativo **Busca XML**
2. Clique no menu **"Configurações"** → **"🔄 Atualizações"** (ou `Ctrl+U`)
3. Se houver atualização disponível:
   - Clique em **"Sim"** para atualizar
   - Aguarde o download automático
   - O instalador será executado automaticamente
   - Reinicie o aplicativo

**Pronto!** Você está na versão mais recente! ✨

## Fluxo de Atualização Automática

```
┌─────────────────────────────────────────────────────────┐
│  1. Usuário clica em "🔄 Atualizações"                  │
└──────────────────┬──────────────────────────────────────┘
                   │
                   v
┌─────────────────────────────────────────────────────────┐
│  2. Sistema verifica GitHub Releases                     │
│     - Compara versão local com remota                    │
│     - Se houver update, mostra diálogo                   │
└──────────────────┬──────────────────────────────────────┘
                   │
                   v
┌─────────────────────────────────────────────────────────┐
│  3. Baixa instalador automaticamente                     │
│     - Barra de progresso                                 │
│     - Download em segundo plano                          │
└──────────────────┬──────────────────────────────────────┘
                   │
                   v
┌─────────────────────────────────────────────────────────┐
│  4. Executa instalador silencioso                        │
│     - Modo /VERYSILENT                                   │
│     - Atualiza arquivos automaticamente                  │
└──────────────────┬──────────────────────────────────────┘
                   │
                   v
┌─────────────────────────────────────────────────────────┐
│  5. Usuário reinicia o aplicativo                        │
│     - Nova versão já instalada! ✅                       │
└─────────────────────────────────────────────────────────┘
```

## Vantagens

✅ **Zero fricção**: Usuário só clica em "Atualizar"  
✅ **Automático**: Download e instalação sem intervenção  
✅ **Seguro**: Verifica versão antes de atualizar  
✅ **Rastreável**: Todas as versões ficam no GitHub Releases  
✅ **Fallback**: Se instalador falhar, atualiza arquivos individuais  
✅ **Backup**: Cria backup antes de atualizar  

## Arquivos Importantes

- **modules/updater.py**: Código de atualização automática
- **version.txt**: Versão atual (formato: `1.0.31`)
- **installer.iss**: Configuração do Inno Setup
- **app.manifest**: Manifesto do Windows
- **deploy.bat**: Script de deploy automático
- **build.bat**: Script de compilação

## Troubleshooting

### "Erro ao conectar"
- Verifique conexão com internet
- GitHub pode estar temporariamente indisponível

### "Instalador não encontrado"
- Verifique se fez upload do `.exe` na release do GitHub
- Nome do arquivo deve conter "setup" ou "busca_xml"

### Atualização não aparece
- Certifique-se de que:
  1. `version.txt` foi atualizado no GitHub
  2. Tag foi criada (ex: `v1.0.32`)
  3. Release foi publicada (não draft)
  4. Instalador foi anexado à release

## Dicas

💡 **Sempre teste** a atualização antes de publicar para todos  
💡 **Documente** mudanças na descrição da release  
💡 **Versão semântica**: MAJOR.MINOR.PATCH (ex: 1.0.32)  
💡 **Backup automático**: Sistema cria backup antes de atualizar  
💡 **Commit regularmente**: Facilita rastrear mudanças  

## Contato

Dúvidas? Abra uma issue no GitHub: https://github.com/W4lterBr/NF-e/issues
