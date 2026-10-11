import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const html = readFileSync(new URL('../docs/index.html', import.meta.url), 'utf8');
const elements = new Map();
const choices = new Map();
for (const [, id, options] of html.matchAll(/<select id="([^"]+)">([\s\S]*?)<\/select>/g)) {
  const values = [...options.matchAll(/<option value="([^"]+)">/g)].map(match => match[1]);
  choices.set(id, values);
  elements.set(id, { value: values[0], addEventListener(event, callback) {
    assert.equal(event, 'change');
    this.change = callback;
  } });
}
for (const id of ['source', 'result']) elements.set(id, {});
const script = html.match(/<script>([\s\S]*?)<\/script>/);
assert.ok(script, 'demo script is missing');
vm.runInNewContext(script[1], { document: { getElementById: id => elements.get(id) } });

let count = 0;
for (const role of choices.get('role')) {
  for (const tone of choices.get('tone')) {
    for (const language of choices.get('language')) {
      for (const [id, value] of Object.entries({ role, tone, language })) {
        const element = elements.get(id);
        element.value = value;
        element.change();
      }
      const source = elements.get('source'), result = elements.get('result');
      const context = `${role}/${tone}/${language}`;
      assert.ok(source.textContent?.trim(), `${context}: empty source`);
      assert.ok(result.textContent?.trim(), `${context}: empty output`);
      assert.equal(source.lang, language, context);
      assert.equal(result.lang, language, context);
      const numbers = text => [...text.matchAll(/\d+(?:\.\d+)*/g)].map(match => match[0]).sort();
      assert.deepEqual(numbers(result.textContent), numbers(source.textContent), `${context}: numbers changed`);
      for (const identifier of ['AUTH-409', 'Marta', 'API']) {
        if (source.textContent.includes(identifier)) assert.ok(result.textContent.includes(identifier), context);
      }
      count++;
    }
  }
}
assert.equal(count, 84);
console.log(`${count} demo selections passed: rendering, language and supplied numbers/identifiers`);
