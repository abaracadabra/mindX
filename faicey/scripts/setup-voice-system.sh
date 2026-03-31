#!/bin/bash

# Setup Voice System - Install TTS Libraries and Dependencies
# © Professor Codephreak - rage.pythai.net
# Organizations: github.com/agenticplace, github.com/cryptoagi, github.com/Professor-Codephreak

echo "🗣️ Setting up Faicey Voice Creation System"
echo "© Professor Codephreak - Advanced TTS Integration"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_warning "Running as root. Consider running as regular user for security."
    fi
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get &> /dev/null; then
            OS="ubuntu"
            PACKAGE_MANAGER="apt-get"
        elif command -v yum &> /dev/null; then
            OS="rhel"
            PACKAGE_MANAGER="yum"
        elif command -v dnf &> /dev/null; then
            OS="fedora"
            PACKAGE_MANAGER="dnf"
        elif command -v pacman &> /dev/null; then
            OS="arch"
            PACKAGE_MANAGER="pacman"
        else
            OS="unknown"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        PACKAGE_MANAGER="brew"
    else
        OS="unknown"
    fi

    print_status "Detected OS: $OS"
}

# Install system packages
install_system_packages() {
    print_status "Installing system packages for TTS engines..."

    case $OS in
        "ubuntu")
            print_status "Installing packages via apt-get..."
            sudo apt-get update

            # Core TTS engines
            sudo apt-get install -y espeak-ng espeak-ng-data
            sudo apt-get install -y festival festvox-kallpc16k festvox-kdlpc16k
            sudo apt-get install -y flite

            # Audio processing tools
            sudo apt-get install -y sox libsox-fmt-all
            sudo apt-get install -y ffmpeg
            sudo apt-get install -y pulseaudio pulseaudio-utils
            sudo apt-get install -y alsa-utils

            # Additional TTS engines (if available)
            sudo apt-get install -y libttspico-utils || print_warning "pico2wave not available in repositories"

            # Development tools
            sudo apt-get install -y build-essential
            sudo apt-get install -y libasound2-dev
            sudo apt-get install -y libpulse-dev

            print_success "Ubuntu packages installed"
            ;;

        "fedora")
            print_status "Installing packages via dnf..."
            sudo dnf update -y

            sudo dnf install -y espeak-ng espeak-ng-devel
            sudo dnf install -y festival festvox-kal-diphone
            sudo dnf install -y flite flite-devel
            sudo dnf install -y sox
            sudo dnf install -y ffmpeg
            sudo dnf install -y pulseaudio pulseaudio-utils
            sudo dnf install -y alsa-utils

            print_success "Fedora packages installed"
            ;;

        "arch")
            print_status "Installing packages via pacman..."
            sudo pacman -Sy

            sudo pacman -S --noconfirm espeak-ng
            sudo pacman -S --noconfirm festival festival-english
            sudo pacman -S --noconfirm flite
            sudo pacman -S --noconfirm sox
            sudo pacman -S --noconfirm ffmpeg
            sudo pacman -S --noconfirm pulseaudio pulseaudio-alsa
            sudo pacman -S --noconfirm alsa-utils

            print_success "Arch Linux packages installed"
            ;;

        "macos")
            print_status "Installing packages via Homebrew..."

            if ! command -v brew &> /dev/null; then
                print_error "Homebrew not found. Please install Homebrew first."
                print_status "Visit: https://brew.sh"
                return 1
            fi

            brew update
            brew install espeak-ng
            brew install festival
            brew install flite
            brew install sox
            brew install ffmpeg

            print_success "macOS packages installed"
            ;;

        *)
            print_error "Unsupported OS: $OS"
            print_status "Please install TTS engines manually:"
            print_status "- espeak-ng"
            print_status "- festival"
            print_status "- flite"
            print_status "- sox"
            print_status "- ffmpeg"
            return 1
            ;;
    esac
}

