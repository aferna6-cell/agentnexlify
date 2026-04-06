const tsParser = require("@typescript-eslint/parser");
const testQualityPlugin = require("./tools/eslint-plugin-agentnexlify-test-quality/index.cjs");

const TEST_FILE_PATTERNS = [
  "**/*.test.{js,jsx,ts,tsx}",
  "**/*.spec.{js,jsx,ts,tsx}",
  "**/__tests__/**/*.{js,jsx,ts,tsx}",
];

const TEST_GLOBALS = {
  beforeAll: "readonly",
  beforeEach: "readonly",
  afterAll: "readonly",
  afterEach: "readonly",
  describe: "readonly",
  expect: "readonly",
  it: "readonly",
  jest: "readonly",
  test: "readonly",
  vi: "readonly",
};

module.exports = [
  {
    ignores: [
      "**/node_modules/**",
      "**/dist/**",
      "**/.venv/**",
      "**/.pytest_cache/**",
      "**/coverage/**",
    ],
  },
  {
    files: TEST_FILE_PATTERNS,
    languageOptions: {
      parser: tsParser,
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: TEST_GLOBALS,
    },
    plugins: {
      "agentnexlify-test-quality": testQualityPlugin,
    },
    rules: {
      "agentnexlify-test-quality/no-mock-echo-implementation": "error",
      "agentnexlify-test-quality/no-interaction-only-tests": "error",
      "agentnexlify-test-quality/no-trivial-test-assertions": "error",
    },
  },
];
