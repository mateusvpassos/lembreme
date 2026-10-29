# Contribuir

Sugestões e correções são bem-vindas.

- **Bug ou ideia:** abra uma [issue](https://github.com/mateusvpassos/lembreme/issues/new/choose) usando o modelo.
- **Falha de segurança:** siga o [SECURITY.md](SECURITY.md), não abra issue pública.

## Pull requests

1. Para mudanças grandes, abra uma issue antes para combinar a ideia.
2. Rode localmente:
   ```bash
   npm install
   npm start
   npm test
   ```
   Para não mexer nos seus lembretes reais, use uma pasta de dados separada: `set LEMBREME_DATA=C:\temp\lembreme-dev` antes do `npm start`.
3. Mantenha o estilo do código (JavaScript simples, sem framework, sem build) e a interface em português.
4. Anote a mudança em `CHANGELOG.md`, na seção **Não lançado**.

Ao enviar um pull request, você concorda que a contribuição é licenciada sob a [licença MIT](LICENSE) do projeto.