# Test TTS engines
test_tts_engines() {
    print_status "Testing TTS engines..."

    # Test espeak-ng
    if command -v espeak-ng &> /dev/null; then
        print_success "espeak-ng available"
        espeak-ng --version 2>/dev/null || print_warning "espeak-ng version check failed"
    else
        print_error "espeak-ng not found"
    fi

    # Test festival
    if command -v festival &> /dev/null; then
        print_success "festival available"
    else
        print_warning "festival not found"
    fi

    # Test flite
    if command -v flite &> /dev/null; then
        print_success "flite available"
        flite -version 2>/dev/null || print_warning "flite version check failed"
    else
        print_warning "flite not found"
    fi

    # Test pico2wave
    if command -v pico2wave &> /dev/null; then
        print_success "pico2wave available"
    else
        print_warning "pico2wave not found"
    fi

    # Test audio tools
    if command -v sox &> /dev/null; then
        print_success "sox available"
        sox --version | head -1
    else
        print_error "sox not found - required for audio processing"
    fi

    if command -v ffmpeg &> /dev/null; then
        print_success "ffmpeg available"
    else
        print_warning "ffmpeg not found - optional but recommended"
    fi

    # Test audio playback
    if command -v paplay &> /dev/null; then
        print_success "paplay available (PulseAudio)"
    elif command -v aplay &> /dev/null; then
        print_success "aplay available (ALSA)"
    elif command -v play &> /dev/null; then
        print_success "play available (sox)"
    else
        print_warning "No audio playback tool found"
    fi
}

# Install Node.js dependencies
install_node_dependencies() {
    print_status "Installing Node.js dependencies..."

    if ! command -v npm &> /dev/null; then
        print_error "npm not found. Please install Node.js first."
        return 1
    fi

    # Navigate to faicey directory
    cd "$(dirname "$0")/.." || return 1

    print_status "Installing enhanced dependencies..."
    npm install

    # Additional audio processing packages
    npm install --save node-wav speaker
    npm install --save audio-context audiomotion-analyzer
    npm install --save audio-buffer-utils audio-buffer

    print_success "Node.js dependencies installed"
}

# Set up voice data directories
setup_directories() {
    print_status "Setting up voice data directories..."

    FAICEY_DIR="/tmp/faicey-voice"
    CACHE_DIR="$HOME/.cache/faicey"
    CONFIG_DIR="$HOME/.config/faicey"

    mkdir -p "$FAICEY_DIR"
    mkdir -p "$CACHE_DIR"
    mkdir -p "$CONFIG_DIR"

    # Set permissions
    chmod 755 "$FAICEY_DIR"
    chmod 755 "$CACHE_DIR"
    chmod 755 "$CONFIG_DIR"

    print_success "Directories created:"
    print_status "  Voice output: $FAICEY_DIR"
    print_status "  Cache: $CACHE_DIR"
    print_status "  Config: $CONFIG_DIR"
}

# Configure audio system
configure_audio() {
    print_status "Configuring audio system..."

    case $OS in
        "ubuntu"|"fedora"|"arch")
            # Check PulseAudio
            if command -v pulseaudio &> /dev/null; then
                if ! pulseaudio --check; then
                    print_status "Starting PulseAudio..."
                    pulseaudio --start --log-target=journal || print_warning "Failed to start PulseAudio"
                fi
                print_success "PulseAudio configured"
            fi

            # Check ALSA
            if command -v aplay &> /dev/null; then
                print_status "ALSA devices:"
                aplay -l | head -10 || print_warning "No ALSA devices found"
            fi
            ;;

        "macos")
            print_status "macOS audio system should be ready"
            ;;
    esac
}

# Create test voice samples
create_test_samples() {
    print_status "Creating test voice samples..."

    SAMPLE_DIR="$HOME/.cache/faicey/samples"
    mkdir -p "$SAMPLE_DIR"

    # Create test samples with different TTS engines
    if command -v espeak-ng &> /dev/null; then
        print_status "Creating espeak-ng sample..."
        espeak-ng -v en-us+f3 -p 55 -s 180 -w "$SAMPLE_DIR/jaimla_espeak.wav" \
            "Hello! I am Jaimla, your machine learning agent. I can speak with various voice engines!" || \
            print_warning "espeak-ng sample creation failed"
    fi

    if command -v festival &> /dev/null; then
        print_status "Creating festival sample..."
        echo "Hello! I am Jaimla, demonstrating festival voice synthesis." | \
            festival --tts --output "$SAMPLE_DIR/jaimla_festival.wav" 2>/dev/null || \
            print_warning "festival sample creation failed"
    fi

    if command -v flite &> /dev/null; then
        print_status "Creating flite sample..."
        flite -voice slt -t "Hello! This is Jaimla speaking through flite TTS engine." \
            -o "$SAMPLE_DIR/jaimla_flite.wav" || \
            print_warning "flite sample creation failed"
    fi

    print_success "Test samples created in $SAMPLE_DIR"
}

