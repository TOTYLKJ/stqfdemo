# STQCF - A Privacy-Preserving Semantic Trajectory Query System in Cloud-Fog Collaborative Environments

STQCF is a comprehensive geospatial data processing platform that integrates frontend visualization interfaces and backend data processing services, supporting secure spatial trajectory queries, fog server management, and data visualization features.

## Project Overview

The STQCF platform consists of the following main components:

- **Frontend Application**: Web interface based on React and TypeScript
- **Backend Service**: RESTful API service based on Django
- **Data Processing**: Support for trajectory data processing and spatial queries
- **Security Mechanism**: Integration of homomorphic encryption and spatiotemporal verification
- **Fog Servers**: Distributed data processing nodes

## Technology Stack

### Frontend Stack
- React 18
- TypeScript 4.9
- Ant Design 5.0
- Redux Toolkit
- React Router 6
- Mapbox GL/Leaflet/AntV L7
- ECharts 5.6
- Axios

### Backend Stack
- Python 3.8+
- Django 3.2+
- MySQL 5.7+
- Cassandra 3.11+
- Docker
- Kubernetes

## Project Structure

```
STQCF/
├── apps/                    # Application modules
│   ├── stv/                # Spatiotemporal verification module
│   └── sstp/               # Secure spatiotemporal trajectory processing module
├── database/               # Database related
│   ├── migrations/         # Database migration files
│   ├── schemas/            # Database schemas
│   └── indexes/            # Database indexes
├── deployment/             # Deployment configuration
│   ├── docker/            # Docker configuration
│   ├── scripts/           # Deployment scripts
│   └── kubernetes/        # K8s configuration
├── stqcf_project/           # Django project configuration
│   ├── settings/          # Project settings
│   └── urls.py            # URL routing
├── stqcf-backend/           # Backend service
│   ├── apps/              # Backend applications
│   ├── core/              # Core functionality
│   ├── tasks/             # Background tasks
│   └── tests/             # Test cases
└── stqcf-frontend/          # Frontend application
    ├── public/            # Static resources
    ├── src/               # Source code
    └── package.json       # Dependency configuration
```

## Core Features

### 1. Secure Spatial Queries
- Query parameter protection based on homomorphic encryption
- Spatiotemporal trajectory verification
- Distributed query processing
- Result decryption and verification

### 2. Fog Server Management
- Distributed node management
- Load balancing
- Status monitoring
- Keyword grouping

### 3. Data Visualization
- Interactive maps
- Trajectory display
- Heat maps
- Statistical analysis

### 4. Data Management
- Trajectory data import/export
- Data quality checking
- Batch operations
- Data maintenance

## Environment Requirements

### Development Environment
- Node.js 16.x+
- Python 3.8+
- MySQL 5.7+
- Cassandra 3.11+
- Docker (optional)

### Production Environment
- Same as development environment requirements
- Kubernetes (optional)
- Nginx

## Installation and Deployment

### 1. Backend Service Deployment

```bash
# Clone the project
git clone [project URL]

# Enter backend directory
cd stqcf-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Initialize database
python manage.py migrate

# Start service
python manage.py runserver
```

### 2. Frontend Application Deployment

```bash
# Enter frontend directory
cd stqcf-frontend

# Install dependencies
npm install

# Start development environment
npm start

# Build for production
npm run build
```

### 3. Docker Deployment

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d
```

## Configuration Guide

### Database Configuration
- MySQL configuration: `stqcf-backend/apps/query/setup/init_db.py`
- Cassandra configuration: `stqcf-backend/apps/query/README.md`

### Environment Variables
```bash
# MySQL configuration
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=3306
export MYSQL_DATABASE=gko_db
export MYSQL_USER=root
export MYSQL_PASSWORD=sl201301

# Cassandra configuration
export CASSANDRA_HOSTS=localhost
export CASSANDRA_PORT=9042
export CASSANDRA_USER=cassandra
export CASSANDRA_PASSWORD=cassandra

# Docker environment
export DOCKER_ENV=false
```

## Development Guide

### Code Standards
- Frontend: ESLint + Prettier
- Backend: PEP 8
- Commit messages: Conventional Commits

### Testing
- Frontend: Jest + React Testing Library
- Backend: Django Test Framework

### Documentation
- API documentation: Swagger/OpenAPI
- Component documentation: Storybook
- Development documentation: Markdown

## Security Notes

- JWT-based authentication
- Homomorphic encryption for query parameter protection
- Role-based access control
- Secure data transmission

## Maintenance and Support

- Issue reporting: [Issue Tracker]
- Documentation updates: [Documentation]
- Technical support: [Support]

## License

[License Type]

## Contribution Guide

1. Fork the project
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Version History

- v1.0.0 - Initial version
  - Basic functionality implementation
  - Secure query support
  - Data visualization 