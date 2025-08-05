#!/usr/bin/env node

/**
 * Simplified GraphQL Gateway Server for Local Testing
 * Tests core functionality without GraphQL Mesh complexity
 */

const express = require('express');
const cors = require('cors');

// Environment configuration with validation
const PORT = process.env.GATEWAY_PORT || process.env.PORT || 8080;
const HOST = process.env.HOST || '0.0.0.0';
const GATEWAY_NAME = process.env.GATEWAY_NAME || 'test-gateway';
const SERVICE_SELECTOR = process.env.SERVICE_SELECTOR || '{"app.kubernetes.io/managed-by":"kubevela"}';
const NAMESPACE = process.env.NAMESPACE || 'default';
const AUTO_DISCOVERY = process.env.AUTO_DISCOVERY || 'true';
const DISCOVERY_INTERVAL = process.env.DISCOVERY_INTERVAL || '5m';

console.log('🚀 Starting Simplified GraphQL Gateway Server');
console.log('==============================================');

// Validate SERVICE_SELECTOR
function validateServiceSelector(selector) {
  console.log(`🔍 Validating SERVICE_SELECTOR: "${selector}"`);
  
  if (!selector || typeof selector !== 'string') {
    throw new Error(`SERVICE_SELECTOR must be a non-empty string, got: ${typeof selector}`);
  }
  
  // Check for extra braces
  const braceCount = (selector.match(/}/g) || []).length;
  const openBraceCount = (selector.match(/{/g) || []).length;
  
  console.log(`   Open braces: ${openBraceCount}, Close braces: ${braceCount}`);
  
  if (braceCount !== openBraceCount) {
    throw new Error(`SERVICE_SELECTOR has unmatched braces. Open: ${openBraceCount}, Close: ${braceCount}`);
  }
  
  try {
    const parsed = JSON.parse(selector);
    console.log('   ✅ Valid JSON:', JSON.stringify(parsed, null, 2));
    return parsed;
  } catch (error) {
    throw new Error(`SERVICE_SELECTOR is not valid JSON: ${error.message}`);
  }
}

// Validate duration
function validateDuration(duration) {
  console.log(`🔍 Validating DISCOVERY_INTERVAL: "${duration}"`);
  
  if (!duration || typeof duration !== 'string') {
    console.log('   ⚠️  Invalid duration, using default: 5m');
    return '5m';
  }
  
  const match = duration.match(/^(\d+)([smhd]?)$/);
  if (!match) {
    console.log('   ⚠️  Invalid duration format, using default: 5m');
    return '5m';
  }
  
  console.log('   ✅ Valid duration format');
  return duration;
}

