#!/usr/bin/env node
// Mechanically converts the frozen backend OpenAPI artefact into TypeScript types.
// No hand-authored field lists: every property name/type/optionality comes straight
// from backend/contract/openapi.v1.json. Re-run via `npm run generate:contract-types`
// whenever the backend re-freezes the contract; the contract-freeze test fails if the
// committed output drifts from what this script would produce.

import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '..', '..');
const openapiPath = resolve(repoRoot, 'backend', 'contract', 'openapi.v1.json');
const outputPath = resolve(here, '..', 'src', 'api', 'generated', 'openapi-types.ts');

function refName(ref) {
  return ref.split('/').pop();
}

function typeForSchema(schema) {
  if (!schema) return 'unknown';
  if (schema.$ref) return refName(schema.$ref);

  if (schema.anyOf) {
    return schema.anyOf.map((entry) => typeForSchema(entry)).join(' | ');
  }
  if (schema.allOf) {
    return schema.allOf.map((entry) => typeForSchema(entry)).join(' & ');
  }
  if (schema.const !== undefined) {
    return JSON.stringify(schema.const);
  }
  if (schema.enum) {
    return schema.enum.map((value) => JSON.stringify(value)).join(' | ');
  }

  switch (schema.type) {
    case 'null':
      return 'null';
    case 'string':
      return 'string';
    case 'integer':
    case 'number':
      return 'number';
    case 'boolean':
      return 'boolean';
    case 'array':
      return `(${typeForSchema(schema.items)})[]`;
    case 'object': {
      if (schema.properties) return objectLiteral(schema);
      if (schema.additionalProperties === true) return 'Record<string, unknown>';
      if (schema.additionalProperties && typeof schema.additionalProperties === 'object') {
        return `Record<string, ${typeForSchema(schema.additionalProperties)}>`;
      }
      return 'Record<string, unknown>';
    }
    default:
      return 'unknown';
  }
}

function objectLiteral(schema) {
  const required = new Set(schema.required ?? []);
  const properties = schema.properties ?? {};
  const fields = Object.keys(properties).map((name) => {
    const optional = required.has(name) ? '' : '?';
    return `  ${JSON.stringify(name)}${optional}: ${typeForSchema(properties[name])};`;
  });
  return `{\n${fields.join('\n')}\n}`;
}

function emitInterface(name, schema) {
  const lines = [];
  if (schema.description) {
    lines.push('/**');
    for (const line of schema.description.split('\n')) lines.push(` * ${line}`);
    lines.push(' */');
  }
  lines.push(`export interface ${name} ${objectLiteral(schema)}`);
  return lines.join('\n');
}

export function generate() {
  const openapi = JSON.parse(readFileSync(openapiPath, 'utf-8'));
  const schemas = openapi.components?.schemas ?? {};
  const names = Object.keys(schemas).sort();

  const header = [
    '// GENERATED FILE — do not hand-edit.',
    `// Source: backend/contract/openapi.v1.json (contract version ${openapi.info?.version ?? 'unknown'}).`,
    '// Regenerate with `npm run generate:contract-types` after the backend re-freezes the contract.',
    '',
  ].join('\n');

  const body = names
    .map((name) => emitInterface(name, schemas[name]))
    .join('\n\n');

  const pathEntries = [];
  for (const [path, operations] of Object.entries(openapi.paths ?? {})) {
    for (const [method, operation] of Object.entries(operations)) {
      const responseSchema =
        operation.responses?.['200']?.content?.['application/json']?.schema ??
        operation.responses?.['201']?.content?.['application/json']?.schema;
      const requestSchema = operation.requestBody?.content?.['application/json']?.schema;
      pathEntries.push({
        method: method.toUpperCase(),
        path,
        operationId: operation.operationId,
        request: requestSchema ? typeForSchema(requestSchema) : null,
        response: responseSchema ? typeForSchema(responseSchema) : null,
      });
    }
  }
  const pathsTable = [
    'export type ContractOperation = {',
    '  method: string;',
    '  path: string;',
    '  operationId: string;',
    '  request: string | null;',
    '  response: string | null;',
    '};',
    '',
    'export const CONTRACT_OPERATIONS: readonly ContractOperation[] = ' +
      JSON.stringify(
        pathEntries.sort((a, b) => (a.path + a.method).localeCompare(b.path + b.method)),
        null,
        2,
      ) +
      ' as const;',
  ].join('\n');

  return `${header}\n${body}\n\n${pathsTable}\n`;
}

function main() {
  const content = generate();
  writeFileSync(outputPath, content);
  console.log(`Wrote ${outputPath}`);
}

const isMain = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) main();
