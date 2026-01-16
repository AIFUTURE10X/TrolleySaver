# Australian Grocery Price Database - Local Setup

This Docker setup runs the [aus_grocery_price_database](https://github.com/tjhowse/aus_grocery_price_database) project locally, collecting real-time prices from Woolworths and Coles.

## Prerequisites

- **Docker Desktop** - [Download here](https://www.docker.com/products/docker-desktop/)
- **Git** - [Download here](https://git-scm.com/downloads)

## Quick Start

### Windows
```batch
cd docker
setup.bat
```

### Linux/Mac
```bash
cd docker
chmod +x setup.sh
./setup.sh
```

## What Gets Installed

| Service | Port | Purpose |
|---------|------|---------|
| **InfluxDB** | 8087 | Time-series database storing price data |
| **Grafana** | 3030 | Dashboard for visualizing price trends |
| **Scraper** | - | Collects prices from Woolworths & Coles |

## Access Points

After setup completes:

- **Grafana Dashboard**: http://localhost:3030
  - Username: `admin`
  - Password: `grocerygrafana123` (or check `.env`)

- **InfluxDB UI**: http://localhost:8087
  - Username: `admin`
  - Password: `grocerypassword123` (or check `.env`)

## Price Update Schedule

| Setting | Value | Description |
|---------|-------|-------------|
| Update check | Every 10 seconds | How often new data is written to DB |
| Product refresh | Every 24 hours | How often each product's price is re-fetched |

You can modify these in `.env`:
```
UPDATE_RATE_SECONDS=10
MAX_PRODUCT_AGE_MINUTES=1440
```

## Common Commands

```bash
# View scraper logs (see what's being collected)
docker-compose logs -f scraper

# Check all services status
docker-compose ps

# Stop all services (keeps data)
docker-compose down

# Stop and DELETE all data
docker-compose down -v

# Restart services
docker-compose restart

# Rebuild after code changes
docker-compose build --no-cache
docker-compose up -d
```

## Data Collection Timeline

- **First hour**: Initial product discovery, ~1000-5000 products
- **First day**: Building comprehensive database
- **Ongoing**: Continuous price monitoring and updates

## Querying the Data

### Via Grafana
Create dashboards using InfluxDB as the data source. Example Flux query:

```flux
from(bucket: "groceries")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "product")
  |> filter(fn: (r) => r.name =~ /milk/i)
```

### Via InfluxDB UI
1. Go to http://localhost:8087
2. Click "Data Explorer"
3. Build queries using the visual builder or Flux

### Via API
```bash
curl -X POST "http://localhost:8087/api/v2/query?org=groceries" \
  -H "Authorization: Token my-super-secret-grocery-token" \
  -H "Content-Type: application/vnd.flux" \
  -d 'from(bucket:"groceries") |> range(start:-1h) |> limit(n:10)'
```

## Troubleshooting

### Scraper not collecting data
```bash
# Check logs for errors
docker-compose logs scraper

# Restart scraper
docker-compose restart scraper
```

### InfluxDB connection issues
```bash
# Verify InfluxDB is healthy
docker-compose ps
curl http://localhost:8087/ping
```

### Out of disk space
```bash
# Check Docker disk usage
docker system df

# Clean up old images
docker system prune
```

## File Structure

```
docker/
├── docker-compose.yml          # Main orchestration file
├── .env.example                 # Environment template
├── .env                         # Your local settings (created on setup)
├── setup.bat                    # Windows setup script
├── setup.sh                     # Linux/Mac setup script
├── README.md                    # This file
├── grafana/
│   └── provisioning/
│       └── datasources/
│           └── influxdb.yml    # Auto-configures InfluxDB in Grafana
└── aus_grocery_price_database/ # Cloned scraper repo (created on setup)
```

## Next Steps

Once you have price data collecting:

1. **Build an API** on top of InfluxDB to serve your app
2. **Add ALDI data** manually or via catalogue parsing
3. **Create product matching** to compare same products across stores
4. **Build your mobile app** consuming the API
