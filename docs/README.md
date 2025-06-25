# NBA Play-by-Play API Documentation

This directory contains comprehensive documentation for the NBA Play-by-Play API project.

## Available Documentation

### Database Management
- **[Database Management Guide](database-management.md)** - Complete documentation for database synchronization tools, workflows, and best practices
- **[Selective Sync Quick Reference](selective-sync-quick-reference.md)** - Quick reference guide for the selective synchronization tool

### API Documentation
- **[API Health Check Guide](../instructions/API-health-check.md)** - Comprehensive API testing procedures and health monitoring

### Development
- **[Project Guide (CLAUDE.md)](../CLAUDE.md)** - Complete project guidance and implementation details
- **[Instructions Directory](../instructions/)** - Individual development plans and guides

## Tool Quick Links

### Database Synchronization
```bash
# Recommended daily workflow
python -m src.database.selective_sync --analyze --ignore-size
python -m src.database.selective_sync --sync --ignore-size

# Full documentation
docs/database-management.md
```

### API Testing
```bash
# Health check
curl http://localhost:8000/health

# Full test suite
# See instructions/API-health-check.md
```

### Database Monitoring
```bash
# Statistics
python -m src.database.database_stats --neon

# Comparison
python -m src.database.database_comparison
```

## Getting Started

1. **Set up environment**: Ensure virtual environment is activated
2. **Database access**: Configure DATABASE_URL for Neon access
3. **Daily workflow**: Use selective sync for routine updates
4. **API testing**: Run health checks after deployments

For detailed setup and usage instructions, see the main [README.md](../README.md) and individual documentation files.