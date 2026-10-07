# Lembreme

Lembretes no desktop (Windows). Escreve em português, popup no canto inferior direito na hora.

## Instalar (deps + iniciar com o Windows)
    powershell -ExecutionPolicy Bypass -File instalar.ps1

## Rodar
    pythonw lembreme.pyw

## Uso
Preenche **O que lembrar**, escolhe **dia/hora** (ou atalho: Em 10 min, Em 1 hora, Hoje 18:00, Amanhã 09:00), **Repetir** se for conta fixa, **+ Adicionar**.
Duplo clique na lista edita. Hora aceita `09:00`, `9h`, `9`.

Fica na bandeja (sino azul perto do relógio): clique abre a janela, botão direito → Testar popup / Sair. Fechar a janela só esconde.
Dados: `%APPDATA%\Lembreme\lembreme.db`. Lembretes perdidos com PC desligado aparecem ao abrir (marcados "atrasado").

## Testes
    python -m pytest -q
