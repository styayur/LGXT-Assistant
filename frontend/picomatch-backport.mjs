// SPDX-License-Identifier: AGPL-3.0-only
// Backport adopted from styayur/gitpad-plus with its provenance and bounded tests.
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync, readdirSync, existsSync } from 'node:fs';
import { resolve, join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const root = dirname(fileURLToPath(import.meta.url));
const hash = value => createHash('sha256').update(value).digest('hex');
const binding = JSON.parse(readFileSync(join(root, 'patches/picomatch-provenance.json')));
const patch = readFileSync(join(root, 'patches/picomatch@4.0.7.patch'));

function installed(directory = join(root, 'node_modules')) {
  const result = [];
  if (!existsSync(directory)) return result;
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    if (!entry.isDirectory() || entry.name.startsWith('.')) continue;
    const path = join(directory, entry.name);
    if (entry.name.startsWith('@')) {
      for (const scoped of readdirSync(path)) result.push(...installedPackage(join(path, scoped)));
    } else result.push(...installedPackage(path));
  }
  return result;
}
function installedPackage(path) {
  return [...(path.endsWith('/picomatch') || path.endsWith('\\picomatch') ? [path] : []),
    ...installed(join(path, 'node_modules'))];
}

export function verifyBackport(apply = false, copies = installed()) {
  if (binding.advisory !== 'GHSA-fc5q-39xc-vjpf' || hash(patch) !== binding.patchSha256) {
    throw Error('Backport patch/provenance mismatch');
  }
  if (!copies.length) throw Error('Missing installed picomatch inventory');
  for (const path of copies) {
    if (JSON.parse(readFileSync(join(path, 'package.json'))).version !== '4.0.7') throw Error('Unreviewed picomatch version');
    const parser = join(path, 'lib/parse.js');
    if (apply && hash(readFileSync(parser)) !== binding.installedSha256['lib/parse.js']) {
      const original = readFileSync(parser, 'utf8');
      const insertion = patch.toString().split('\n').filter(line => line.startsWith('+') && !line.startsWith('+++')).map(line => line.slice(1)).join('\n') + '\n';
      const anchor = '  if (branches.length > 1) {';
      if (original.split(anchor).length !== 2) throw Error('Unexpected upstream parser');
      const patched = original.replace(anchor, insertion + anchor);
      if (hash(Buffer.from(patched)) !== binding.installedSha256['lib/parse.js']) throw Error('Upstream parser differs from reviewed patch');
      writeFileSync(parser, patched);
    }
    for (const [file, expected] of Object.entries(binding.installedSha256)) {
      if (hash(readFileSync(join(path, file))) !== expected) throw Error('Unpatched or changed picomatch: ' + file);
    }
    execFileSync(process.execPath, ['--input-type=commonjs', '-e', `
      const assert = require('node:assert/strict');
      const pm = require(process.argv[1]);
      for (const pattern of ['+(*)', '*(*a)', '+(*a)', '*(a*)', '+(*?)', '+(*a|b)']) {
        assert.equal(pm.isMatch('a'.repeat(64) + '!', pattern), false, pattern);
        assert.equal(pm.isMatch(pattern, pattern), true, 'risky pattern remains literal');
      }
      for (const [value, pattern, expected] of [
        ['web/editor.ts', '**/*.ts', true], ['web/editor.js', '**/*.ts', false],
        ['abcabc', '+(abc)', true], ['foobar', '*(foo|bar)', true],
        ['abab', '+([ab])', true], ['aab', '+(*(a)|*(b))', true],
        ['abc', 'a?c', true], ['test.ts', '*.{ts,tsx}', true]
      ]) assert.equal(pm.isMatch(value, pattern), expected, pattern);
    `, path], { timeout: 3000, stdio: 'pipe' });
  }
  return { advisory: binding.advisory, status: 'VERIFIED_LOCAL_BACKPORT', copies: copies.map(path => resolve(path)) };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  console.log(JSON.stringify(verifyBackport(process.argv.includes('--apply'))));
}
