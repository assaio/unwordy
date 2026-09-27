import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

let count = 0;
for (const surface of readdirSync('evals', { withFileTypes: true })) {
  if (!surface.isDirectory() || surface.name === 'results') continue;
  const directory = join('evals', surface.name, 'graders');
  for (const file of readdirSync(directory)) {
    const text = readFileSync(join(directory, file), 'utf8');
    if (!/^type: regex$/m.test(text)) continue;
    const raw = text.match(/^pattern: (.+)$/m)?.[1];
    if (!raw) throw new Error(`${file}: missing pattern`);
    const pattern = raw.startsWith("'") ? raw.slice(1, -1).replaceAll("''", "'") : raw;
    const flags = text.match(/^flags: (.+)$/m)?.[1] ?? '';
    const regex = new RegExp(pattern, flags);
    if (file.startsWith('retains-') && regex.test('')) {
      throw new Error(`${file}: empty answer passed the fact check`);
    }
    count++;
  }
}
console.log(`Compiled ${count} JavaScript regex graders; positive fact checks reject empty answers.`);
