# Changelog

Mudanças de cada versão do Lembreme. Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/); as versões seguem [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não lançado]

### Segurança
- Electron 44.7.0 → 44.10.0 (correção de certificados intermediários eMudhra comprometidos). Dependências de build atualizadas (undici, fast-uri).

## [0.3.1] - 2026-10-28

Primeira versão pública.

### Adicionado
- Licença MIT e avisos de terceiros (ícones Lucide, fontes Geist, Electron), incluídos no instalador.
- README com download, privacidade e o aviso do SmartScreen.
- Instalador gerado e publicado automaticamente a cada tag `v*`.

### Corrigido
- Um `lembretes.json` corrompido não é mais sobrescrito com uma lista vazia: o app guarda uma cópia `lembretes.json.corrompido-<data>` antes de começar de novo.
- Descrição do app com acentuação quebrada.

## [0.3.0] - 2026-10-18

Versão de uso pessoal, não publicada.

### Adicionado
- Tipos de lembrete (conta, fatura, imposto, saúde...) sugeridos pelo texto, com cor, ícone e filtro.
- Ícone e tema ciano próprios.

### Corrigido
- Iniciar com o Windows pela pasta Inicializar.
- O app não bloqueia mais o desligamento do Windows.

[Não lançado]: https://github.com/mateusvpassos/lembreme/compare/v0.3.1...HEAD
[0.3.1]: https://github.com/mateusvpassos/lembreme/releases/tag/v0.3.1
