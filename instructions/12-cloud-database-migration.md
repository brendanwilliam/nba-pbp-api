# 12 - Cloud Database Migration

## Objective
Migrate the NBA play-by-play database from local PostgreSQL to a cloud-hosted solution, ensuring scalability, reliability, and optimal performance for API serving.

## Background
With the local database populated with historical NBA data, migrate to a cloud platform to support public API access, ensure high availability, and enable horizontal scaling as usage grows.

## Scope
- **Cloud Provider Selection**: AWS, Google Cloud, or Azure evaluation
- **Migration Strategy**: Zero-downtime migration approach
- **Performance Optimization**: Cloud-specific optimizations
- **Cost Management**: Efficient resource allocation

## Implementation Plan

### Phase 1: Cloud Provider Evaluation
1. **AWS RDS PostgreSQL**
   ```
   Pros:
   - Mature managed service
   - Excellent backup/recovery
   - Read replicas for scaling
   - Aurora PostgreSQL option
   
   Cons:
   - Higher cost for large datasets
   - Vendor lock-in considerations
   
   Estimated Cost: $200-500/month for production workload
   ```

2. **Google Cloud SQL**
   ```
   Pros:
   - Competitive pricing
   - Good integration with GKE
   - Automatic storage scaling
   
   Cons:
   - Less mature than AWS
   - Limited customization options
   
   Estimated Cost: $150-400/month
   ```

3. **Azure Database for PostgreSQL**
   ```
   Pros:
   - Strong enterprise features
   - Good compliance options
   - Flexible server options
   
   Cons:
   - Complex pricing model
   - Regional availability
   
   Estimated Cost: $180-450/month
   ```

### Phase 2: Architecture Design
1. **Production architecture**
   ```
   Load Balancer
   ├── API Servers (2-4 instances)
   ├── Primary Database (Write operations)
   ├── Read Replicas (2-3 instances)
   └── Redis Cache (Query caching)
   ```

2. **Database sizing**
   ```
   Storage: 100GB (with 50% growth buffer)
   Memory: 16GB RAM minimum
   CPU: 4-8 vCPUs
   IOPS: 3000+ for responsive queries
   ```

### Phase 3: Migration Strategy
1. **Zero-downtime migration approach**
   ```
   Phase 1: Setup cloud database
   Phase 2: Initial data sync
   Phase 3: Setup continuous replication
   Phase 4: Cutover during maintenance window
   Phase 5: Cleanup old infrastructure
   ```

2. **Data synchronization**
   ```python
   class DatabaseMigration:
       def setup_replication(self):
           # Configure logical replication
           # Setup publication on source
           # Create subscription on target
           
       def monitor_sync_lag(self):
           # Monitor replication lag
           # Alert if lag exceeds threshold
           
       def perform_cutover(self):
           # Stop writes to source
           # Verify sync completion
           # Update application configuration
           # Resume operations on target
   ```

### Phase 4: Cloud-Specific Optimizations
1. **AWS RDS optimizations**
   ```sql
   -- Enable performance insights
   -- Configure parameter groups
   SET shared_preload_libraries = 'pg_stat_statements';
   SET log_statement = 'all';
   SET log_min_duration_statement = 1000;
   
   -- Configure connection pooling
   -- Setup read replica endpoints
   ```

2. **Backup and recovery**
   ```
   Automated Backups:
   - Point-in-time recovery: 35 days
   - Daily snapshots
   - Cross-region backup replication
   
   Recovery Testing:
   - Monthly recovery drills
   - Documented recovery procedures
   - RTO: 15 minutes, RPO: 5 minutes
   ```

## Technical Implementation

### Migration Scripts
1. **Pre-migration validation**
   ```python
   def validate_migration_readiness():
       checks = [
           verify_data_consistency(),
           check_storage_requirements(),
           validate_network_connectivity(),
           test_authentication_setup()
       ]
       return all(checks)
   ```

2. **Data migration utilities**
   ```python
   class CloudMigrationTools:
       def export_database_dump(self):
           # Create compressed database dump
           # Split large tables for parallel processing
           
       def setup_logical_replication(self):
           # Configure WAL level
           # Create replication slot
           # Setup subscription
           
       def validate_data_integrity(self):
           # Compare row counts
           # Validate critical queries
           # Check constraint integrity
   ```

### Monitoring and Alerting
1. **Cloud monitoring setup**
   ```python
   monitoring_metrics = {
       'database_connections': {'threshold': 80, 'unit': 'percent'},
       'cpu_utilization': {'threshold': 85, 'unit': 'percent'},
       'memory_usage': {'threshold': 90, 'unit': 'percent'},
       'disk_space': {'threshold': 85, 'unit': 'percent'},
       'replication_lag': {'threshold': 10, 'unit': 'seconds'}
   }
   ```

