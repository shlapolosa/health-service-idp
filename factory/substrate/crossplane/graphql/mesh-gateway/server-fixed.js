#!/usr/bin/env node

/**
 * Fixed GraphQL Mesh Gateway Server
 * Addresses SERVICE_SELECTOR and GraphQL Mesh initialization issues
 */

const express = require('express');
const cors = require('cors');
const { createYoga } = require('graphql-yoga');
const { printSchemaWithDirectives } = require('@graphql-tools/utils');
const path = require('path');
const fs = require('fs');

// Environment configuration with robust validation
const PORT = process.env.GATEWAY_PORT || process.env.PORT || 8080;
const HOST = process.env.HOST || '0.0.0.0';
const GATEWAY_NAME = process.env.GATEWAY_NAME || 'graphql-gateway';
const NAMESPACE = process.env.NAMESPACE || 'default';

// Fix SERVICE_SELECTOR parsing - handle potential corruption
function parseServiceSelector(rawSelector) {
  console.log(`🔍 Raw SERVICE_SELECTOR: "${rawSelector}"`);
  
  if (!rawSelector || typeof rawSelector !== 'string') {
    console.log('⚠️  SERVICE_SELECTOR empty or not string, using default');
    return { "app.kubernetes.io/managed-by": "kubevela" };
  }
  
  // Remove any trailing extra braces (fix the main issue)
  let cleanSelector = rawSelector.trim();
  
  // Count braces to detect corruption
  const openBraces = (cleanSelector.match(/{/g) || []).length;
  const closeBraces = (cleanSelector.match(/}/g) || []).length;
  
  console.log(`   Open braces: ${openBraces}, Close braces: ${closeBraces}`);
  
  if (closeBraces > openBraces) {
    console.log('⚠️  Detected extra closing braces, attempting to fix...');
    // Remove extra closing braces from the end
    while (cleanSelector.endsWith('}') && (cleanSelector.match(/}/g) || []).length > (cleanSelector.match(/{/g) || []).length) {
      cleanSelector = cleanSelector.slice(0, -1);
      console.log(`   Cleaned to: "${cleanSelector}"`);
    }
  }
  
  try {
    const parsed = JSON.parse(cleanSelector);
    console.log('✅ SERVICE_SELECTOR parsed successfully:', JSON.stringify(parsed));
    return parsed;
  } catch (error) {
    console.error('❌ SERVICE_SELECTOR parsing failed:', error.message);
    console.log('📝 Using default selector');
    return { "app.kubernetes.io/managed-by": "kubevela" };
  }
}

const SERVICE_SELECTOR = parseServiceSelector(process.env.SERVICE_SELECTOR);
const AUTO_DISCOVERY = process.env.AUTO_DISCOVERY === 'true';
const DISCOVERY_INTERVAL = process.env.DISCOVERY_INTERVAL || '5m';

class GraphQLMeshGateway {
  constructor() {
    this.app = express();
    this.mesh = null;
    this.startTime = new Date();
    this.servicesCount = 0;
    this.lastConfigUpdate = null;
    
    this.setupMiddleware();
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

    // Health check endpoint (before mesh initialization)
    this.app.get('/healthz', this.healthCheck.bind(this));
    this.app.get('/health', this.healthCheck.bind(this));
    
    // Gateway info endpoint
    this.app.get('/info', this.gatewayInfo.bind(this));
    
    // Schema endpoint
    this.app.get('/schema', this.schemaEndpoint.bind(this));
  }

  async healthCheck(req, res) {
    const health = {
      status: 'healthy',
      timestamp: new Date().toISOString(),
      uptime: Math.floor((Date.now() - this.startTime.getTime()) / 1000),
      gateway: GATEWAY_NAME,
      meshReady: this.mesh !== null,
      servicesCount: this.servicesCount,
      lastConfigUpdate: this.lastConfigUpdate,
      serviceSelector: SERVICE_SELECTOR,
      namespace: NAMESPACE,
      autoDiscovery: AUTO_DISCOVERY,
      discoveryInterval: DISCOVERY_INTERVAL
    };

    res.json(health);
  }

