import assert from 'node:assert/strict';
import { test } from 'node:test';

import { firstNameOf } from '@/src/utils/display-name';

test('firstNameOf returns the first token of a full name', () => {
  assert.equal(firstNameOf('Yasindu Kularathne'), 'Yasindu');
});

test('firstNameOf collapses extra internal whitespace', () => {
  assert.equal(firstNameOf('  Yasindu   Kularathne  '), 'Yasindu');
});

test('firstNameOf returns a single-word name unchanged', () => {
  assert.equal(firstNameOf('Yass'), 'Yass');
});

test('firstNameOf returns an empty string unchanged', () => {
  assert.equal(firstNameOf(''), '');
  assert.equal(firstNameOf('   '), '');
});

test('firstNameOf handles a three-part name', () => {
  assert.equal(firstNameOf('Mary Jane Watson'), 'Mary');
});

test('firstNameOf capitalizes a lowercase name', () => {
  assert.equal(firstNameOf('yass'), 'Yass');
});

test('firstNameOf capitalizes only the first letter, leaving the rest as typed', () => {
  assert.equal(firstNameOf('mcKay'), 'McKay');
});
