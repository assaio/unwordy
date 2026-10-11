import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

let count = 0;
let probes = 0;
for (const surface of readdirSync('evals', { withFileTypes: true })) {
  if (!surface.isDirectory() || surface.name === 'results') continue;
  const directory = join('evals', surface.name, 'graders');
  const graders = new Map();
  for (const file of readdirSync(directory)) {
    const text = readFileSync(join(directory, file), 'utf8');
    if (!/^type: regex$/m.test(text)) continue;
    const raw = text.match(/^pattern: (.+)$/m)?.[1];
    if (!raw) throw new Error(`${file}: missing pattern`);
    const pattern = raw.startsWith("'") ? raw.slice(1, -1).replaceAll("''", "'") : raw;
    const flags = text.match(/^flags: (.+)$/m)?.[1] ?? '';
    const regex = new RegExp(pattern, flags);
    const negative = /^match: not_contains$/m.test(text);
    const passes = output => {
      regex.lastIndex = 0;
      return regex.test(output) !== negative;
    };
    if (!negative && passes('')) {
      throw new Error(`${file}: empty answer passed the fact check`);
    }
    graders.set(file, passes);
    count++;
  }
  const checks = join('evals', surface.name, 'checks.json');
  if (!existsSync(checks)) continue;
  const fixtures = JSON.parse(readFileSync(checks, 'utf8'));
  for (const output of fixtures.accepted) {
    for (const [name, passes] of graders) {
      if (!passes(output)) throw new Error(`${surface.name}/${name}: valid output rejected`);
      probes++;
    }
  }
  for (const fixture of fixtures.rejected) {
    for (const name of fixture.graders) {
      if (!graders.has(name)) throw new Error(`${surface.name}: unknown grader ${name}`);
      if (graders.get(name)(fixture.output)) throw new Error(`${surface.name}/${name}: invalid output accepted`);
      probes++;
    }
  }
}
console.log(`Compiled ${count} JavaScript regex graders; ${probes} behavior checks passed.`);
