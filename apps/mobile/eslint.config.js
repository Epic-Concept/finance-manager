const expoConfig = require('eslint-config-expo/flat');
const { defineConfig } = require('eslint/config');

module.exports = defineConfig([
  expoConfig,
  {
    ignores: ['dist/*', 'node_modules/*', '.expo/*'],
  },
  {
    rules: {
      // Standard pattern for screen mount fetches; rule is too strict for RN tabs.
      'react-hooks/set-state-in-effect': 'off',
    },
  },
]);
