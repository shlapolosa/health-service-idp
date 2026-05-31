/**
 * GraphQL Mesh Manager
 * Dynamically manages GraphQL Mesh configuration and schema federation
 */

const { getMesh } = require('@graphql-mesh/runtime');
const { findAndParseConfig } = require('@graphql-mesh/config');
const { join } = require('path');
const { writeFileSync, existsSync, mkdirSync } = require('fs');
const { makeExecutableSchema } = require('@graphql-tools/schema');
const { stitchSchemas } = require('@graphql-tools/stitch');

class MeshManager {
  constructor() {
    this.mesh = null;
    this.currentServices = new Map();
    this.currentSchemas = new Map();
    this.configPath = join(__dirname, '../config');
    this.meshConfigPath = join(this.configPath, '.meshrc.yml');
    
    // Ensure config directory exists
    if (!existsSync(this.configPath)) {
      mkdirSync(this.configPath, { recursive: true });
    }
  }

  /**
   * Update mesh configuration with discovered services
   * @param {Array} discoveredServices - Array of services with OpenAPI specs
   * @returns {Promise<boolean>} True if configuration was updated and mesh rebuilt
   */
  async updateConfiguration(discoveredServices) {
    try {
      console.log(`🔧 Updating GraphQL Mesh configuration with ${discoveredServices.length} services`);
      
      // Filter services that have OpenAPI specs
      const servicesWithSpecs = discoveredServices.filter(service => 
        service.hasOpenApi && service.openApiSpec
      );
      
      if (servicesWithSpecs.length === 0) {
        console.log('⚠️  No services with OpenAPI specs found, using fallback configuration');
        return await this.createFallbackConfiguration();
      }
      
      // Check if services have changed
      const servicesChanged = this.hasServicesChanged(servicesWithSpecs);
      if (!servicesChanged) {
        console.log('📋 Services haven\'t changed, keeping current mesh configuration');
        return false;
      }
      
      // Generate new mesh configuration
      const meshConfig = this.generateMeshConfig(servicesWithSpecs);
      
      // Write mesh configuration file
      this.writeMeshConfig(meshConfig);
      
      // Rebuild mesh with new configuration
      const success = await this.rebuildMesh();
      
      if (success) {
        // Update our service tracking
        this.updateServiceTracking(servicesWithSpecs);
        console.log(`✅ GraphQL Mesh updated with ${servicesWithSpecs.length} federated services`);
      }
      
      return success;
    } catch (error) {
      console.error('❌ Failed to update mesh configuration:', error.message);
      throw error;
    }
  }

  /**
   * Check if the discovered services have changed from current services
   * @param {Array} newServices - Newly discovered services
   * @returns {boolean} True if services have changed
   */
  hasServicesChanged(newServices) {
    if (newServices.length !== this.currentServices.size) {
      return true;
    }
    
    return newServices.some(service => {
      const currentService = this.currentServices.get(service.name);
      if (!currentService) return true;
      
      // Check if service URL or last updated changed
      return (
        currentService.url !== service.url ||
        currentService.lastUpdated !== service.lastUpdated ||
        JSON.stringify(currentService.openApiSpec) !== JSON.stringify(service.openApiSpec)
      );
    });
  }

  /**
   * Generate GraphQL Mesh configuration from services
   * @param {Array} services - Services with OpenAPI specifications
   * @returns {Object} Mesh configuration object
   */
  generateMeshConfig(services) {
    const sources = services.map(service => ({
      name: service.name,
      handler: {
        openapi: {
          source: service.openApiUrl || `${service.url}/openapi.json`,
          baseUrl: service.url,
          operationHeaders: {
            'User-Agent': 'GraphQL-Mesh-Gateway/1.0',
            'Accept': 'application/json'
          }
        }
      },
      transforms: [
        {
          prefix: {
            value: `${this.toPascalCase(service.name)}_`,
            includeRootOperations: true
          }
        },
        {
          namingConvention: {
            mode: 'bare',
            typeNames: 'PascalCase',
            fieldNames: 'camelCase'
          }
        }
      ]
    }));

    const config = {
      sources,
      serve: {
        port: 8080,
        hostname: '0.0.0.0',
        cors: {
          origin: '*',
          methods: ['GET', 'POST', 'OPTIONS'],
          allowedHeaders: ['Content-Type', 'Authorization', 'X-API-Key']
        },
        playground: true,
        introspection: true
      },
      logger: {
        level: 'info'
      },
      cache: {
        redis: false // Disable Redis for now - can be enabled later
      }
    };

    return config;
  }

  /**
   * Create fallback configuration when no services are available
   * @returns {Promise<boolean>}
   */
  async createFallbackConfiguration() {
    console.log('🔧 Creating fallback GraphQL configuration');
    
    const fallbackConfig = {
      sources: [],
      serve: {
        port: 8080,
        hostname: '0.0.0.0',
        cors: {
          origin: '*',
          methods: ['GET', 'POST', 'OPTIONS'],
          allowedHeaders: ['Content-Type', 'Authorization', 'X-API-Key']
        },
        playground: true,
        introspection: true
      },
      logger: {
        level: 'info'
      }
    };

    this.writeMeshConfig(fallbackConfig);
    return await this.rebuildMesh();
  }

