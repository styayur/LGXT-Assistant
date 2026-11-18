// SPDX-License-Identifier: AGPL-3.0-only
// Retain the raw advisory. Only hash-verified installed remediation qualifies it.
import { spawnSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { relative } from 'node:path';
import { verifyBackport } from './picomatch-backport.mjs';

const result = spawnSync('npm audit --json', { shell: true, encoding: 'utf8', timeout: 60000 });
if (result.error || ![0, 1].includes(result.status)) throw Error('npm audit execution failed');
writeFileSync('npm-audit.raw.json', result.stdout);
const report = JSON.parse(result.stdout);
if (report.auditReportVersion !== 2 || !report.metadata?.vulnerabilities || report.error) throw Error('Incomplete npm audit');
const findings = Object.values(report.vulnerabilities ?? {});
if (!findings.length) {
  console.log('npm audit: no current advisories');
} else {
  const verified = verifyBackport();
  const installed = new Set(verified.copies.map(path => relative(process.cwd(), path).replaceAll('\\', '/')));
  const lock = JSON.parse(readFileSync('package-lock.json'));
  const graph = new Set(['picomatch', 'fdir', 'tinyglobby', 'vite']);
  let advisory = false;
  for (const item of findings) {
    if (!graph.has(item.name) || item.severity !== 'high' || !item.nodes?.length || !item.via?.length) throw Error('Unresolved npm vulnerability: ' + item.name);
    if (item.nodes.some(path => lock.packages[path]?.dev !== true)) throw Error('Backport is restricted to the verified development dependency graph');
    for (const via of item.via) {
      if (typeof via === 'string') {
        if (!graph.has(via)) throw Error('Unknown audit dependency: ' + via);
      } else {
        if (via.name !== 'picomatch' || via.url !== 'https://github.com/advisories/GHSA-fc5q-39xc-vjpf') throw Error('Unresolved npm advisory: ' + via.url);
        advisory = true;
      }
    }
    if (item.name === 'picomatch' && item.nodes.some(path => !installed.has(path))) throw Error('Audit includes an unverified parser');
  }
  if (!advisory) throw Error('Backport cannot qualify unrelated findings');
  console.log(JSON.stringify({ ...verified, rawAudit: 'npm-audit.raw.json', upstreamFixed: false }));
}
