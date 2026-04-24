# 🚀 Guia Rápido de Build - Busca XML

## ⚡ Comandos Principais

| Comando | Descrição |
|---------|-----------|
| `validate_build.bat` | Valida ambiente antes de compilar |
| `build.bat` | **Compila executável + cria instalador** |
| `test_build.bat` | Testa executável após compilação |
| `update_version.bat` | Atualiza número de versão |
| `create_release.bat` | **Release completo automatizado** |

---

## 🎯 Fluxo Recomendado

### Para Desenvolvimento Local

```bash
# 1. Validar ambiente
validate_build.bat

# 2. Compilar
build.bat

# 3. Testar
test_build.bat
```

### Para Release Oficial

```bash
# 1. Atualizar versão
update_version.bat

# 2. Atualizar CHANGELOG.md (manual)

# 3. Release completo (tudo automatizado)
create_release.bat

# 4. Publicar no GitHub (manual)
```

---

## 📦 Estrutura de Saída

```
Output/
├── Busca_XML_Setup_v1.0.96.exe          # Instalador Windows
├── Busca_XML_Portable_v1.0.96.zip       # Versão portable
└── RELEASE_NOTES_v1.0.96.txt            # Notas de release

dist/
└── Busca XML/
    ├── Busca XML.exe                    # Executável principal
    └── _internal/                       # Bibliotecas e dependências
```

---

## ⚠️ Troubleshooting Rápido

| Problema | Solução |
|----------|---------|
| Python não encontrado | `python -m venv .venv` |
| PyInstaller erro | `pip install --upgrade pyinstaller` |
| Inno Setup não instalado | Baixar: https://jrsoftware.org/isdl.php |
| Logo.ico ausente | Colocar `Logo.png` na raiz |
| Erro de permissão | Executar como administrador |

---

## 🔧 Configurações Importantes

### Versão (`version.txt`)
```
1.0.96
```

### Instalador (`installer.iss`)
- Sincroniza versão automaticamente
- Compressão máxima por padrão
- Detecta Windows 10+

### PyInstaller (`BOT_Busca_NFE.spec`)
- Modo onedir (executável + _internal/)
- Console desabilitado (GUI)
- UPX habilitado (compressão)

---

## 📊 Checklist de Release

- [ ] Atualizar `version.txt`
- [ ] Atualizar `CHANGELOG.md`
- [ ] Executar `validate_build.bat`
- [ ] Executar `create_release.bat`
- [ ] Testar instalador em VM limpa
- [ ] Testar versão portable
- [ ] Criar tag Git: `git tag v1.0.96`
- [ ] Push: `git push origin main --tags`
- [ ] Criar release no GitHub
- [ ] Anexar arquivos de `Output/`
- [ ] Testar auto-update

---

## 🎨 Personalização

### Alterar Ícone
```bash
# Substituir Logo.png (512x512 recomendado)
# build.bat converterá automaticamente para .ico
```

### Alterar Compressão
Em `installer.iss`:
```inno
Compression=lzma2/max    # Máxima (padrão)
Compression=lzma2/fast   # Rápida
```

### Desabilitar UAC
Em `installer.iss`:
```inno
PrivilegesRequired=lowest
```

---

## 📝 Arquivos Críticos

| Arquivo | Função | Crítico? |
|---------|--------|----------|
| `Busca NF-e.py` | Aplicação principal | ✅ Sim |
| `BOT_Busca_NFE.spec` | Config PyInstaller | ✅ Sim |
| `version.txt` | Versão atual | ✅ Sim |
| `updater_launcher.py` | Auto-update | ⚠️ Recomendado |
| `Logo.ico` | Ícone | ⚠️ Opcional |
| `Arquivo_xsd/` | Schemas XML | ⚠️ Opcional |

---

## 🏃 Comandos Git Úteis

```bash
# Commit de nova versão
git add version.txt CHANGELOG.md
git commit -m "chore: bump version to 1.0.97"

# Criar tag
git tag v1.0.97
git push origin main --tags

# Ver tags
git tag -l

# Deletar tag (se necessário)
git tag -d v1.0.97
git push origin :refs/tags/v1.0.97
```

---

## 📞 Suporte

**Problemas no build?**
1. Execute `validate_build.bat` para diagnóstico
2. Consulte `BUILD_README.md` para detalhes
3. Abra issue no GitHub com logs completos

**Desenvolvido por:** DWM System Developer  
**GitHub:** https://github.com/W4lterBr/NF-e
