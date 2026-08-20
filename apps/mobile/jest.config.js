/** @type {import('jest').Config} */
module.exports = {
  testEnvironment: 'node',
  testMatch: ['**/lib/__tests__/**/*.(test|spec).(ts|tsx)'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  transform: {
    '^.+\\.(ts|tsx)$': [
      'babel-jest',
      {
        presets: ['babel-preset-expo'],
      },
    ],
  },
  moduleFileExtensions: ['ts', 'tsx', 'js', 'json'],
};
