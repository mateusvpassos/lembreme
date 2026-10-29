# Lembreme

Lembretes no desktop (Windows) com aviso no canto da tela. Electron, mesma família visual do Kino e do Strata.

*Desktop reminders for Windows with a corner notification. The interface is in Brazilian Portuguese.*

## Baixar

Instalador em [Releases](https://github.com/mateusvpassos/lembreme/releases) (`Lembreme-Setup-<versão>.exe`). O instalador não é assinado, então o Windows pode mostrar o aviso do SmartScreen: clique em **Mais informações → Executar assim mesmo**.

## Recursos
- **Formulário:** o que lembrar, dia, hora, atalhos (Em 10 min, Em 1 hora, Hoje 18:00, Amanhã 09:00, Segunda 09:00) e repetição (uma vez, diário, semanal, mensal, anual)
- **Resumo ao vivo:** mostra em português quando vai avisar e como repete
- **Tipos:** conta, fatura, imposto, parcela, saúde, trabalho, compromisso, pessoal, outro — sugerido pelo texto ("luz", "INSS", "cartão"...), com cor/ícone e filtro na lista
- **Lista agrupada:** atrasados, hoje, amanhã, próximos 7 dias, mais adiante; aba de concluídos
- **Editar** clicando no item; **excluir com desfazer**
- **Aviso no canto inferior direito:** som curto, empilha vários, adiar 10 min / 1 h / amanhã 9h
- **Bandeja:** fechar a janela só esconde; menu com testar aviso, iniciar com o Windows e sair
- **Mensal no dia 31** cai no último dia dos meses curtos e volta pro 31 depois
- Lembretes perdidos com o PC desligado aparecem ao abrir, marcados como atrasados

## Privacidade

O Lembreme funciona offline: não tem conta, não envia nada pela internet e não coleta dados de uso. Os lembretes ficam só no seu computador, em `%APPDATA%\Lembreme\lembretes.json` (a versão Python antiga, `lembreme.db`, é migrada automaticamente). Para apagar tudo, desinstale e remova essa pasta. Se o arquivo estiver corrompido, o app guarda uma cópia (`lembretes.json.corrompido-*`) antes de começar uma lista nova.

Na primeira execução do app instalado, a opção **Iniciar com o Windows** fica ligada (atalho na pasta Inicializar). Ela pode ser desligada pelo menu da bandeja.

## Atalhos
`Enter` salva · `Esc` cancela edição · `Ctrl+N` novo · `Delete` exclui o item focado

## Rodar
```bash
npm install
npm start
```

## Gerar instalador
```bash
npm run dist
```
Saída em `dist/Lembreme-Setup-<versão>.exe`. Usa o Electron do `node_modules` (`electronDist`), sem baixar do GitHub. Log em `%APPDATA%\Lembreme\lembreme.log`.

Ícone: `assets/icon.svg` → `npm run icon` gera `renderer/icon.png`. Testes: `npm test`.

Publicar uma versão: suba a versão no `package.json` e crie a tag (`git tag v0.3.0 && git push origin v0.3.0`). O workflow `release.yml` roda os testes, gera o instalador e cria a Release.

## Licença

MIT ([LICENSE](LICENSE)). Fontes Geist (OFL 1.1) e ícones Lucide (ISC): ver [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
