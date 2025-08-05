/**
 * Production-Ready GraphQL Gateway Server
 * Express.js server with GraphQL endpoint, health checks, and monitoring
 */

const express = require('express');
const { graphqlHTTP } = require('express-graphql');
const { GraphQLSchema, GraphQLObjectType, GraphQLString, GraphQLList, GraphQLBoolean } = require('graphql');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');

const DiscoveryLoop = require('./discovery-loop');
const MeshManager = require('./mesh-manager');
const ServiceDiscovery = require('./service-discovery');

class GatewayServer {
  constructor(options = {}) {
    this.port = options.port || process.env.GATEWAY_PORT || 8080;
    this.host = options.host || process.env.HOST || '0.0.0.0';
    this.nodeEnv = process.env.NODE_ENV || 'development';
    
    // Discovery configuration
    this.namespace = options.namespace || process.env.NAMESPACE || 'default';
    this.labelSelector = options.labelSelector || process.env.SERVICE_SELECTOR_LABELS || 'app.kubernetes.io/managed-by=kubevela';
    this.discoveryInterval = options.discoveryInterval || process.env.DISCOVERY_INTERVAL || '5m';
    this.autoDiscovery = (options.autoDiscovery !== undefined) ? options.autoDiscovery : (process.env.AUTO_DISCOVERY !== 'false');
    
    // Gateway configuration
    this.exposePlayground = (options.exposePlayground !== undefined) ? options.exposePlayground : (process.env.EXPOSE_PLAYGROUND !== 'false');
    this.exposeIntrospection = (options.exposeIntrospection !== undefined) ? options.exposeIntrospection : (process.env.EXPOSE_INTROSPECTION === 'true');
    this.enableCors = (options.enableCors !== undefined) ? options.enableCors : (process.env.ENABLE_CORS !== 'false');
    
    this.app = express();
    this.server = null;
    this.isReady = false;
    
    // Initialize components
    this.discoveryLoop = new DiscoveryLoop({
      namespace: this.namespace,
      labelSelector: this.labelSelector,
      interval: this.discoveryInterval
    });
    
    this.meshManager = this.discoveryLoop.meshManager;
    
    // Graceful shutdown handling
    this.setupGracefulShutdown();
    
    console.log(`🚀 GraphQL Gateway Server initialized`);
    console.log(`   Namespace: ${this.namespace}`);
    console.log(`   Label Selector: ${this.labelSelector}`);
    console.log(`   Auto Discovery: ${this.autoDiscovery}`);
    console.log(`   Discovery Interval: ${this.discoveryInterval}`);
  }

  /**
   * Initialize and start the server
   * @returns {Promise<void>}
   */
  async start() {
    try {
      console.log('🔧 Setting up Express middleware...');
      await this.setupMiddleware();
      
      console.log('🔧 Setting up GraphQL endpoint...');
      await this.setupGraphQLEndpoint();
      
      console.log('🔧 Setting up API routes...');
      this.setupRoutes();
      
      console.log('🔧 Setting up error handling...');
      this.setupErrorHandling();
      
      // Start discovery loop if auto-discovery is enabled
      if (this.autoDiscovery) {
        console.log('🔄 Starting service discovery loop...');
        await this.discoveryLoop.start();
      } else {
        console.log('⏸️  Auto-discovery disabled, creating fallback mesh...');
        await this.meshManager.createFallbackConfiguration();
      }
      
      // Start HTTP server
      await this.startHttpServer();
      
      this.isReady = true;
      console.log(`✅ GraphQL Gateway Server running on http://${this.host}:${this.port}`);
      console.log(`   GraphQL Endpoint: http://${this.host}:${this.port}/graphql`);
      console.log(`   Health Check: http://${this.host}:${this.port}/healthz`);
      console.log(`   Status: http://${this.host}:${this.port}/status`);
      
      if (this.exposePlayground) {
        console.log(`   GraphQL Playground: http://${this.host}:${this.port}/graphql`);
      }
      
    } catch (error) {
      console.error('❌ Failed to start GraphQL Gateway Server:', error.message);
      process.exit(1);
    }
  }

