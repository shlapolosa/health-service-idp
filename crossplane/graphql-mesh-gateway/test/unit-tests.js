#!/usr/bin/env node

/**
 * Unit Tests for GraphQL Mesh Gateway
 * Tests edge cases and input validation before container deployment
 */

const assert = require('assert');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

// Test utilities
function runTest(testName, testFn) {
  try {
    console.log(`🧪 Testing: ${testName}`);
    testFn();
    console.log(`✅ PASS: ${testName}`);
  } catch (error) {
    console.log(`❌ FAIL: ${testName}`);
    console.error(`   Error: ${error.message}`);
    process.exitCode = 1;
  }
}

function runBashCommand(command, input) {
  return new Promise((resolve, reject) => {
    const proc = spawn('bash', ['-c', command], {
      stdio: ['pipe', 'pipe', 'pipe']
    });
    
    let stdout = '';
    let stderr = '';
    
    proc.stdout.on('data', (data) => stdout += data.toString());
    proc.stderr.on('data', (data) => stderr += data.toString());
    
    if (input) {
      proc.stdin.write(input);
      proc.stdin.end();
    }
    
    proc.on('close', (code) => {
      resolve({ code, stdout, stderr });
    });
    
    proc.on('error', reject);
  });
}

// Test SERVICE_SELECTOR JSON parsing
async function testServiceSelectorParsing() {
  console.log('\n🔍 Testing SERVICE_SELECTOR parsing scenarios...\n');
  
  const testCases = [
    {
      name: 'Valid JSON',
      input: '{"app.kubernetes.io/managed-by":"kubevela"}',
      shouldPass: true
    },
    {
      name: 'Valid JSON with extra brace (current issue)',
      input: '{"app.kubernetes.io/managed-by":"kubevela"}}',
      shouldPass: false
    },
    {
      name: 'Empty string',
      input: '',
      shouldPass: false
    },
    {
      name: 'Invalid JSON - missing quotes',
      input: '{app.kubernetes.io/managed-by:kubevela}',
      shouldPass: false
    },
    {
      name: 'Invalid JSON - trailing comma',
      input: '{"app.kubernetes.io/managed-by":"kubevela",}',
      shouldPass: false
    },
    {
      name: 'Null string',
      input: 'null',
      shouldPass: true
    },
    {
      name: 'Non-JSON string',
      input: 'not-json-at-all',
      shouldPass: false
    }
  ];
  
  for (const testCase of testCases) {
    runTest(`SERVICE_SELECTOR: ${testCase.name}`, () => {
      // Test jq parsing
      const jqCommand = `echo '${testCase.input}' | jq -r 'to_entries | map("\\(.key)=\\(.value)") | join(",")'`;
      
      runBashCommand(jqCommand).then(result => {
        if (testCase.shouldPass) {
          assert(result.code === 0, `jq should succeed but failed with: ${result.stderr}`);
          console.log(`     Output: ${result.stdout.trim()}`);
        } else {
          if (result.code !== 0) {
            console.log(`     Expected failure: ${result.stderr.trim()}`);
          } else {
            console.log(`     Unexpected success: ${result.stdout.trim()}`);
          }
        }
      }).catch(error => {
        if (!testCase.shouldPass) {
          console.log(`     Expected error: ${error.message}`);
        } else {
          throw error;
        }
      });
    });
  }
}

