import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { generate } from '../../../scripts/generate-contract-types.mjs';
import { isHealthReadyResponse } from '@/src/api/runtime-validation';
import { getComponentBDevelopmentFixture } from '@/src/api/component-b-api';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '..', '..', '..', '..');
const openapiPath = resolve(repoRoot, 'backend', 'contract', 'openapi.v1.json');
const metaPath = resolve(repoRoot, 'backend', 'contract', 'openapi.v1.meta.json');
const generatedTypesPath = resolve(here, '..', 'generated', 'openapi-types.ts');

test('the frontend checks its own copy of the frozen OpenAPI artefact against the backend checksum', () => {
  const raw = readFileSync(openapiPath);
  const meta = JSON.parse(readFileSync(metaPath, 'utf-8'));
  const digest = createHash('sha256').update(raw).digest('hex');
  assert.equal(digest, meta.checksum_sha256);
  assert.equal(meta.contract_version, 'v1');
});

test('the committed generated TypeScript types are not stale relative to the frozen artefact', () => {
  const committed = readFileSync(generatedTypesPath, 'utf-8');
  const freshlyGenerated = generate();
  assert.equal(committed, freshlyGenerated);
});

test('isHealthReadyResponse accepts the live /health/ready shape and fails closed on drift', () => {
  const openapi = JSON.parse(readFileSync(openapiPath, 'utf-8'));
  const schema = openapi.components.schemas.ReadinessResponse;

  const validSample = {
    status: 'ready',
    stage: 'infrastructure',
    request_id: 'req-1',
    checks: { database_connection: 'ok' },
  };
  for (const field of schema.required) {
    assert.ok(field in validSample, `sample is missing required field ${field}`);
  }
  assert.equal(isHealthReadyResponse(validSample), true);

  for (const field of schema.required) {
    const mutated = { ...validSample };
    delete (mutated as Record<string, unknown>)[field];
    assert.equal(
      isHealthReadyResponse(mutated),
      false,
      `dropping required field ${field} should fail closed`,
    );
  }
});

test('the Component B dev fixture cannot activate outside EXPO_PUBLIC_APP_ENV=development', () => {
  const originalAppEnv = process.env.EXPO_PUBLIC_APP_ENV;
  const originalFixture = process.env.EXPO_PUBLIC_COMPONENT_B_DEV_FIXTURE;
  try {
    process.env.EXPO_PUBLIC_COMPONENT_B_DEV_FIXTURE = 'resume';

    for (const appEnv of ['staging', 'production', undefined]) {
      if (appEnv === undefined) delete process.env.EXPO_PUBLIC_APP_ENV;
      else process.env.EXPO_PUBLIC_APP_ENV = appEnv;
      assert.equal(
        getComponentBDevelopmentFixture(),
        null,
        `fixture must be null when EXPO_PUBLIC_APP_ENV=${appEnv}`,
      );
    }

    process.env.EXPO_PUBLIC_APP_ENV = 'development';
    assert.equal(getComponentBDevelopmentFixture(), 'resume');
  } finally {
    if (originalAppEnv === undefined) delete process.env.EXPO_PUBLIC_APP_ENV;
    else process.env.EXPO_PUBLIC_APP_ENV = originalAppEnv;
    if (originalFixture === undefined) delete process.env.EXPO_PUBLIC_COMPONENT_B_DEV_FIXTURE;
    else process.env.EXPO_PUBLIC_COMPONENT_B_DEV_FIXTURE = originalFixture;
  }
});