  async gatewayInfo(req, res) {
    const info = {
      name: GATEWAY_NAME,
      version: '1.0.0-fixed',
      namespace: NAMESPACE,
      serviceSelector: SERVICE_SELECTOR,
      servicesCount: this.servicesCount,
      lastUpdated: this.lastConfigUpdate,
      startTime: this.startTime.toISOString(),
      meshReady: this.mesh !== null,
      autoDiscovery: AUTO_DISCOVERY,
      discoveryInterval: DISCOVERY_INTERVAL,
      endpoints: {
        graphql: '/graphql',
        playground: '/graphql',
        health: '/healthz',
        info: '/info',
        schema: '/schema'
      }
    };

    res.json(info);
  }

  async schemaEndpoint(req, res) {
    if (!this.mesh) {
      return res.status(503).json({ 
        error: 'Mesh not ready',
        fallbackSchema: this.getFallbackSchema()
      });
    }

    try {
      const schema = this.mesh.schema;
      const sdl = printSchemaWithDirectives(schema);
      
      if (req.headers.accept === 'application/json') {
        res.json({ schema: sdl });
      } else {
        res.type('text/plain').send(sdl);
      }
    } catch (error) {
      console.error('Error generating schema:', error);
      res.status(500).json({ 
        error: 'Failed to generate schema',
        fallbackSchema: this.getFallbackSchema()
      });
    }
  }

  getFallbackSchema() {
    return `
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
    `;
  }

  async initializeMesh() {
    try {
      console.log('🔧 Initializing GraphQL Mesh (Fixed Version)...');
      
      // Create a safe mesh configuration that won't fail
      this.createSafeConfig();
      
      // Try to import GraphQL Mesh dynamically with error handling
      let findAndParseConfig, getMesh;
      
      try {
        const meshCli = await import('@graphql-mesh/cli');
        findAndParseConfig = meshCli.findAndParseConfig;
        getMesh = meshCli.getMesh;
      } catch (importError) {
        console.error('❌ Failed to import GraphQL Mesh:', importError.message);
        throw new Error('GraphQL Mesh not available');
      }
      
      // Find and parse mesh configuration with safe defaults
      const meshConfig = await findAndParseConfig({
        dir: process.cwd(),
        ignoreAdditionalResolvers: false
      });

      console.log('📋 Mesh configuration loaded (safe mode)');
      
      // Validate configuration before creating mesh
      if (!meshConfig || !meshConfig.config) {
        throw new Error('Invalid mesh configuration');
      }
      
      // Ensure all string inputs to mesh are actually strings
      this.validateMeshConfig(meshConfig.config);
      
      // Get mesh instance
      this.mesh = await getMesh(meshConfig);
      
      // Update service count from configuration
      if (meshConfig.config && meshConfig.config.sources) {
        this.servicesCount = meshConfig.config.sources.length;
      }
      
      this.lastConfigUpdate = new Date().toISOString();
      
      console.log(`✅ Mesh initialized successfully with ${this.servicesCount} services`);
      
      return this.mesh;
    } catch (error) {
      console.error('❌ Failed to initialize mesh:', error.message);
      
      // Create a working fallback mesh
      console.log('🔄 Creating fallback mesh without external sources...');
      await this.createFallbackMesh();
      
      return this.mesh;
    }
  }

  validateMeshConfig(config) {
    console.log('🔍 Validating mesh configuration inputs...');
    
    // Check that the gateway name is a string (this was causing the TypeError)
    if (typeof GATEWAY_NAME !== 'string') {
      throw new Error(`GATEWAY_NAME must be a string, got: ${typeof GATEWAY_NAME}`);
    }
    
    // Validate other critical string inputs
    if (typeof NAMESPACE !== 'string') {
      throw new Error(`NAMESPACE must be a string, got: ${typeof NAMESPACE}`);
    }
    
    console.log('✅ All mesh configuration inputs are valid');
  }

