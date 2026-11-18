// SPDX-License-Identifier: AGPL-3.0-only
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, cpSync, writeFileSync, readFileSync, rmSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { execFileSync } from 'node:child_process';
import { verifyBackport } from './picomatch-backport.mjs';

test('installed parser is hash-bound and exploit/ordinary-glob tests pass', () => {
  assert.equal(verifyBackport().status, 'VERIFIED_LOCAL_BACKPORT');
});

test('changed installed bytes fail verification', t => {
  const path = mkdtempSync(join(tmpdir(), 'lgxt-parser-tamper-'));
  t.after(() => rmSync(path, { recursive: true }));
  cpSync(resolve('node_modules/picomatch'), path, { recursive: true });
  writeFileSync(join(path, 'lib/parse.js'), 'changed');
  assert.throws(() => verifyBackport(false, [path]), /Unpatched or changed/);
});

test('original upstream parser reproduces the exploit within a bounded process', t => {
  const path = mkdtempSync(join(tmpdir(), 'lgxt-parser-original-'));
  t.after(() => rmSync(path, { recursive: true }));
  cpSync(resolve('node_modules/picomatch'), path, { recursive: true });
  const file = join(path, 'lib/parse.js');
  const patched = readFileSync(file, 'utf8');
  const start = patched.indexOf('  // GHSA-fc5q-39xc-vjpf:');
  const end = patched.indexOf('  if (branches.length > 1)', start);
  assert.ok(start > 0 && end > start);
  writeFileSync(file, patched.slice(0, start) + patched.slice(end));
  assert.throws(() => execFileSync(process.execPath, ['-e',
    "require(process.argv[1]).isMatch('a'.repeat(64)+'!', '+(*a)')", path],
    { timeout: 1500, stdio: 'pipe' }), error => error.code === 'ETIMEDOUT');
});