  /**
   * Setup Express middleware
   */
  async setupMiddleware() {
    // Security middleware
    this.app.use(helmet({
      contentSecurityPolicy: this.nodeEnv === 'production' ? undefined : false,
      crossOriginEmbedderPolicy: false
    }));
    
    // Compression
    this.app.use(compression());
    
    // CORS
    if (this.enableCors) {
      this.app.use(cors({
        origin: this.nodeEnv === 'production' ? false : true, // Configure properly for production
        methods: ['GET', 'POST', 'OPTIONS'],
        allowedHeaders: ['Content-Type', 'Authorization', 'X-API-Key'],
        credentials: true
      }));
    }
    
    // Rate limiting
    if (this.nodeEnv === 'production') {
      const limiter = rateLimit({
        windowMs: 15 * 60 * 1000, // 15 minutes
        max: 1000, // limit each IP to 1000 requests per windowMs
        message: 'Too many requests from this IP, please try again later.',
        standardHeaders: true,
        legacyHeaders: false
      });
      this.app.use('/graphql', limiter);
    }
    
    // Request parsing
    this.app.use(express.json({ limit: '10mb' }));
    this.app.use(express.urlencoded({ extended: true, limit: '10mb' }));
    
    // Request logging
    this.app.use((req, res, next) => {
      const start = Date.now();
      res.on('finish', () => {
        const duration = Date.now() - start;
        console.log(`${req.method} ${req.url} ${res.statusCode} - ${duration}ms`);
      });
      next();
    });
  }

  /**
   * Setup GraphQL endpoint
   */
  async setupGraphQLEndpoint() {
    this.app.use('/graphql', (req, res, next) => {
      // Get current schema from mesh manager
      const schema = this.meshManager.getSchema();
      
      if (!schema) {
        return res.status(503).json({
          error: 'GraphQL schema not available',
          message: 'Service discovery is still in progress or no services found'
        });
      }
      
      // Create GraphQL HTTP handler with current schema
      const graphqlHandler = graphqlHTTP({
        schema,
        graphiql: this.exposePlayground && this.nodeEnv !== 'production',
        introspection: this.exposeIntrospection,
        context: {
          request: req,
          headers: req.headers
        },
        customFormatErrorFn: (error) => {
          console.error('GraphQL Error:', error);
          return {
            message: error.message,
            locations: error.locations,
            path: error.path,
            ...(this.nodeEnv !== 'production' && { stack: error.stack })
          };
        }
      });
      
      return graphqlHandler(req, res, next);
    });
  }

  /**
   * Setup API routes
   */
  setupRoutes() {
    // Health check endpoint
    this.app.get('/healthz', (req, res) => {
      const meshStatus = this.meshManager.getHealthStatus();
      const discoveryStatus = this.discoveryLoop.getStatus();
      
      const isHealthy = this.isReady && meshStatus.status === 'healthy';
      
      res.status(isHealthy ? 200 : 503).json({
        status: isHealthy ? 'healthy' : 'unhealthy',
        timestamp: new Date().toISOString(),
        mesh: meshStatus,
        discovery: {
          isRunning: discoveryStatus.isRunning,
          lastSuccessfulRun: discoveryStatus.lastSuccessfulRun,
          lastError: discoveryStatus.lastError
        }
      });
    });

    // Readiness probe
    this.app.get('/readyz', (req, res) => {
      const schema = this.meshManager.getSchema();
      const isReady = this.isReady && !!schema;
      
      res.status(isReady ? 200 : 503).json({
        ready: isReady,
        schema: !!schema,
        timestamp: new Date().toISOString()
      });
    });

    // Status endpoint with detailed information
    this.app.get('/status', (req, res) => {
      const discoveryStatus = this.discoveryLoop.getStatus();
      const meshStats = this.meshManager.getStats();
      
      res.json({
        server: {
          version: '1.0.0',
          nodeEnv: this.nodeEnv,
          uptime: process.uptime(),
          ready: this.isReady
        },
        configuration: {
          namespace: this.namespace,
          labelSelector: this.labelSelector,
          autoDiscovery: this.autoDiscovery,
          discoveryInterval: this.discoveryInterval,
          exposePlayground: this.exposePlayground,
          exposeIntrospection: this.exposeIntrospection
        },
        discovery: discoveryStatus,
        mesh: meshStats,
        timestamp: new Date().toISOString()
      });
    });

    // Metrics endpoint
    this.app.get('/metrics', (req, res) => {
      const metrics = this.discoveryLoop.getMetrics();
      res.json(metrics);
    });

    // Force discovery endpoint
    this.app.post('/api/discovery/force', async (req, res) => {
      try {
        console.log('🚀 Forcing discovery via API request');
        await this.discoveryLoop.forceDiscovery();
        res.json({
          success: true,
          message: 'Discovery forced successfully',
          timestamp: new Date().toISOString()
        });
      } catch (error) {
        console.error('❌ Force discovery failed:', error.message);
        res.status(500).json({
          success: false,
          error: error.message,
          timestamp: new Date().toISOString()
        });
      }
    });

    // Configuration update endpoint
    this.app.put('/api/config', (req, res) => {
      try {
        const { interval, labelSelector, retryDelay, maxRetries } = req.body;
        
        this.discoveryLoop.updateConfig({
          interval,
          labelSelector,
          retryDelay,
          maxRetries
        });
        
        res.json({
          success: true,
          message: 'Configuration updated successfully',
          timestamp: new Date().toISOString()
        });
      } catch (error) {
        console.error('❌ Configuration update failed:', error.message);
        res.status(400).json({
          success: false,
          error: error.message,
          timestamp: new Date().toISOString()
        });
      }
    });

    // Root endpoint
    this.app.get('/', (req, res) => {
      res.json({
        service: 'GraphQL Gateway',
        version: '1.0.0',
        endpoints: {
          graphql: '/graphql',
          health: '/healthz',
          ready: '/readyz',
          status: '/status',
          metrics: '/metrics'
        },
        timestamp: new Date().toISOString()
      });
    });
  }

