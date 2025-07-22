#!/bin/bash
# AlienRecon Docker Wrapper Script
# This script provides a convenient interface for running AlienRecon in Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.yml"
SERVICE_NAME="alienrecon"
DOCKER_CMD="docker-compose"

# Function to print colored output
print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Function to check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        # Try docker compose (newer version)
        if docker compose version &> /dev/null; then
            DOCKER_CMD="docker compose"
        else
            print_error "Docker Compose is not installed. Please install Docker Compose first."
            exit 1
        fi
    fi
}

# Function to check if the image is built
check_image() {
    if ! docker images | grep -q "alienrecon"; then
        print_warn "AlienRecon Docker image not found. Building it now..."
        build_image
    fi
}

# Function to build the Docker image
build_image() {
    print_info "Building AlienRecon Docker image..."
    $DOCKER_CMD build
    print_info "Build complete!"
}

# Function to run AlienRecon commands
run_alienrecon() {
    check_image

    # Check if we need interactive mode
    case "$1" in
        recon|interactive)
            # These commands need interactive terminal
            exec $DOCKER_CMD run --rm -it $SERVICE_NAME alienrecon "$@"
            ;;
        *)
            # Other commands can run without -it
            exec $DOCKER_CMD run --rm $SERVICE_NAME alienrecon "$@"
            ;;
    esac
}

# Function to start services in background
start_services() {
    print_info "Starting AlienRecon services..."
    $DOCKER_CMD up -d
    print_info "Services started. You can now attach to the container."
}

# Function to stop services
stop_services() {
    print_info "Stopping AlienRecon services..."
    $DOCKER_CMD down
    print_info "Services stopped."
}

# Function to show logs
show_logs() {
    $DOCKER_CMD logs "$@"
}

# Function to execute shell in container
shell() {
    check_image
    print_info "Starting shell in AlienRecon container..."
    exec $DOCKER_CMD run --rm -it $SERVICE_NAME /bin/bash
}

# Function to run development mode
dev_mode() {
    print_info "Starting AlienRecon in development mode..."
    print_info "Source code will be mounted from current directory"
    exec $DOCKER_CMD -f docker-compose.yml -f docker-compose.dev.yml run --rm -it alienrecon /bin/bash
}

# Function to backup data
backup_data() {
    local backup_dir="${1:-./backups}"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_name="alienrecon_backup_${timestamp}.tar.gz"

    print_info "Creating backup of AlienRecon data..."
    mkdir -p "$backup_dir"

    # Create temporary container to access volumes
    docker run --rm \
        -v alienrecon_sessions:/sessions \
        -v alienrecon_cache:/cache \
        -v alienrecon_missions:/missions \
        -v "$(pwd)/$backup_dir":/backup \
        alpine tar czf "/backup/$backup_name" /sessions /cache /missions

    print_info "Backup created: $backup_dir/$backup_name"
}

# Function to restore data
restore_data() {
    local backup_file="$1"

    if [ -z "$backup_file" ] || [ ! -f "$backup_file" ]; then
        print_error "Backup file not found: $backup_file"
        exit 1
    fi

    print_warn "This will overwrite existing AlienRecon data. Continue? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        print_info "Restore cancelled."
        exit 0
    fi

    print_info "Restoring AlienRecon data from $backup_file..."

    # Create temporary container to restore volumes
    docker run --rm \
        -v alienrecon_sessions:/sessions \
        -v alienrecon_cache:/cache \
        -v alienrecon_missions:/missions \
        -v "$(realpath "$backup_file")":/backup.tar.gz \
        alpine tar xzf /backup.tar.gz -C /

    print_info "Restore complete!"
}

# Function to show usage
show_usage() {
    cat << EOF
AlienRecon Docker Wrapper

Usage: $0 [COMMAND] [ARGS...]

Commands:
    build               Build the Docker image
    run [ARGS...]      Run AlienRecon with the specified arguments
    start              Start services in background
    stop               Stop background services
    shell              Open a shell in the container
    dev                Start in development mode with source mounted
    logs [OPTIONS]     Show container logs
    backup [DIR]       Backup AlienRecon data (default: ./backups)
    restore FILE       Restore AlienRecon data from backup
    help               Show this help message

Examples:
    $0 build                                    # Build the Docker image
    $0 run recon --target 10.10.10.10          # Start reconnaissance
    $0 run interactive                         # Launch TUI mode
    $0 run cache status                        # Check cache status
    $0 shell                                   # Open shell in container
    $0 backup                                  # Create backup
    $0 restore ./backups/alienrecon_backup.tar.gz  # Restore backup

For more information, see DOCKER_USAGE.md
EOF
}

# Main script logic
check_docker

case "$1" in
    build)
        build_image
        ;;
    run)
        shift
        run_alienrecon "$@"
        ;;
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    shell)
        shell
        ;;
    dev)
        dev_mode
        ;;
    logs)
        shift
        show_logs "$@"
        ;;
    backup)
        backup_data "$2"
        ;;
    restore)
        restore_data "$2"
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        # If no command specified, pass all arguments to alienrecon
        run_alienrecon "$@"
        ;;
esac