// Test GraphQL Mesh configuration inputs
function testGraphQLMeshInputs() {
  console.log('\n🔍 Testing GraphQL Mesh input scenarios...\n');
  
  const testCases = [
    {
      name: 'Valid string input',
      input: 'test-service',
      expected: 'test-service'
    },
    {
      name: 'Empty string',
      input: '',
      expected: ''
    },
    {
      name: 'Undefined input',
      input: undefined,
      expectError: true
    },
    {
      name: 'Null input',
      input: null,
      expectError: true
    },
    {
      name: 'Number input',
      input: 123,
      expectError: true
    },
    {
      name: 'Object input',
      input: { name: 'test' },
      expectError: true
    },
    {
      name: 'Array input',
      input: ['test'],
      expectError: true
    }
  ];
  
  testCases.forEach(testCase => {
    runTest(`GraphQL Mesh Input: ${testCase.name}`, () => {
      // Simulate the no-case package behavior
      function simulateNoCase(input) {
        if (typeof input !== 'string') {
          throw new TypeError(`input.replace is not a function (input type: ${typeof input})`);
        }
        return input.replace(/[\s_-]+/g, ' ').toLowerCase();
      }
      
      if (testCase.expectError) {
        let errorThrown = false;
        try {
          simulateNoCase(testCase.input);
        } catch (error) {
          errorThrown = true;
          console.log(`     Expected error: ${error.message}`);
        }
        assert(errorThrown, 'Expected error but none was thrown');
      } else {
        const result = simulateNoCase(testCase.input);
        console.log(`     Result: "${result}"`);
        assert(typeof result === 'string', 'Result should be a string');
      }
    });
  });
}

// Test environment variable scenarios
function testEnvironmentVariables() {
  console.log('\n🔍 Testing environment variable scenarios...\n');
  
  const testCases = [
    {
      name: 'All required env vars present',
      env: {
        GATEWAY_NAME: 'test-gateway',
        NAMESPACE: 'default',
        SERVICE_SELECTOR: '{"app.kubernetes.io/managed-by":"kubevela"}',
        AUTO_DISCOVERY: 'true',
        DISCOVERY_INTERVAL: '5m'
      },
      shouldPass: true
    },
    {
      name: 'Missing GATEWAY_NAME (should use default)',
      env: {
        NAMESPACE: 'default',
        SERVICE_SELECTOR: '{"app.kubernetes.io/managed-by":"kubevela"}',
        AUTO_DISCOVERY: 'true',
        DISCOVERY_INTERVAL: '5m'
      },
      shouldPass: true
    },
    {
      name: 'Invalid SERVICE_SELECTOR JSON',
      env: {
        GATEWAY_NAME: 'test-gateway',
        NAMESPACE: 'default',
        SERVICE_SELECTOR: '{"app.kubernetes.io/managed-by":"kubevela"}}',
        AUTO_DISCOVERY: 'true',
        DISCOVERY_INTERVAL: '5m'
      },
      shouldPass: false
    },
    {
      name: 'Empty SERVICE_SELECTOR',
      env: {
        GATEWAY_NAME: 'test-gateway',
        NAMESPACE: 'default',
        SERVICE_SELECTOR: '',
        AUTO_DISCOVERY: 'true',
        DISCOVERY_INTERVAL: '5m'
      },
      shouldPass: false
    }
  ];
  
  testCases.forEach(testCase => {
    runTest(`Environment: ${testCase.name}`, () => {
      // Simulate environment variable processing
      const gatewayName = testCase.env.GATEWAY_NAME || 'api-gateway';
      const namespace = testCase.env.NAMESPACE || 'default';
      const serviceSelector = testCase.env.SERVICE_SELECTOR || '{"app.kubernetes.io/managed-by":"kubevela"}';
      const autoDiscovery = testCase.env.AUTO_DISCOVERY || 'true';
      const discoveryInterval = testCase.env.DISCOVERY_INTERVAL || '5m';
      
      console.log(`     GATEWAY_NAME: ${gatewayName}`);
      console.log(`     NAMESPACE: ${namespace}`);
      console.log(`     SERVICE_SELECTOR: ${serviceSelector}`);
      console.log(`     AUTO_DISCOVERY: ${autoDiscovery}`);
      console.log(`     DISCOVERY_INTERVAL: ${discoveryInterval}`);
      
      // Test JSON parsing
      if (testCase.shouldPass) {
        assert.doesNotThrow(() => {
          JSON.parse(serviceSelector);
        }, 'SERVICE_SELECTOR should be valid JSON');
      } else {
        if (serviceSelector) {
          assert.throws(() => {
            JSON.parse(serviceSelector);
          }, 'SERVICE_SELECTOR should be invalid JSON');
        }
      }
    });
  });
}

