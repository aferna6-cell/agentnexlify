"use strict";

const EQUALITY_MATCHERS = new Set(["toBe", "toEqual", "toStrictEqual"]);

function getPropertyName(memberExpression) {
  if (!memberExpression || memberExpression.type !== "MemberExpression") {
    return null;
  }
  if (!memberExpression.computed && memberExpression.property.type === "Identifier") {
    return memberExpression.property.name;
  }
  if (memberExpression.computed && memberExpression.property.type === "Literal") {
    return String(memberExpression.property.value);
  }
  return null;
}

function getExpectDetails(callExpression) {
  if (!callExpression || callExpression.type !== "CallExpression") {
    return null;
  }

  let current = callExpression.callee;
  const chain = [];
  while (current && current.type === "MemberExpression") {
    const propertyName = getPropertyName(current);
    if (!propertyName) {
      return null;
    }
    chain.push(propertyName);
    current = current.object;
  }

  if (
    !current ||
    current.type !== "CallExpression" ||
    current.callee.type !== "Identifier" ||
    current.callee.name !== "expect" ||
    chain.length === 0
  ) {
    return null;
  }

  return {
    matcherName: chain[0],
    expectCall: current,
  };
}

function sameSourceText(context, left, right) {
  // ESLint 10 removed context.getSourceCode(); context.sourceCode is the
  // replacement (available since v8.40). Keep the old call as a fallback so
  // the rule still works if anything pins ESLint <8.40.
  const sourceCode =
    context.sourceCode ||
    (typeof context.getSourceCode === "function" && context.getSourceCode());
  return sourceCode.getText(left) === sourceCode.getText(right);
}

function isLiteralTrue(node) {
  return node && node.type === "Literal" && node.value === true;
}

function isLiteralFalse(node) {
  return node && node.type === "Literal" && node.value === false;
}

module.exports = {
  meta: {
    type: "problem",
    docs: {
      description: "Disallow tautological/trivial assertions that do not validate behavior.",
    },
    schema: [],
    messages: {
      trivialAssertion:
        "This assertion is tautological and does not validate behavior. Assert against a meaningful expected outcome instead.",
    },
  },
  create(context) {
    return {
      CallExpression(node) {
        const details = getExpectDetails(node);
        if (!details) {
          return;
        }

        const actual = details.expectCall.arguments[0];
        const expected = node.arguments[0];
        if (!actual) {
          return;
        }

        if (
          EQUALITY_MATCHERS.has(details.matcherName) &&
          expected &&
          sameSourceText(context, actual, expected)
        ) {
          context.report({ node, messageId: "trivialAssertion" });
          return;
        }

        if (details.matcherName === "toBeTruthy" && isLiteralTrue(actual)) {
          context.report({ node, messageId: "trivialAssertion" });
          return;
        }

        if (details.matcherName === "toBeFalsy" && isLiteralFalse(actual)) {
          context.report({ node, messageId: "trivialAssertion" });
        }
      },
    };
  },
};
