# Lembreme

Lembretes no desktop (Windows) com aviso no canto da tela. Electron, mesma família visual do Kino e do Strata.

## Recursos
- **Formulário:** o que lembrar, dia, hora, atalhos (Em 10 min, Em 1 hora, Hoje 18:00, Amanhã 09:00, Segunda 09:00) e repetição (uma vez, diário, semanal, mensal, anual)
- **Resumo ao vivo:** mostra em português quando vai avisar e como repete
- **Lista agrupada:** atrasados, hoje, amanhã, próximos 7 dias, mais adiante; aba de concluídos
- **Editar** clicando no item; **excluir com desfazer**
- **Aviso no canto inferior direito:** som curto, empilha vários, adiar 10 min / 1 h / amanhã 9h
- **Bandeja:** fechar a janela só esconde; menu com testar aviso, iniciar com o Windows e sair
- **Mensal no dia 31** cai no último dia dos meses curtos e volta pro 31 depois
- Lembretes perdidos com o PC desligado aparecem ao abrir, marcados como atrasados

Dados em `%APPDATA%\Lembreme\lembretes.json` (migra automaticamente a versão Python antiga, `lembreme.db`).

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
Saída em `dist/Lembreme-Setup-<versão>.exe`. Instalado, liga "Iniciar com o Windows" na primeira execução.

Ícone: `assets/icon.svg` → `npm run icon` gera `renderer/icon.png`. Testes: `npm test`.
