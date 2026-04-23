const { version } = require("./package.json");

module.exports = {
  version,
  platformVersion: require("zapier-platform-core").version,
  authentication: require("./authentication"),
  triggers: {
    [require("./triggers/new_lead").key]: require("./triggers/new_lead"),
  },
};
