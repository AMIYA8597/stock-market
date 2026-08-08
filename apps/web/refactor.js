const fs = require('fs');
const files = [
  'src/components/charts/LightweightCandlestickChart.tsx',
  'src/components/charts/tradingview/indicatorsRenderer.ts',
  'src/components/charts/tradingview/smcRenderer.ts',
  'src/components/charts/tradingview/subpaneRenderer.ts'
];
for (const file of files) {
  let content = fs.readFileSync(file, 'utf8');
  content = content.replace(/\.addCandlestickSeries\(/g, '.addSeries(CandlestickSeries, ');
  content = content.replace(/\.addLineSeries\(/g, '.addSeries(LineSeries, ');
  content = content.replace(/\.addAreaSeries\(/g, '.addSeries(AreaSeries, ');
  content = content.replace(/\.addHistogramSeries\(/g, '.addSeries(HistogramSeries, ');
  content = content.replace(/\.addBaselineSeries\(/g, '.addSeries(BaselineSeries, ');
  
  if (content.includes('addSeries(')) {
    const importsToAdd = ['CandlestickSeries', 'LineSeries', 'AreaSeries', 'HistogramSeries', 'BaselineSeries']
      .filter(imp => content.includes(imp + ',') || content.includes(imp + ')'));
    
    if (importsToAdd.length > 0) {
      if (content.includes('import {')) {
        content = content.replace(/import\s+{([^}]*)}\s+from\s+[\"']lightweight-charts[\"'];/g, (match, p1) => {
          let newImports = p1;
          for (const imp of importsToAdd) {
            if (!newImports.includes(imp)) {
              newImports += ', ' + imp;
            }
          }
          return `import {${newImports}} from 'lightweight-charts';`;
        });
      } else {
         content = `import { ${importsToAdd.join(', ')} } from 'lightweight-charts';\n` + content;
      }
    }
  }
  fs.writeFileSync(file, content);
}
console.log('Done');