  /**
   * Write mesh configuration to file
   * @param {Object} config - Mesh configuration
   */
  writeMeshConfig(config) {
    const yaml = require('js-yaml');
    const configYaml = yaml.dump(config, { 
      indent: 2,
      lineWidth: 120,
      noRefs: true
    });
    
    writeFileSync(this.meshConfigPath, configYaml, 'utf8');
    console.log(`📄 Mesh configuration written to ${this.meshConfigPath}`);
  }

  /**
   * Rebuild GraphQL Mesh with current configuration
   * @returns {Promise<boolean>} True if successful
   */
  async rebuildMesh() {
    try {
      console.log('🔄 Rebuilding GraphQL Mesh...');
      
      // Dispose current mesh if exists
      if (this.mesh && typeof this.mesh.destroy === 'function') {
        await this.mesh.destroy();
      }
      
      // Find and parse the mesh configuration
      const meshConfig = await findAndParseConfig({
        configName: '.meshrc',
        dir: this.configPath
      });
      
      if (!meshConfig) {
        throw new Error('Failed to parse mesh configuration');
      }
      
      // Create new mesh instance
      this.mesh = await getMesh(meshConfig);
      
      console.log('✅ GraphQL Mesh rebuilt successfully');
      return true;
    } catch (error) {
      console.error('❌ Failed to rebuild mesh:', error.message);
      
      // Try to create a basic executable schema as fallback
      try {
        console.log('🔄 Creating fallback schema...');
        const fallbackSchema = this.createFallbackSchema();
        this.mesh = { schema: fallbackSchema };
        console.log('✅ Fallback schema created');
        return true;
      } catch (fallbackError) {
        console.error('❌ Failed to create fallback schema:', fallbackError.message);
        return false;
      }
    }
  }

  /**
   * Create a basic fallback schema when mesh fails
   * @returns {Object} GraphQL schema
   */
  createFallbackSchema() {
    const typeDefs = `
      type Query {
        status: String
        discoveredServices: [ServiceInfo]
      }
      
      type ServiceInfo {
        name: String!
        namespace: String!
        url: String
        ready: Boolean!
        hasOpenApi: Boolean!
      }
    `;

    const resolvers = {
      Query: {
        status: () => 'GraphQL Gateway is running with fallback schema',
        discoveredServices: () => Array.from(this.currentServices.values()).map(service => ({
          name: service.name,
          namespace: service.namespace,
          url: service.url,
          ready: service.ready,
          hasOpenApi: service.hasOpenApi
        }))
      }
    };

    return makeExecutableSchema({ typeDefs, resolvers });
  }

  /**
   * Update internal service tracking
   * @param {Array} services - Current services
   */
  updateServiceTracking(services) {
    this.currentServices.clear();
    services.forEach(service => {
      this.currentServices.set(service.name, {
        name: service.name,
        namespace: service.namespace,
        url: service.url,
        ready: service.ready,
        hasOpenApi: service.hasOpenApi,
        lastUpdated: service.lastUpdated,
        openApiSpec: service.openApiSpec
      });
    });
  }

  /**
   * Get current GraphQL schema
   * @returns {Object|null} Current GraphQL schema
   */
  getSchema() {
    if (!this.mesh) {
      return null;
    }
    
    return this.mesh.schema || this.mesh.getSchema?.();
  }

  /**
   * Get current mesh instance
   * @returns {Object|null} Current mesh instance
   */
  getMeshInstance() {
    return this.mesh;
  }

  /**
   * Get statistics about current configuration
   * @returns {Object} Configuration statistics
   */
  getStats() {
    return {
      servicesCount: this.currentServices.size,
      meshConfigured: !!this.mesh,
      configPath: this.meshConfigPath,
      services: Array.from(this.currentServices.keys())
    };
  }

  /**
   * Convert string to PascalCase
   * @param {string} str - Input string
   * @returns {string} PascalCase string
   */
  toPascalCase(str) {
    return str
      .replace(/[^a-zA-Z0-9]+/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase())
      .replace(/\s/g, '');
  }

  /**
   * Health check for mesh manager
   * @returns {Object} Health status
   */
  getHealthStatus() {
    return {
      status: this.mesh ? 'healthy' : 'unhealthy',
      servicesCount: this.currentServices.size,
      meshConfigured: !!this.mesh,
      lastUpdate: new Date().toISOString(),
      configExists: existsSync(this.meshConfigPath)
    };
  }

  /**
   * Cleanup resources
   */
  async cleanup() {
    console.log('🧹 Cleaning up mesh manager resources...');
    
    if (this.mesh && typeof this.mesh.destroy === 'function') {
      await this.mesh.destroy();
    }
    
    this.mesh = null;
    this.currentServices.clear();
    this.currentSchemas.clear();
    
    console.log('✅ Mesh manager cleanup completed');
  }
}

module.exports = MeshManager;