// Convert duration to seconds
function durationToSeconds(duration) {
  const match = duration.match(/^(\d+)([smhd]?)$/);
  if (!match) return 300; // default 5 minutes
  
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

class SimpleGateway {
  constructor() {
    this.app = express();
    this.startTime = new Date();
    this.servicesCount = 0;
    this.lastConfigUpdate = null;
    this.serviceSelector = null;
    this.discoveryInterval = null;
    
    this.setupMiddleware();
    this.validateConfiguration();
  }
  
  validateConfiguration() {
    console.log('\n📋 Configuration Validation:');
    console.log(`   GATEWAY_NAME: ${GATEWAY_NAME}`);
    console.log(`   NAMESPACE: ${NAMESPACE}`);
    console.log(`   HOST: ${HOST}`);
    console.log(`   PORT: ${PORT}`);
    console.log(`   AUTO_DISCOVERY: ${AUTO_DISCOVERY}`);
    
    try {
      // Validate SERVICE_SELECTOR
      this.serviceSelector = validateServiceSelector(SERVICE_SELECTOR);
      
      // Validate DISCOVERY_INTERVAL
      this.discoveryInterval = validateDuration(DISCOVERY_INTERVAL);
      const intervalSeconds = durationToSeconds(this.discoveryInterval);
      console.log(`   Discovery interval: ${this.discoveryInterval} (${intervalSeconds} seconds)`);
      
      console.log('✅ All configuration valid\n');
      
    } catch (error) {
      console.error('❌ Configuration validation failed:', error.message);
      process.exit(1);
    }
  }
  
  setupMiddleware() {
    // CORS configuration
    this.app.use(cors({
      origin: true,
      credentials: true,
      methods: ['GET', 'POST', 'OPTIONS'],
      allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With', 'Accept']
    }));

    // Request logging
    this.app.use((req, res, next) => {
      console.log(`${new Date().toISOString()} ${req.method} ${req.path}`);
      next();
    });

    // Health check endpoint
    this.app.get('/healthz', this.healthCheck.bind(this));
    this.app.get('/health', this.healthCheck.bind(this));
    
    // Gateway info endpoint
    this.app.get('/info', this.gatewayInfo.bind(this));
    
    // Simple GraphQL endpoint (mock)
    this.app.get('/graphql', this.graphqlPlayground.bind(this));
    this.app.post('/graphql', this.graphqlEndpoint.bind(this));
    
    // Root endpoint
    this.app.get('/', this.rootEndpoint.bind(this));
  }
  
  healthCheck(req, res) {
    const health = {
      status: 'healthy',
      timestamp: new Date().toISOString(),
      uptime: Math.floor((Date.now() - this.startTime.getTime()) / 1000),
      gateway: GATEWAY_NAME,
      namespace: NAMESPACE,
      serviceSelector: this.serviceSelector,
      discoveryInterval: this.discoveryInterval,
      servicesCount: this.servicesCount,
      lastConfigUpdate: this.lastConfigUpdate
    };

    res.json(health);
  }
  
  gatewayInfo(req, res) {
    const info = {
      name: GATEWAY_NAME,
      version: '1.0.0-simplified',
      namespace: NAMESPACE,
      serviceSelector: this.serviceSelector,
      servicesCount: this.servicesCount,
      lastUpdated: this.lastConfigUpdate,
      startTime: this.startTime.toISOString(),
      discoveryInterval: this.discoveryInterval,
      endpoints: {
        graphql: '/graphql',
        playground: '/graphql',
        health: '/healthz',
        info: '/info'
      }
    };

    res.json(info);
  }
  
  rootEndpoint(req, res) {
    res.json({
      message: 'GraphQL Gateway - Simplified Test Server',
      gateway: GATEWAY_NAME,
      version: '1.0.0-simplified',
      endpoints: {
        health: '/healthz',
        info: '/info',
        graphql: '/graphql'
      }
    });
  }
  
  graphqlPlayground(req, res) {
    if (req.headers.accept && req.headers.accept.includes('text/html')) {
      res.send(this.getPlaygroundHTML());
    } else {
      res.json({
        message: 'GraphQL endpoint (simplified)',
        gateway: GATEWAY_NAME,
        serviceSelector: this.serviceSelector,
        servicesDiscovered: this.servicesCount
      });
    }
  }
  
  graphqlEndpoint(req, res) {
    // Simple mock GraphQL response
    res.json({
      data: {
        _gateway: GATEWAY_NAME,
        _health: 'OK',
        _gatewayInfo: {
          name: GATEWAY_NAME,
          version: '1.0.0-simplified',
          servicesCount: this.servicesCount,
          lastUpdated: new Date().toISOString()
        }
      }
    });
  }
  
  getPlaygroundHTML() {
    return `
<!DOCTYPE html>
<html>
<head>
  <title>GraphQL Gateway - ${GATEWAY_NAME} (Simplified)</title>
  <style>
    body { 
      margin: 0; 
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
      background: #f5f5f5;
    }
    .container {
      display: flex;
      height: 100vh;
      align-items: center;
      justify-content: center;
    }
    .card {
      background: white;
      padding: 2rem;
      border-radius: 8px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.1);
      text-align: center;
      max-width: 500px;
    }
    h1 { color: #333; margin-bottom: 1rem; }
    .status { color: #28a745; font-weight: bold; }
    .links a { 
      display: inline-block;
      margin: 0.5rem 1rem;
      color: #007bff;
      text-decoration: none;
    }
    .config {
      background: #f8f9fa;
      padding: 1rem;
      border-radius: 4px;
      margin: 1rem 0;
      text-align: left;
      font-family: monospace;
      font-size: 0.9rem;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>🚀 ${GATEWAY_NAME}</h1>
      <p class="status">✅ Simplified GraphQL Gateway - Running</p>
      <div class="config">
        <strong>Configuration:</strong><br>
        Namespace: ${NAMESPACE}<br>
        Service Selector: ${JSON.stringify(this.serviceSelector)}<br>
        Discovery Interval: ${this.discoveryInterval}<br>
        Services: ${this.servicesCount}
      </div>
      <div class="links">
        <a href="/graphql">GraphQL Endpoint</a>
        <a href="/info">Gateway Info</a>
        <a href="/healthz">Health Check</a>
      </div>
    </div>
  </div>
</body>
</html>`;
  }
  
  start() {
    this.server = this.app.listen(PORT, HOST, () => {
      console.log(`✅ Simplified Gateway running on http://${HOST}:${PORT}`);
      console.log(`🎮 GraphQL Playground: http://${HOST}:${PORT}/graphql`);
      console.log(`🏥 Health Check: http://${HOST}:${PORT}/healthz`);
      console.log(`ℹ️  Gateway Info: http://${HOST}:${PORT}/info`);
      console.log(`\n🎯 Test URLs:`);
      console.log(`   curl http://${HOST}:${PORT}/healthz`);
      console.log(`   curl http://${HOST}:${PORT}/info`);
      console.log(`   curl http://${HOST}:${PORT}/graphql`);
    });

    // Graceful shutdown
    process.on('SIGTERM', this.shutdown.bind(this));
    process.on('SIGINT', this.shutdown.bind(this));
  }
  
  shutdown() {
    console.log('\n🛑 Shutting down gateway...');
    if (this.server) {
      this.server.close(() => {
        console.log('✅ Server closed');
        process.exit(0);
      });
    } else {
      process.exit(0);
    }
  }
}

// Start the simplified gateway
if (require.main === module) {
  const gateway = new SimpleGateway();
  gateway.start();
}

module.exports = SimpleGateway;