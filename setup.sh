#!/bin/bash
# setup.sh - Linux/macOS Installation Script for Pacify & Defy
# Usage: chmod +x setup.sh && ./setup.sh

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ASCII Art Banner
show_banner() {
    echo -e "${CYAN}"
    cat << "EOF"
                                    
    ____             _ ____         ___         ____       ____       
   / __ \____ ______(_) __/_  __   ( _ )       / __ \___  / __/_  __
  / /_/ / __ `/ ___/ / /_/ / / /  / __ |      / / / / _ \/ /_/ / / /
 / ____/ /_/ / /__/ / __/ /_/ /  / /_/ _|_   / /_/ /  __/ __/ /_/ / 
/_/    \__,_/\___/_/_/  \__, /   \____/_|_| /_____/\___/_/  \__, /  
                       /____/                              /____/   
EOF
    echo -e "${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}              Dual-Mode Conversational AI System${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
}

# Print colored messages
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    else
        print_error "Unsupported OS: $OSTYPE"
        exit 1
    fi
    print_info "Detected OS: $OS"
}

# Check Python installation
check_python() {
    print_info "Checking Python installation..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_success "Python $PYTHON_VERSION found"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
        PYTHON_VERSION=$(python --version | cut -d' ' -f2)
        print_success "Python $PYTHON_VERSION found"
    else
        print_error "Python not found! Please install Python 3.8 or higher."
        echo ""
        echo "Installation instructions:"
        if [[ "$OS" == "linux" ]]; then
            echo "  Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip"
            echo "  Fedora/RHEL:   sudo dnf install python3 python3-pip"
            echo "  Arch:          sudo pacman -S python python-pip"
        elif [[ "$OS" == "macos" ]]; then
            echo "  Homebrew:      brew install python3"
        fi
        exit 1
    fi
}

# Check pip installation
check_pip() {
    print_info "Checking pip installation..."
    
    if command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
        print_success "pip3 found"
    elif command -v pip &> /dev/null; then
        PIP_CMD="pip"
        print_success "pip found"
    else
        print_error "pip not found! Installing pip..."
        $PYTHON_CMD -m ensurepip --upgrade
        PIP_CMD="$PYTHON_CMD -m pip"
    fi
}

# Create virtual environment
create_venv() {
    print_info "Creating virtual environment..."
    
    if [ ! -d "venv" ]; then
        $PYTHON_CMD -m venv venv
        print_success "Virtual environment created"
    else
        print_warning "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    print_success "Virtual environment activated"
}

# Install dependencies
install_dependencies() {
    print_info "Installing dependencies..."
    
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt not found!"
        exit 1
    fi
    
    pip install --upgrade pip > /dev/null 2>&1
    pip install -r requirements.txt
    print_success "All dependencies installed"
}

# Create directory structure
create_directories() {
    print_info "Creating directory structure..."
    
    mkdir -p data logs exports personas/pacify personas/defy
    touch data/.gitkeep logs/.gitkeep exports/.gitkeep
    
    print_success "Directory structure created"
}

# Configure Groq API
configure_api() {
    echo ""
    echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}                  API CONFIGURATION${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
    echo ""
    
    if [ -f ".env" ]; then
        print_warning ".env file already exists"
        read -p "$(echo -e ${YELLOW}Overwrite existing configuration? [y/N]:${NC} )" -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Keeping existing configuration"
            return
        fi
    fi
    
    echo -e "${BLUE}You need a Groq API key to use this system.${NC}"
    echo -e "${BLUE}Get your free API key at: ${CYAN}https://console.groq.com/keys${NC}"
    echo ""
    
    while true; do
        read -p "$(echo -e ${GREEN}Enter your Groq API key:${NC} )" GROQ_KEY
        
        if [ -z "$GROQ_KEY" ]; then
            print_error "API key cannot be empty!"
            continue
        fi
        
        # Basic validation (Groq keys start with 'gsk_')
        if [[ ! $GROQ_KEY == gsk_* ]]; then
            print_warning "This doesn't look like a valid Groq API key (should start with 'gsk_')"
            read -p "$(echo -e ${YELLOW}Use it anyway? [y/N]:${NC} )" -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                continue
            fi
        fi
        
        break
    done
    
    # Create .env file
    cat > .env << EOF
# Groq API Configuration
GROQ_API_KEY=$GROQ_KEY

# Optional: Enable debug mode
# PACIFY_DEBUG=false
EOF
    
    chmod 600 .env  # Secure the file
    print_success "API key configured successfully"
}

# Create launcher script
create_launcher() {
    print_info "Creating launcher script..."
    
    INSTALL_DIR=$(pwd)
    
    cat > pacify-defy.sh << EOF
#!/bin/bash
# Pacify & Defy Launcher

cd "$INSTALL_DIR"
source venv/bin/activate
python -m cli
deactivate
EOF
    
    chmod +x pacify-defy.sh
    print_success "Launcher script created"
}

# Setup shell alias
setup_alias() {
    print_info "Setting up global command alias..."
    
    INSTALL_DIR=$(pwd)
    SHELL_NAME=$(basename "$SHELL")
    
    # Determine shell config file
    if [[ "$SHELL_NAME" == "bash" ]]; then
        if [[ "$OS" == "macos" ]]; then
            RC_FILE="$HOME/.bash_profile"
        else
            RC_FILE="$HOME/.bashrc"
        fi
    elif [[ "$SHELL_NAME" == "zsh" ]]; then
        RC_FILE="$HOME/.zshrc"
    else
        print_warning "Unknown shell: $SHELL_NAME"
        RC_FILE="$HOME/.bashrc"
    fi
    
    # Check if alias already exists
    if grep -q "alias pacify-defy=" "$RC_FILE" 2>/dev/null; then
        print_warning "Alias already exists in $RC_FILE"
        return
    fi
    
    # Add alias
    echo "" >> "$RC_FILE"
    echo "# Pacify & Defy - Global Command" >> "$RC_FILE"
    echo "alias pacify-defy='$INSTALL_DIR/pacify-defy.sh'" >> "$RC_FILE"
    
    print_success "Alias added to $RC_FILE"
    
    # Source the file to make it available immediately
    source "$RC_FILE" 2>/dev/null || true
}

# Verify installation
verify_installation() {
    print_info "Verifying installation..."
    
    # Check required files
    REQUIRED_FILES=(".env" "venv" "core" "personas" "requirements.txt")
    
    for file in "${REQUIRED_FILES[@]}"; do
        if [ -e "$file" ]; then
            print_success "$file exists"
        else
            print_error "$file missing!"
            return 1
        fi
    done
    
    # Check Python imports
    source venv/bin/activate
    if $PYTHON_CMD -c "import requests, rich, pyfiglet" 2>/dev/null; then
        print_success "All Python packages installed correctly"
    else
        print_error "Some Python packages are missing!"
        return 1
    fi
    
    print_success "Installation verified successfully"
}

# Show completion message
show_completion() {
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}             ✓ INSTALLATION COMPLETE!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}To start using Pacify & Defy:${NC}"
    echo ""
    echo -e "  ${YELLOW}1.${NC} Reload your shell configuration:"
    if [[ "$SHELL_NAME" == "bash" ]]; then
        echo -e "     ${BLUE}source ~/.bashrc${NC}"
    elif [[ "$SHELL_NAME" == "zsh" ]]; then
        echo -e "     ${BLUE}source ~/.zshrc${NC}"
    fi
    echo ""
    echo -e "  ${YELLOW}2.${NC} Run the system from anywhere:"
    echo -e "     ${BLUE}pacify-defy${NC}"
    echo ""
    echo -e "${CYAN}Alternative (without alias):${NC}"
    echo -e "     ${BLUE}cd $(pwd) && ./pacify-defy.sh${NC}"
    echo ""
    echo -e "${CYAN}Quick Start:${NC}"
    echo -e "  • Type ${YELLOW}/help${NC} to see all commands"
    echo -e "  • Type ${YELLOW}/setmode defy${NC} to switch to uncensored mode"
    echo -e "  • Type ${YELLOW}/persona sage${NC} for task-oriented coding"
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Main installation flow
main() {
    show_banner
    
    detect_os
    check_python
    check_pip
    create_venv
    install_dependencies
    create_directories
    configure_api
    create_launcher
    setup_alias
    verify_installation
    
    show_completion
}

# Run main function
main
