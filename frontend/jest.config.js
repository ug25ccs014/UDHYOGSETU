const nextJest = require('next/jest')({ dir: './' })

const config = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  testPathIgnorePatterns: ['<rootDir>/node_modules/', '<rootDir>/.next/'],
  collectCoverageFrom: ['lib/**/*.{ts,tsx}', 'hooks/**/*.{ts,tsx}', '!**/*.d.ts'],
}

module.exports = nextJest(config)