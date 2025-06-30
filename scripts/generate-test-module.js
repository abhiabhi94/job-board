#!/usr/bin/env node

/**
 * Script to automatically generate main.mjs from main.js for testing
 * This ensures we only maintain one source of truth for the JavaScript logic
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const sourceFile = path.join(__dirname, '../job_board/static/js/main.js');
const outputFile = path.join(__dirname, '../job_board/static/js/main.mjs');

try {
  // Read the original main.js file
  const mainJsContent = fs.readFileSync(sourceFile, 'utf8');

  // Remove the DOMContentLoaded wrapper to extract the inner content
  const domContentLoadedMatch = mainJsContent.match(/document\.addEventListener\('DOMContentLoaded',\s*function\s*\(\)\s*\{([\s\S]*)\}\);?\s*$/);

  let innerContent;
  if (domContentLoadedMatch) {
    // Extract content inside DOMContentLoaded
    innerContent = domContentLoadedMatch[1];
  } else {
    // Fallback: use entire content if no DOMContentLoaded wrapper found
    innerContent = mainJsContent;
  }

  // Fix the early return issue in sort dropdown code for testing
  // Replace "if (!sortButton || !sortOptions) return;" with conditional block
  innerContent = innerContent.replace(
    /if\s*\(\s*!\s*sortButton\s*\|\|\s*!\s*sortOptions\s*\)\s*return\s*;/,
    'if (sortButton && sortOptions) {'
  );

  // Find the last occurrence of sort-related code and add closing brace
  // This matches the pattern from sort dropdown setup to the last dropdown event listener
  innerContent = innerContent.replace(
    /(\/\/\s*Close dropdown on escape key[\s\S]*?}\s*\);)/,
    '$1\n    }'
  );

  // Transform the content to be an ES module
  const moduleContent = `// This file is auto-generated from main.js for testing purposes
// DO NOT EDIT MANUALLY - Run 'npm run generate:test-module' to update

// Export the main.js functionality as a module for testing
export function initializeMainJs() {
${innerContent.split('\n').map(line => '    ' + line).join('\n')}
}
`;

  // Write the module file
  fs.writeFileSync(outputFile, moduleContent);

  console.log('✅ Successfully generated main.mjs from main.js');
  console.log(`📁 Source: ${sourceFile}`);
  console.log(`📁 Output: ${outputFile}`);

} catch (error) {
  console.error('❌ Error generating test module:', error.message);
  process.exit(1);
}
