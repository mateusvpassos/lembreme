const test = require('node:test');
const assert = require('node:assert');
const { nextOccurrence, nextAfter, fromLocal } = require('./recur');

test('diária, semanal, anual', () => {
  assert.equal(nextOccurrence('2026-10-11T09:00', 'diaria'), '2026-10-12T09:00');
  assert.equal(nextOccurrence('2026-12-28T09:00', 'semanal'), '2027-01-04T09:00');
  assert.equal(nextOccurrence('2028-02-29T09:00', 'anual', 29), '2029-02-28T09:00');
  assert.equal(nextOccurrence('2026-10-11T09:00', 'unica'), null);
});

test('mensal no dia 31 não deriva', () => {
  let d = '2026-01-31T09:00';
  d = nextOccurrence(d, 'mensal', 31); assert.equal(d, '2026-02-28T09:00');
  d = nextOccurrence(d, 'mensal', 31); assert.equal(d, '2026-03-31T09:00');
  assert.equal(nextOccurrence('2026-12-10T08:30', 'mensal', 10), '2027-01-10T08:30');
});

test('nextAfter pula ocorrências perdidas', () => {
  const now = fromLocal('2026-10-11T10:00');
  assert.equal(nextAfter('2026-08-05T09:00', 'mensal', 5, now), '2026-11-05T09:00');
  assert.equal(nextAfter('2026-10-01T09:00', 'diaria', 1, now), '2026-10-12T09:00');
});
