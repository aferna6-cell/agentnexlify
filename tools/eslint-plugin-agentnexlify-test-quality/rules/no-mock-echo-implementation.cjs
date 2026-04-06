"use strict";

const IMPLEMENTATION_METHODS = new Set([
  "mockImplementation",
  "mockImplementationOnce",
]);

const MOCK_FACTORIES = new Set(["jest", "vi"]);

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

function unwrapExpression(node) {
  let current = node;
  while (
    current &&
    [
      "TSAsExpression",
      "TSTypeAssertion",
      "TSNonNullExpression",
      "ParenthesizedExpression",
    ].includes(current.type)
  ) {
    current = current.expression;
  }
  return current;
}

function getFunctionParamInfo(fnNode) {
  const paramNames = new Set();
  let restParamName = null;

  for (const param of fnNode.params || []) {
    if (param.type === "Identifier") {
      paramNames.add(param.name);
      continue;
    }

    if (param.type === "RestElement" && param.argument.type === "Identifier") {
      restParamName = param.argument.name;
      paramNames.add(restParamName);
    }
  }

  return { paramNames, restParamName };
}

function isParamReference(node, paramInfo) {
  const current = unwrapExpression(node);
  if (!current) {
    return false;
  }

  if (current.type === "Identifier" && paramInfo.paramNames.has(current.name)) {
    return true;
  }

  if (
    paramInfo.restParamName &&
    current.type === "MemberExpression" &&
    current.computed &&
    current.object.type === "Identifier" &&
    current.object.name === paramInfo.restParamName &&
    current.property.type === "Literal" &&
    current.property.value === 0
  ) {
    return true;
  }

  if (current.type === "AwaitExpression") {
    return isParamReference(current.argument, paramInfo);
  }

  if (
    current.type === "CallExpression" &&
    current.callee.type === "MemberExpression" &&
    current.callee.object.type === "Identifier" &&
    current.callee.object.name === "Promise" &&
    getPropertyName(current.callee) === "resolve" &&
    current.arguments.length === 1
  ) {
    return isParamReference(current.arguments[0], paramInfo);
  }

  return false;
}

function collectReturnExpressions(node, expressions, seenNodes = new WeakSet()) {
  if (!node) {
    return;
  }
  if (seenNodes.has(node)) {
    return;
  }
  seenNodes.add(node);

  if (
    node.type === "FunctionExpression" ||
    node.type === "ArrowFunctionExpression" ||
    node.type === "FunctionDeclaration"
  ) {
    return;
  }

  if (node.type === "ReturnStatement" && node.argument) {
    expressions.push(node.argument);
    return;
  }

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
          collectReturnExpressions(child, expressions, seenNodes);
        }
      }
      continue;
    }
    if (value && typeof value.type === "string") {
      collectReturnExpressions(value, expressions, seenNodes);
    }
  }
}

function isEchoFunction(node) {
  if (!node || (node.type !== "ArrowFunctionExpression" && node.type !== "FunctionExpression")) {
    return false;
  }

  const paramInfo = getFunctionParamInfo(node);
  if (paramInfo.paramNames.size === 0) {
    return false;
  }

  if (node.body.type !== "BlockStatement") {
    return isParamReference(node.body, paramInfo);
  }

  const returnExpressions = [];
  collectReturnExpressions(node.body, returnExpressions);
  if (returnExpressions.length === 0) {
    return false;
  }

  return returnExpressions.every((expr) => isParamReference(expr, paramInfo));
}

function getImplementationCallback(node) {
  if (!node || node.type !== "CallExpression") {
    return null;
  }

  if (
    node.callee.type === "MemberExpression" &&
    node.callee.object.type === "Identifier" &&
    MOCK_FACTORIES.has(node.callee.object.name) &&
    getPropertyName(node.callee) === "fn" &&
    node.arguments.length >= 1
  ) {
    return node.arguments[0];
  }

  if (
    node.callee.type === "MemberExpression" &&
    IMPLEMENTATION_METHODS.has(getPropertyName(node.callee)) &&
    node.arguments.length >= 1
  ) {
    return node.arguments[0];
  }

  return null;
}

module.exports = {
  meta: {
    type: "problem",
    docs: {
      description:
        "Disallow mock implementations that only echo the input argument (a low-value test anti-pattern).",
    },
    schema: [],
    messages: {
      noMockEcho:
        "Mock implementations must model behavior, not echo test inputs. Replace this echo mock with meaningful domain behavior.",
    },
  },
  create(context) {
    return {
      CallExpression(node) {
        const callback = getImplementationCallback(node);
        if (!callback || !isEchoFunction(callback)) {
          return;
        }

        context.report({
          node: callback,
          messageId: "noMockEcho",
        });
      },
    };
  },
};