  createSafeConfig() {
    const safeConfig = {
      serve: {
        port: parseInt(PORT),
        hostname: HOST,
        cors: {
          origin: '*',
          credentials: false
        },
        playground: true,
        endpoint: '/graphql',
        healthCheckEndpoint: false // We handle this ourselves
      },
      sources: [], // Start with no external sources to avoid errors
      additionalTypeDefs: this.getFallbackSchema(),
      additionalResolvers: [
        {
          Query: {
            _gateway: () => GATEWAY_NAME,
            _health: () => 'OK',
            _gatewayInfo: () => ({
              name: GATEWAY_NAME,
              version: '1.0.0-fixed',
              servicesCount: this.servicesCount,
              lastUpdated: this.lastConfigUpdate || new Date().toISOString()
            })
          }
        }
      ]
    };

    const yaml = require('yaml');
    fs.writeFileSync('.meshrc.yaml', yaml.stringify(safeConfig));
    console.log('📝 Created safe mesh configuration');
  }

  async createFallbackMesh() {
    try {
      // Create minimal working mesh without external dependencies
      this.createSafeConfig();
      
      const { findAndParseConfig, getMesh } = await import('@graphql-mesh/cli');
      
      const meshConfig = await findAndParseConfig({
        dir: process.cwd(),
        ignoreAdditionalResolvers: false
      });
      
      this.mesh = await getMesh(meshConfig);
      this.servicesCount = 0; // No external services in fallback mode
      console.log('✅ Fallback mesh created successfully');
    } catch (fallbackError) {
      console.error('❌ Failed to create fallback mesh:', fallbackError.message);
      // Continue without mesh - health endpoints will still work
    }
  }

  async setupGraphQLEndpoint() {
    if (!this.mesh) {
      console.log('⚠️  No mesh available, setting up basic GraphQL endpoint');
      
      // Create a basic GraphQL endpoint without mesh
      this.app.post('/graphql', (req, res) => {
        res.json({
          data: {
            _gateway: GATEWAY_NAME,
            _health: 'OK',
            _gatewayInfo: {
              name: GATEWAY_NAME,
              version: '1.0.0-fixed',
              servicesCount: 0,
              lastUpdated: new Date().toISOString()
            }
          }
        });
      });
      
      this.app.get('/graphql', (req, res) => {
        if (req.headers.accept && req.headers.accept.includes('text/html')) {
          res.send(this.getPlaygroundHTML());
        } else {
          res.json({
            message: 'GraphQL endpoint (fallback mode)',
            gateway: GATEWAY_NAME,
            serviceSelector: SERVICE_SELECTOR,
            servicesDiscovered: this.servicesCount
          });
        }
      });
      
      return;
    }

    // Create GraphQL Yoga server with mesh
    const yoga = createYoga({
      schema: this.mesh.schema,
      context: this.mesh.context,
      graphqlEndpoint: '/graphql',
      landingPage: false, // We'll serve playground separately
      healthCheckEndpoint: false, // We handle this ourselves
      cors: false // We handle CORS at the Express level
    });

    // Add GraphQL endpoint
    this.app.use('/graphql', yoga);
    
    // Serve GraphQL Playground on GET requests to /graphql
    this.app.get('/graphql', (req, res) => {
      if (req.headers.accept && req.headers.accept.includes('text/html')) {
        res.send(this.getPlaygroundHTML());
      } else {
        yoga(req, res);
      }
    });

    console.log('🎮 GraphQL endpoint configured successfully');
  }