2. **Performance monitoring**
   ```sql
   -- Setup slow query monitoring
   CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
   
   -- Monitor long-running queries
   SELECT query, mean_time, calls, total_time
   FROM pg_stat_statements
   WHERE mean_time > 5000
   ORDER BY mean_time DESC;
   ```

## Security and Compliance

### Security Configuration
1. **Network security**
   ```
   VPC Configuration:
   - Private subnet for database
   - Security groups restricting access
   - VPN/bastion host for admin access
   - SSL/TLS encryption in transit
   ```

2. **Access control**
   ```sql
   -- Create application-specific roles
   CREATE ROLE nba_api_read;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO nba_api_read;
   
   CREATE ROLE nba_api_write;
   GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO nba_api_write;
   
   -- Create application user
   CREATE USER api_user WITH PASSWORD 'secure_password';
   GRANT nba_api_read TO api_user;
   ```

3. **Data encryption**
   ```
   Encryption at Rest: AES-256
   Encryption in Transit: TLS 1.2+
   Key Management: Cloud KMS
   Certificate Management: Automated rotation
   ```

## Performance Optimization

### Database Tuning
1. **PostgreSQL configuration**
   ```sql
   -- Memory settings
   shared_buffers = 4GB
   effective_cache_size = 12GB
   work_mem = 256MB
   maintenance_work_mem = 1GB
   
   -- Checkpoint settings
   checkpoint_completion_target = 0.9
   wal_buffers = 64MB
   
   -- Query planner settings
   random_page_cost = 1.1  -- SSD storage
   effective_io_concurrency = 200
   ```

2. **Connection pooling**
   ```python
   # PgBouncer configuration
   pool_mode = transaction
   max_client_conn = 1000
   default_pool_size = 25
   reserve_pool_size = 5
   ```

### Query Optimization
1. **Read replica usage**
   ```python
   class DatabaseRouter:
       def route_query(self, query_type):
           if query_type in ['SELECT', 'EXPLAIN']:
               return self.read_replica_connection
           else:
               return self.primary_connection
   ```

2. **Caching strategy**
   ```python
   cache_config = {
       'popular_queries': {'ttl': 300, 'layer': 'redis'},
       'player_stats': {'ttl': 3600, 'layer': 'application'},
       'game_metadata': {'ttl': 86400, 'layer': 'cdn'}
   }
   ```

## Cost Optimization

### Resource Right-Sizing
1. **Instance sizing strategy**
   ```
   Development: db.t3.medium (2 vCPU, 4GB RAM)
   Staging: db.t3.large (2 vCPU, 8GB RAM)
   Production: db.r5.xlarge (4 vCPU, 32GB RAM)
   ```

2. **Storage optimization**
   ```
   Storage Type: gp3 (General Purpose SSD)
   Initial Size: 100GB
   IOPS: 3000 provisioned
   Throughput: 125 MB/s
   Auto-scaling: Enabled (up to 500GB)
   ```

### Cost Monitoring
1. **Budget alerts**
   - Monthly budget: $400
   - Alert thresholds: 80%, 90%, 100%
   - Cost anomaly detection

2. **Resource optimization**
   - Scheduled scaling for read replicas
   - Reserved instances for predictable workloads
   - Storage lifecycle policies

## Disaster Recovery

### Backup Strategy
1. **Automated backups**
   ```
   Frequency: Daily snapshots
   Retention: 30 days
   Cross-region replication: Enabled
   Point-in-time recovery: 35 days
   ```

2. **Recovery procedures**
   ```python
   def disaster_recovery_plan():
       steps = [
           'Assess impact and required recovery point',
           'Provision new database instance',
           'Restore from appropriate backup',
           'Update application configuration',
           'Verify data integrity',
           'Resume normal operations'
       ]
       return steps
   ```

## Success Criteria
- Zero data loss during migration
- Minimal downtime (<30 minutes)
- Improved query performance (20%+ faster)
- 99.9% uptime SLA achievement
- Cost within budget ($300-400/month)

## Timeline
- **Week 1**: Cloud provider selection and architecture design
- **Week 2**: Cloud infrastructure setup and testing
- **Week 3**: Migration execution and validation
- **Week 4**: Performance optimization and monitoring setup

## Dependencies
- Completed local database with all data (Plan 11)
- Cloud account setup and billing
- Network connectivity and security approvals
- API application ready for cloud deployment

## Next Steps
After completion:
1. API development and deployment (Plan 13)
2. Performance monitoring and optimization
3. Cost analysis and optimization
4. Security audit and compliance verification