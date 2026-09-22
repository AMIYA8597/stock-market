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
  test('No live trading endpoints or console dot log in source tree', () => {
    const srcDir = path.resolve(__dirname, '..');
    const files = findFiles(srcDir, '.ts').concat(findFiles(srcDir, '.tsx'));
    
    let badStringsFound = 0;
    const p1 = 'trading/' + 'mode';
    const p2 = 'setTrading' + 'Mode';
    const p3 = 'ups' + 'tox';
    const p4 = '\\\\?\\\\? 0\\\\.5';
    const p5 = '0\\\\.85';
    const p6 = 'console\\\\.' + 'log';
    const pattern = new RegExp([p1, p2, p3, p4, p5, p6].join('|'));
    
    for (const file of files) {
      const content = fs.readFileSync(file, 'utf-8');
      if (content.match(pattern)) {
        if (!file.includes('safety.test.ts')) {
          badStringsFound++;
          console.error('Found restricted string in ' + file);
        }
      }
    }
    
    expect(badStringsFound).toBe(0);
  });
});