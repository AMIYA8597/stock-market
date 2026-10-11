// @vitest-environment node
import { describe, test, expect } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

function findFiles(dir: string, extension: string, fileList: string[] = []): string[] {
  const files = fs.readdirSync(dir);
  for (const file of files) {
    const filePath = path.join(dir, file);
    if (fs.statSync(filePath).isDirectory()) {
      if (file !== 'node_modules' && file !== '.next') {
        findFiles(filePath, extension, fileList);
      }
    } else if (filePath.endsWith(extension)) {
      fileList.push(filePath);
    }
  }
  return fileList;
}

describe('Safety Guard Rails', () => {
  test('No live trading order endpoints, mode mutation, fake defaults, or console logging in source tree', () => {
    const srcDir = path.resolve(__dirname, '..');
    const files = findFiles(srcDir, '.ts').concat(findFiles(srcDir, '.tsx'));

    const violations: string[] = [];
    const p1 = 'trading/' + 'order';
    const p2 = 'setTrading' + 'Mode';
    const p3 = '\\?\\?\\s*0\\.5';
    const p4 = 'return\\s+0\\.85';
    const p5 = 'console\\.' + 'log';
    const pattern = new RegExp([p1, p2, p3, p4, p5].join('|'));

    for (const file of files) {
      if (file.includes('safety.test.ts')) continue;
      const content = fs.readFileSync(file, 'utf-8');
      const lines = content.split('\n');
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (line && pattern.test(line)) {
          violations.push(`${file}:${i + 1}: ${line.trim()}`);
        }
      }
    }

    expect(violations).toEqual([]);
  });
});