  /**
   * Setup error handling
   */
  setupErrorHandling() {
    // 404 handler
    this.app.use((req, res) => {
      res.status(404).json({
        error: 'Not Found',
        message: `Cannot ${req.method} ${req.url}`,
        timestamp: new Date().toISOString()
      });
    });

    // Error handler
    this.app.use((err, req, res, next) => {
      console.error('Express Error:', err);
      
      res.status(err.status || 500).json({
        error: err.name || 'Internal Server Error',
        message: err.message,
        timestamp: new Date().toISOString(),
        ...(this.nodeEnv !== 'production' && { stack: err.stack })
      });
    });
  }

  /**
   * Start the HTTP server
   * @returns {Promise<void>}
   */
  startHttpServer() {
    return new Promise((resolve, reject) => {
      this.server = this.app.listen(this.port, this.host, (error) => {
        if (error) {
          reject(error);
        } else {
          resolve();
        }
      });
      
      this.server.on('error', (error) => {
        if (error.code === 'EADDRINUSE') {
          console.error(`❌ Port ${this.port} is already in use`);
        } else {
          console.error('❌ Server error:', error);
        }
        reject(error);
      });
    });
  }

  /**
   * Setup graceful shutdown handling
   */
  setupGracefulShutdown() {
    const shutdown = async (signal) => {
      console.log(`\n📡 Received ${signal}, starting graceful shutdown...`);
      
      try {
        // Stop accepting new connections
        if (this.server) {
          console.log('🔌 Closing HTTP server...');
          this.server.close();
        }
        
        // Stop discovery loop
        console.log('⏹️  Stopping discovery loop...');
        await this.discoveryLoop.stop();
        
        console.log('✅ Graceful shutdown completed');
        process.exit(0);
      } catch (error) {
        console.error('❌ Error during shutdown:', error);
        process.exit(1);
      }
    };

    process.on('SIGTERM', () => shutdown('SIGTERM'));
    process.on('SIGINT', () => shutdown('SIGINT'));
    
    // Handle uncaught exceptions
    process.on('uncaughtException', (error) => {
      console.error('💥 Uncaught Exception:', error);
      shutdown('uncaughtException');
    });
    
    process.on('unhandledRejection', (reason, promise) => {
      console.error('💥 Unhandled Rejection at:', promise, 'reason:', reason);
      shutdown('unhandledRejection');
    });
  }

  /**
   * Stop the server
   * @returns {Promise<void>}
   */
  async stop() {
    console.log('⏹️  Stopping GraphQL Gateway Server...');
    
    this.isReady = false;
    
    if (this.server) {
      this.server.close();
    }
    
    await this.discoveryLoop.stop();
    
    console.log('✅ GraphQL Gateway Server stopped');
  }
}

module.exports = GatewayServer;