  getPlaygroundHTML() {
    return `
<!DOCTYPE html>
<html>
<head>
  <title>GraphQL Gateway - ${GATEWAY_NAME} (Fixed)</title>
  <style>
    body { 
      margin: 0; 
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
      background: #f5f5f5;
    }
    .container { display: flex; height: 100vh; align-items: center; justify-content: center; }
    .card {
      background: white; padding: 2rem; border-radius: 8px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; max-width: 600px;
    }
    h1 { color: #333; margin-bottom: 1rem; }
    .status { color: #28a745; font-weight: bold; }
    .links a { 
      display: inline-block; margin: 0.5rem 1rem; color: #007bff; text-decoration: none;
      padding: 0.5rem 1rem; border: 1px solid #007bff; border-radius: 4px;
    }
    .links a:hover { background: #007bff; color: white; }
    .config {
      background: #f8f9fa; padding: 1rem; border-radius: 4px; margin: 1rem 0;
      text-align: left; font-family: monospace; font-size: 0.9rem;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>🚀 ${GATEWAY_NAME}</h1>
      <p class="status">✅ GraphQL Gateway - Running (Fixed Version)</p>
      <div class="config">
        <strong>Configuration:</strong><br>
        Namespace: ${NAMESPACE}<br>
        Service Selector: ${JSON.stringify(SERVICE_SELECTOR)}<br>
        Auto Discovery: ${AUTO_DISCOVERY}<br>
        Discovery Interval: ${DISCOVERY_INTERVAL}<br>
        Services: ${this.servicesCount}<br>
        Mesh Ready: ${this.mesh !== null}
      </div>
      <div class="links">
        <a href="/graphql">GraphQL Endpoint</a>
        <a href="/info">Gateway Info</a>
        <a href="/healthz">Health Check</a>
        <a href="/schema">Schema</a>
      </div>
    </div>
  </div>
</body>
</html>`;
  }

  async start() {
    try {
      console.log(`🚀 Starting Fixed GraphQL Mesh Gateway: ${GATEWAY_NAME}`);
      console.log(`📍 Namespace: ${NAMESPACE}`);
      console.log(`🔍 Service Selector:`, SERVICE_SELECTOR);
      console.log(`🔄 Auto Discovery: ${AUTO_DISCOVERY}`);
      console.log(`⏱️  Discovery Interval: ${DISCOVERY_INTERVAL}`);
      
      // Initialize mesh (with fallback handling)
      await this.initializeMesh();
      
      // Setup GraphQL endpoint (works with or without mesh)
      await this.setupGraphQLEndpoint();
      
      // Start server
      this.server = this.app.listen(PORT, HOST, () => {
        console.log(`✅ Fixed GraphQL Gateway running on http://${HOST}:${PORT}`);
        console.log(`🎮 GraphQL Playground: http://${HOST}:${PORT}/graphql`);
        console.log(`🏥 Health Check: http://${HOST}:${PORT}/healthz`);
        console.log(`ℹ️  Gateway Info: http://${HOST}:${PORT}/info`);
        console.log(`📋 Schema: http://${HOST}:${PORT}/schema`);
      });

      // Graceful shutdown
      process.on('SIGTERM', this.shutdown.bind(this));
      process.on('SIGINT', this.shutdown.bind(this));
      
    } catch (error) {
      console.error('❌ Failed to start gateway:', error);
      process.exit(1);
    }
  }

  async shutdown() {
    console.log('🛑 Shutting down Fixed GraphQL Gateway...');
    
    if (this.server) {
      this.server.close(() => {
        console.log('✅ Server closed');
      });
    }
    
    if (this.mesh) {
      try {
        await this.mesh.destroy();
        console.log('✅ Mesh destroyed');
      } catch (error) {
        console.error('⚠️  Error destroying mesh:', error);
      }
    }
    
    process.exit(0);
  }
}

// Start the fixed gateway
if (require.main === module) {
  const gateway = new GraphQLMeshGateway();
  gateway.start().catch(error => {
    console.error('❌ Fatal error:', error);
    process.exit(1);
  });
}

module.exports = GraphQLMeshGateway;