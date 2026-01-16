#!/bin/bash

echo "================================================"
echo "Australian Grocery Price Database - Setup"
echo "================================================"
echo

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running!"
    echo "Please start Docker and try again."
    exit 1
fi

echo "Docker is running. Proceeding with setup..."
echo

# Check if Git is available
if ! git --version > /dev/null 2>&1; then
    echo "ERROR: Git is not installed!"
    echo "Please install Git and try again."
    exit 1
fi

# Clone the scraper repo if it doesn't exist
if [ ! -d "aus_grocery_price_database" ]; then
    echo "Cloning aus_grocery_price_database repository..."
    git clone https://github.com/tjhowse/aus_grocery_price_database.git
    echo
else
    echo "Updating aus_grocery_price_database repository..."
    cd aus_grocery_price_database
    git pull
    cd ..
    echo
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo
    echo "IMPORTANT: Edit .env to change default passwords!"
    echo
fi

# Build and start services
echo "Building and starting services (this may take a few minutes)..."
docker-compose build
docker-compose up -d
echo

# Wait for services to be ready
echo "Waiting for services to initialize (60 seconds)..."
sleep 60

# Show status
echo
echo "================================================"
echo "Setup Complete!"
echo "================================================"
echo
echo "Services running:"
docker-compose ps
echo
echo "Access points:"
echo "  - Grafana Dashboard: http://localhost:3030"
echo "    Username: admin"
echo "    Password: grocerygrafana123 (or see .env file)"
echo
echo "  - InfluxDB UI: http://localhost:8087"
echo "    Username: admin"
echo "    Password: grocerypassword123 (or see .env file)"
echo
echo "The scraper is now collecting prices from:"
echo "  - Woolworths"
echo "  - Coles"
echo
echo "Price Refresh Schedule:"
echo "  - Checks for updates: Every 10 seconds"
echo "  - Full product refresh: Every 24 hours"
echo
echo "Useful commands:"
echo "  docker-compose logs -f scraper    View scraper logs"
echo "  docker-compose ps                 Check service status"
echo "  docker-compose down               Stop all services"
echo "  docker-compose down -v            Stop and delete all data"
echo
echo "NOTE: It may take several hours to build up a full"
echo "      price database. Check Grafana for progress!"
