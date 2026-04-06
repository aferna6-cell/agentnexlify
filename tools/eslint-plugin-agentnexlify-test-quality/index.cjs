"use strict";

module.exports = {
  rules: {
    "no-mock-echo-implementation": require("./rules/no-mock-echo-implementation.cjs"),
    "no-interaction-only-tests": require("./rules/no-interaction-only-tests.cjs"),
    "no-trivial-test-assertions": require("./rules/no-trivial-test-assertions.cjs"),
  },
};
