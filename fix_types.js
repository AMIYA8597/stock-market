const fs = require('fs');

const typesContent = fs.readFileSync('packages/types/src/index.ts.backup', 'utf8');

let newContent = `export * from "./zod-schemas";\n`;
newContent += `import { components } from "./api";\n`;
newContent += `export type { components } from "./api";\n\n`;
newContent += `type Schemas = components['schemas'];\n\n`;

// Copy over all manually defined types from backup
newContent += typesContent + "\n";

fs.writeFileSync('packages/types/src/index.ts', newContent);
console.log("Written index.ts");
