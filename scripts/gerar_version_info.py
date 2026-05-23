"""
Gera file_version_info.txt automaticamente a partir de version.txt
Metadados de versão do Windows para o executável
"""
from pathlib import Path

# Lê versão do version.txt
version_file = Path("version.txt")
if version_file.exists():
    version_str = version_file.read_text(encoding='utf-8').strip()
else:
    version_str = "1.0.0"

# Converte "1.0.96" para (1, 0, 96, 0)
parts = version_str.split('.')
while len(parts) < 4:
    parts.append('0')
    
file_version = tuple(int(p) for p in parts[:4])
product_version = file_version

#Gera o conteúdo do file_version_info.txt
content = f'''# UTF-8
#
# File version information for Windows executable
# Generated automatically from version.txt
#
VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
    # Set not needed items to zero 0.
    filevers={file_version},
    prodvers={product_version},
    # Contains a bitmask that specifies the valid bits 'flags'r
    mask=0x3f,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=0x0,
    # The operating system for which this file was designed.
    # 0x4 - NT and there is no need to change it.
    OS=0x40004,
    # The general type of file.
    # 0x1 - the file is an application.
    fileType=0x1,
    # The function of the file.
    # 0x0 - the function is not defined for this fileType
    subtype=0x0,
    # Creation date and time stamp.
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'DWM System Developer'),
        StringStruct(u'FileDescription', u'Busca XML - Sistema de Gerenciamento de Notas Fiscais Eletrônicas'),
        StringStruct(u'FileVersion', u'{version_str}'),
        StringStruct(u'InternalName', u'Busca XML'),
        StringStruct(u'LegalCopyright', u'© 2024-2026 DWM System Developer. Todos os direitos reservados.'),
        StringStruct(u'OriginalFilename', u'Busca XML.exe'),
        StringStruct(u'ProductName', u'Busca XML'),
        StringStruct(u'ProductVersion', u'{version_str}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''

# Salva o arquivo
output_file = Path("file_version_info.txt")
output_file.write_text(content, encoding='utf-8')

print(f"✅ file_version_info.txt gerado com sucesso!")
print(f"   Versão: {version_str}")
print(f"   FileVersion: {file_version}")
print(f"   Arquivo: {output_file.absolute()}")
