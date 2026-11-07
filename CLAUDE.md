# Lembreme

Lembretes no desktop com aviso no canto da tela. Público (MIT).

Electron (família visual Kino/Strata/Lembreme). Interface em português do Brasil.

## Comandos
```bash
npm start              # roda em dev
npm test               # recorrências (shared/recur.test.js)
npm run dist:dir       # build sem instalador
npm run dist           # instalador NSIS
```

## Regras
- Padrões da família (tela Sobre, licenças, instalação, teste via CDP) estão no CLAUDE.md global.
- Dados de teste isolados: `LEMBREME_DATA=<pasta temporária>`. Nunca mexa nos dados reais do usuário.
- Release: subir versão no package.json, tag `vX.Y.Z`, push (o workflow gera o instalador). Só com pedido do usuário.
- CHANGELOG.md alimenta as notas da Release.

## Fluxo
Ao terminar uma mudança: `npm test` (se houver), conferir a tela, commit + push na `main`. Se o app está instalado, gerar de novo e reinstalar (padrão no CLAUDE.md global).
