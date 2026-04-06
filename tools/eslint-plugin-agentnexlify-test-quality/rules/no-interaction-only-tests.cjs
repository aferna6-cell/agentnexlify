"use strict";

const TEST_ROOT_IDENTIFIERS = new Set(["it", "test"]);
const TEST_MODIFIERS = new Set(["only", "skip", "concurrent", "fails", "todo"]);
const INTERACTION_MATCHERS = new Set([
  "toBeCalled",
  "toBeCalledTimes",
  "toBeCalledWith",
  "toHaveBeenCalled",
  "toHaveBeenCalledTimes",
  "toHaveBeenCalledWith",
  "toHaveBeenLastCalledWith",
  "toHaveBeenNthCalledWith",
  "toHaveBeenCalledBefore",
  "toHaveBeenCalledAfter",
  "toHaveReturned",
  "toHaveReturnedTimes",
  "toHaveReturnedWith",
  "toHaveLastReturnedWith",
  "toHaveNthReturnedWith",
  "toReturn",
  "toReturnTimes",
  "toReturnWith",
  "toHaveBeenCalledOnce",
  "toHaveBeenCalledExactlyOnceWith",
]);

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

function isTestCalleeShape(callee) {
  if (!callee) {
    return false;
  }

  if (callee.type === "Identifier") {
    return TEST_ROOT_IDENTIFIERS.has(callee.name);
  }

  if (callee.type === "MemberExpression") {
    const propertyName = getPropertyName(callee);
    if (!propertyName || !TEST_MODIFIERS.has(propertyName)) {
      return false;
    }
    return isTestCalleeShape(callee.object);
  }

  if (callee.type === "CallExpression") {
    if (callee.callee.type !== "MemberExpression") {
      return false;
    }
    const propertyName = getPropertyName(callee.callee);
    if (propertyName !== "each") {
      return false;
    }
    return isTestCalleeShape(callee.callee.object);
  }

  return false;
}

function extractTestCallback(node) {
  if (!node || node.type !== "CallExpression") {
    return null;
  }
  if (!isTestCalleeShape(node.callee)) {
    return null;
  }

  for (let i = node.arguments.length - 1; i >= 0; i -= 1) {
    const arg = node.arguments[i];
    if (
      arg &&
      (arg.type === "ArrowFunctionExpression" || arg.type === "FunctionExpression")
    ) {
      return arg;
    }
  }
  return null;
}

function getExpectMatcherName(callExpression) {
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

  return chain[0];
}

function walk(node, visitor, rootFunctionNode, seenNodes = new WeakSet()) {
  if (!node || typeof node.type !== "string") {
    return;
  }
  if (seenNodes.has(node)) {
    return;
  }
  seenNodes.add(node);

  if (
    node !== rootFunctionNode &&
    (node.type === "FunctionExpression" ||
      node.type === "ArrowFunctionExpression" ||
      node.type === "FunctionDeclaration")
  ) {
    return;
  }

  visitor(node);

  for (const key of Object.keys(node)) {
    if (key === "parent") {
      continue;
    }
    const value = node[key];
    if (!value) {
      continue;
    }
    if (Array.isArray(value)) {
      for (const child of value) {
        if (child && typeof child.type === "string") {
          walk(child, visitor, rootFunctionNode, seenNodes);
        }
      }
      continue;
    }
    if (value && typeof value.type === "string") {
      walk(value, visitor, rootFunctionNode, seenNodes);
    }
  }
}

module.exports = {
  meta: {
    type: "problem",
    docs: {
      description:
        "Disallow tests that only assert mock/spies interaction and never assert observable outcomes.",
    },
    schema: [],
    messages: {
      interactionOnly:
        "This test only checks mock interactions. Add at least one assertion against observable behavior (return value, rendered output, state, or side effect).",
    },
  },
  create(context) {
    return {
      CallExpression(node) {
        const callback = extractTestCallback(node);
        if (!callback) {
          return;
        }

        const matcherNames = [];
        walk(
          callback.body,
          (innerNode) => {
            if (innerNode.type !== "CallExpression") {
              return;
            }
            const matcher = getExpectMatcherName(innerNode);
            if (matcher) {
              matcherNames.push(matcher);
            }
          },
          callback,
        );

        if (matcherNames.length === 0) {
          return;
        }

        const onlyInteractionMatchers = matcherNames.every((name) =>
          INTERACTION_MATCHERS.has(name),
        );

        if (!onlyInteractionMatchers) {
          return;
        }

        context.report({
          node,
          messageId: "interactionOnly",
        });
      },
    };
  },
};
