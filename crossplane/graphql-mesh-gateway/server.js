#!/usr/bin/env node

/**
 * GraphQL Mesh Gateway Server
 * Serves federated GraphQL API from discovered Kubernetes services
 */

const express = require('express');
const cors = require('cors');
const { createYoga } = require('graphql-yoga');
const { printSchemaWithDirectives } = require('@graphql-tools/utils');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

// Environment configuration
const PORT = process.env.PORT || 8080;
const HOST = process.env.HOST || '0.0.0.0';
const GATEWAY_NAME = process.env.GATEWAY_NAME || 'graphql-gateway';
const SERVICE_SELECTOR = process.env.SERVICE_SELECTOR || '{}';
const NAMESPACE = process.env.NAMESPACE || 'default';

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
      lastConfigUpdate: this.lastConfigUpdate
    };

    res.json(health);
  }

  async gatewayInfo(req, res) {
    const info = {
      name: GATEWAY_NAME,
      version: '1.0.0',
      namespace: NAMESPACE,
      serviceSelector: JSON.parse(SERVICE_SELECTOR),
      servicesCount: this.servicesCount,
      lastUpdated: this.lastConfigUpdate,
      startTime: this.startTime.toISOString(),
      meshReady: this.mesh !== null,
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
      return res.status(503).json({ error: 'Mesh not ready' });
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
      res.status(500).json({ error: 'Failed to generate schema' });
    }
  }

  async initializeMesh() {
    try {
      console.log('🔧 Initializing GraphQL Mesh...');
      
      // Check if mesh configuration exists
      const configPath = path.join(process.cwd(), '.meshrc.yaml');
      if (!fs.existsSync(configPath)) {
        console.log('⚠️  Mesh configuration not found, using default config');
        this.createDefaultConfig();
      }

      // Find and parse mesh configuration
      const meshConfig = await findAndParseConfig({
        dir: process.cwd(),
        ignoreAdditionalResolvers: false
      });

      console.log('📋 Mesh configuration loaded');
      
      // Get mesh instance
      this.mesh = await getMesh(meshConfig);
      
      // Update service count from configuration
      if (meshConfig.config && meshConfig.config.sources) {
        this.servicesCount = meshConfig.config.sources.length;
      }
      
      this.lastConfigUpdate = new Date().toISOString();
      
      console.log(`✅ Mesh initialized with ${this.servicesCount} services`);
      
      return this.mesh;
    } catch (error) {
      console.error('❌ Failed to initialize mesh:', error);
      
      // Create a fallback mesh with empty schema
      console.log('🔄 Creating fallback mesh...');
      this.createFallbackMesh();
      
      throw error;
    }
  }

  createDefaultConfig() {
    const defaultConfig = {
      serve: {
        port: PORT,
        hostname: HOST,
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
            _gateway: () => GATEWAY_NAME,
            _health: () => 'OK',
            _gatewayInfo: () => ({
              name: GATEWAY_NAME,
              version: '1.0.0',
              servicesCount: 0,
              lastUpdated: new Date().toISOString()
            })
          }
        }
      ]
    };

    const yaml = require('yaml');
    fs.writeFileSync('.meshrc.yaml', yaml.stringify(defaultConfig));
    console.log('📝 Created default mesh configuration');
  }

  async createFallbackMesh() {
    // Create minimal working mesh
    this.createDefaultConfig();
    
    try {
      const meshConfig = await findAndParseConfig({
        dir: process.cwd(),
        ignoreAdditionalResolvers: false
      });
      
      this.mesh = await getMesh(meshConfig);
      console.log('✅ Fallback mesh created');
    } catch (fallbackError) {
      console.error('❌ Failed to create fallback mesh:', fallbackError);
    }
  }

  async setupGraphQLEndpoint() {
    if (!this.mesh) {
      throw new Error('Mesh not initialized');
    }

    // Create GraphQL Yoga server
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
        // Serve GraphQL Playground
        res.send(this.getPlaygroundHTML());
      } else {
        // Let Yoga handle it
        yoga(req, res);
      }
    });

    console.log('🎮 GraphQL Playground available at /graphql');
  }

  getPlaygroundHTML() {
    return `
<!DOCTYPE html>
<html>
<head>
  <title>GraphQL Playground - ${GATEWAY_NAME}</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/graphql-playground-react@1.7.26/build/static/css/index.css" />
</head>
<body>
  <div id="root">
    <style>
      body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif; }
      #root { height: 100vh; }
    </style>
    <div style="display: flex; height: 100vh; align-items: center; justify-content: center;">
      <div style="text-align: center;">
        <h1>${GATEWAY_NAME}</h1>
        <p>GraphQL Gateway - ${this.servicesCount} services federated</p>
        <p><a href="/graphql" style="color: #e535ab;">Access GraphQL Endpoint</a></p>
        <p><a href="/info" style="color: #1976d2;">Gateway Info</a></p>
        <p><a href="/schema" style="color: #388e3c;">View Schema</a></p>
      </div>
    </div>
  </div>
</body>
</html>`;
  }

  async start() {
    try {
      console.log(`🚀 Starting GraphQL Mesh Gateway: ${GATEWAY_NAME}`);
      console.log(`📍 Namespace: ${NAMESPACE}`);
      console.log(`🔍 Service Selector: ${SERVICE_SELECTOR}`);
      
      // Initialize mesh
      await this.initializeMesh();
      
      // Setup GraphQL endpoint
      await this.setupGraphQLEndpoint();
      
      // Start server
      this.server = this.app.listen(PORT, HOST, () => {
        console.log(`✅ GraphQL Mesh Gateway running on http://${HOST}:${PORT}`);
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
    console.log('🛑 Shutting down GraphQL Mesh Gateway...');
    
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

// Start the gateway
if (require.main === module) {
  const gateway = new GraphQLMeshGateway();
  gateway.start().catch(error => {
    console.error('❌ Fatal error:', error);
    process.exit(1);
  });
}

module.exports = GraphQLMeshGateway;