# Test voice generation
test_voice_generation() {
    print_status "Testing voice generation system..."

    cd "$(dirname "$0")/.." || return 1

    # Create simple test script
    cat > test_voice.js << 'EOF'
import { VoiceCreationEngine } from './src/voice/VoiceCreationEngine.js';

async function testVoice() {
    try {
        console.log('🗣️ Testing Voice Creation Engine...');

        const engine = new VoiceCreationEngine({
            agentId: 'test-agent',
            voiceId: 'jaimla'
        });

        await engine.init();

        console.log('✅ Engine initialized, generating test speech...');

        const speechFile = await engine.generateSpeech(
            "Hello! This is a test of the Jaimla voice system. I am the machine learning agent!",
            { autoPlay: false }
        );

        console.log(`✅ Speech generated: ${speechFile}`);
        console.log('🔊 Test completed successfully!');

        await engine.shutdown();

    } catch (error) {
        console.error('❌ Voice test failed:', error.message);
        process.exit(1);
    }
}

testVoice();
EOF

    print_status "Running voice generation test..."
    node test_voice.js

    if [ $? -eq 0 ]; then
        print_success "Voice generation test passed!"
    else
        print_error "Voice generation test failed!"
    fi

    # Clean up
    rm -f test_voice.js
}

# Create configuration file
create_config() {
    print_status "Creating configuration file..."

    CONFIG_FILE="$HOME/.config/faicey/voice-config.json"

    cat > "$CONFIG_FILE" << EOF
{
  "ttsEngine": "espeak-ng",
  "defaultVoice": "en-us+f3",
  "sampleRate": 44100,
  "outputPath": "/tmp/faicey-voice",
  "voiceCharacteristics": {
    "jaimla": {
      "gender": "female",
      "basePitch": 55,
      "speed": 180,
      "energy": 0.8
    }
  },
  "audioSettings": {
    "autoPlay": false,
    "cleanup": true,
    "quality": "high"
  },
  "integrations": {
    "voiceyBridge": true,
    "backgroundManager": true,
    "agenticplace": true
  }
}
EOF

    print_success "Configuration created: $CONFIG_FILE"
}

# Main installation process
main() {
    echo
    echo "🎭 Faicey Voice System Setup"
    echo "============================"

    check_root
    detect_os

    echo
    print_status "Starting installation process..."

    # Step 1: Install system packages
    if ! install_system_packages; then
        print_error "Failed to install system packages"
        exit 1
    fi

    # Step 2: Test TTS engines
    echo
    test_tts_engines

    # Step 3: Install Node.js dependencies
    echo
    install_node_dependencies

    # Step 4: Set up directories
    echo
    setup_directories

    # Step 5: Configure audio
    echo
    configure_audio

    # Step 6: Create test samples
    echo
    create_test_samples

    # Step 7: Create configuration
    echo
    create_config

    # Step 8: Test voice generation
    echo
    if command -v node &> /dev/null; then
        test_voice_generation
    else
        print_warning "Node.js not available, skipping voice generation test"
    fi

    echo
    print_success "🎉 Faicey Voice System setup complete!"
    echo
    print_status "Quick Start:"
    print_status "  npm run jaimla              # Run Jaimla demo with voice"
    print_status "  npm run voice-test           # Test voice generation"
    print_status "  npm run enhanced-jaimla      # Run enhanced Jaimla with full features"
    echo
    print_status "Voice engines available:"
    command -v espeak-ng &> /dev/null && print_status "  ✅ espeak-ng (recommended)"
    command -v festival &> /dev/null && print_status "  ✅ festival"
    command -v flite &> /dev/null && print_status "  ✅ flite"
    command -v pico2wave &> /dev/null && print_status "  ✅ pico2wave"
    echo
    print_status "For more information, see README.md"
    echo
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi