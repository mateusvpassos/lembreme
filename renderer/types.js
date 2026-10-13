// Tipos de lembrete (cor + ícone) e sugestão automática pelo texto. Usado na janela, no popup e no main.
const TYPES = {
  conta: { label: 'Conta', icon: 'receipt', color: '#ffbf47' },
  fatura: { label: 'Fatura', icon: 'creditCard', color: '#ff6fa8' },
  imposto: { label: 'Imposto', icon: 'landmark', color: '#ff8a4c' },
  parcela: { label: 'Parcela', icon: 'coins', color: '#b48cff' },
  saude: { label: 'Saúde', icon: 'heart', color: '#ff5d6c' },
  trabalho: { label: 'Trabalho', icon: 'briefcase', color: '#6f8bff' },
  compromisso: { label: 'Compromisso', icon: 'calendar', color: '#22c3e6' },
  pessoal: { label: 'Pessoal', icon: 'user', color: '#3ddc97' },
  outro: { label: 'Outro', icon: 'tag', color: '#8b90a4' }
};

const TYPE_WORDS = {
  fatura: ['fatura', 'cartao', 'cartao de credito', 'nubank', 'credito'],
  imposto: ['inss', 'imposto', 'impostos', 'das', 'darf', 'ipva', 'iptu', 'irpf', 'imposto de renda', 'nota fiscal', 'nf', 'mei', 'gps'],
  parcela: ['emprestimo', 'parcela', 'financiamento', 'consorcio', 'prestacao', 'carne', 'boleto'],
  conta: ['conta', 'luz', 'agua', 'energia', 'internet', 'telefone', 'celular', 'tim', 'vivo', 'claro', 'gas',
    'aluguel', 'condominio', 'habitacao', 'net', 'streaming', 'netflix', 'spotify', 'mensalidade', 'escola'],
  saude: ['saude', 'plano de saude', 'medico', 'medica', 'dentista', 'remedio', 'consulta', 'exame', 'vacina', 'terapia'],
  trabalho: ['reuniao', 'relatorio', 'trabalho', 'cliente', 'entrega', 'deploy', 'daily', 'sprint', 'ponto'],
  pessoal: ['academia', 'treino', 'mercado', 'compras', 'cabelo', 'barbeiro', 'casa', 'limpeza', 'carro', 'lavar'],
  compromisso: ['aniversario', 'festa', 'viagem', 'casamento', 'missa', 'encontro', 'evento', 'buscar', 'levar']
};

const normText = s => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');

// devolve o tipo cuja palavra aparece primeiro no texto (ou null)
function guessType(text) {
  const t = ` ${normText(text).replace(/[^a-z0-9]+/g, ' ')} `;
  let best = null, pos = Infinity;
  for (const [type, words] of Object.entries(TYPE_WORDS)) {
    for (const w of words) {
      const i = t.indexOf(` ${w} `);
      if (i >= 0 && i < pos) { best = type; pos = i; }
    }
  }
  return best;
}

if (typeof module !== 'undefined') module.exports = { TYPES, guessType };
