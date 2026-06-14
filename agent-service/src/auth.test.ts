import { test } from 'node:test';
import assert from 'node:assert/strict';
import { isTokenAuthorized } from './auth.ts';

test('open mode: empty expected token allows any request', () => {
  assert.equal(isTokenAuthorized(undefined, ''), true);
  assert.equal(isTokenAuthorized('whatever', ''), true);
});

test('matching token is authorized', () => {
  assert.equal(isTokenAuthorized('s3cret', 's3cret'), true);
});

test('missing token is rejected when one is expected', () => {
  assert.equal(isTokenAuthorized(undefined, 's3cret'), false);
});

test('wrong token is rejected when one is expected', () => {
  assert.equal(isTokenAuthorized('nope', 's3cret'), false);
});

test('array-valued header uses the first value', () => {
  assert.equal(isTokenAuthorized(['s3cret', 'extra'], 's3cret'), true);
  assert.equal(isTokenAuthorized(['nope', 's3cret'], 's3cret'), false);
});
