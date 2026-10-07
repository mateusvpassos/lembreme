# Lembreme

Lembretes no desktop (Windows). Escreve em português, popup no canto inferior direito na hora.

## Instalar (deps + iniciar com o Windows)
    powershell -ExecutionPolicy Bypass -File instalar.ps1

## Rodar
    pythonw lembreme.pyw

## Exemplos
- `amanhã 8h ligar dentista`
- `10/10 9:00 pagar luz mensal`
- `em 30 min tirar bolo` / `daqui 2 horas varal`
- `toda segunda 7h academia`
- `todo dia 5 pagar aluguel` / `todo dia 22h remédio`
- `sexta às 18 cerveja` / `dia 20 IPVA` / `05/01 renovar CNH`

Sem hora → 09:00. Fica na bandeja (sino azul perto do relógio): clique abre a janela, botão direito → Testar popup / Sair. Fechar a janela só esconde.
Dados: `%APPDATA%\Lembreme\lembreme.db`. Lembretes perdidos com PC desligado aparecem ao abrir (marcados "atrasado").

## Testes
    python -m pytest -q