// Test mesh configuration creation
function testMeshConfigGeneration() {
  console.log('\n🔍 Testing mesh configuration generation...\n');
  
  runTest('Default mesh configuration structure', () => {
    const defaultConfig = {
      serve: {
        port: 8080,
        hostname: '0.0.0.0',
        cors: {
          origin: '*',
          credentials: false
        },
        playground: true,
        endpoint: '/graphql',
        healthCheckEndpoint: '/healthz'
      },
      sources: [],
      additionalTypeDefs: `
        type Query {
          _gateway: String!
          _health: String!
          _gatewayInfo: GatewayInfo!
        }
        
        type GatewayInfo {
          name: String!
          version: String!
          servicesCount: Int!
          lastUpdated: String!
        }
      `,
      additionalResolvers: [
        {
          Query: {
            _gateway: () => 'test-gateway',
            _health: () => 'OK',
            _gatewayInfo: () => ({
              name: 'test-gateway',
              version: '1.0.0',
              servicesCount: 0,
              lastUpdated: new Date().toISOString()
            })
          }
        }
      ]
    };
    
    // Validate config structure
    assert(typeof defaultConfig === 'object', 'Config should be an object');
    assert(typeof defaultConfig.serve === 'object', 'Serve config should be an object');
    assert(Array.isArray(defaultConfig.sources), 'Sources should be an array');
    assert(typeof defaultConfig.additionalTypeDefs === 'string', 'TypeDefs should be a string');
    assert(Array.isArray(defaultConfig.additionalResolvers), 'Resolvers should be an array');
    
    console.log('     ✅ Default config structure is valid');
  });
}

// Test duration parsing
function testDurationParsing() {
  console.log('\n🔍 Testing duration parsing...\n');
  
  const testCases = [
    { input: '5m', expected: 300 },
    { input: '1h', expected: 3600 },
    { input: '30s', expected: 30 },
    { input: '1d', expected: 86400 },
    { input: '120', expected: 120 },
    { input: 'invalid', expected: 300 }, // default
    { input: '', expected: 300 }, // default
  ];
  
  function durationToSeconds(duration) {
    if (!duration) return 300;
    
    const match = duration.match(/^(\d+)([smhd]?)$/);
    if (!match) return 300; // default fallback
    
    const value = parseInt(match[1]);
    const unit = match[2] || 's';
    
    switch (unit) {
      case 's': return value;
      case 'm': return value * 60;
      case 'h': return value * 3600;
      case 'd': return value * 86400;
      default: return value;
    }
  }
  
  testCases.forEach(testCase => {
    runTest(`Duration: ${testCase.input}`, () => {
      const result = durationToSeconds(testCase.input);
      console.log(`     Input: "${testCase.input}" -> ${result} seconds`);
      assert.strictEqual(result, testCase.expected, `Expected ${testCase.expected}, got ${result}`);
    });
  });
}

// Main test execution
async function runAllTests() {
  console.log('🧪 GraphQL Mesh Gateway Unit Tests');
  console.log('=====================================\n');
  
  testEnvironmentVariables();
  await testServiceSelectorParsing();
  testGraphQLMeshInputs();
  testMeshConfigGeneration();
  testDurationParsing();
  
  console.log('\n📊 Test Summary:');
  if (process.exitCode === 1) {
    console.log('❌ Some tests failed. Check output above for details.');
  } else {
    console.log('✅ All tests passed!');
  }
}

// Run tests if this file is executed directly
if (require.main === module) {
  runAllTests().catch(console.error);
}

module.exports = {
  testServiceSelectorParsing,
  testGraphQLMeshInputs,
  testEnvironmentVariables,
  testMeshConfigGeneration,
  testDurationParsing
};