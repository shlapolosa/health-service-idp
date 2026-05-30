#!/usr/bin/env node

const fs = require('fs');
const { mergeSchemas } = require('@graphql-tools/merge');
const { print } = require('graphql');
const { buildSchema } = require('graphql');

// Simple schema merger for GraphQL schemas
// Usage: node merge-schemas.js generated.graphql custom.graphql > merged.graphql

if (process.argv.length < 4) {
    console.error('Usage: node merge-schemas.js <generated-schema> <custom-schema>');
    process.exit(1);
}

try {
    // Read schema files
    const generatedSchema = fs.readFileSync(process.argv[2], 'utf8');
    const customSchema = fs.readFileSync(process.argv[3], 'utf8');
    
    // Parse schemas
    const schemas = [];
    
    // Add generated schema if valid
    try {
        const parsed = buildSchema(generatedSchema);
        schemas.push(parsed);
    } catch (e) {
        console.error('Warning: Could not parse generated schema:', e.message);
    }
    
    // Add custom schema if valid and not empty
    if (customSchema && customSchema.trim() !== '') {
        try {
            const parsed = buildSchema(customSchema);
            schemas.push(parsed);
        } catch (e) {
            console.error('Warning: Could not parse custom schema:', e.message);
        }
    }
    
    if (schemas.length === 0) {
        console.error('Error: No valid schemas to merge');
        process.exit(1);
    }
    
    // If only one schema, just print it
    if (schemas.length === 1) {
        console.log(print(schemas[0]));
        process.exit(0);
    }
    
    // Merge schemas
    const merged = mergeSchemas({
        schemas: schemas,
        // Prefer custom schema types over generated ones
        resolvers: {}
    });
    
    // Print merged schema
    console.log(print(merged));
    
} catch (error) {
    console.error('Error merging schemas:', error.message);
    process.exit(1);
}

// Fallback if @graphql-tools/merge is not available
// This provides a simple concatenation approach
if (!mergeSchemas) {
    console.warn('Warning: @graphql-tools/merge not available, using simple concatenation');
    
    const generatedSchema = fs.readFileSync(process.argv[2], 'utf8');
    const customSchema = fs.readFileSync(process.argv[3], 'utf8');
    
    // Simple concatenation with deduplication
    const lines = new Set();
    
    // Add generated schema lines
    generatedSchema.split('\n').forEach(line => {
        if (line.trim() && !line.startsWith('#')) {
            lines.add(line);
        }
    });
    
    // Add custom schema lines (will override duplicates)
    customSchema.split('\n').forEach(line => {
        if (line.trim() && !line.startsWith('#')) {
            lines.add(line);
        }
    });
    
    // Output merged schema
    console.log('# Merged GraphQL Schema');
    console.log('# Generated at:', new Date().toISOString());
    console.log('');
    console.log(Array.from(lines).join('\n'));
}