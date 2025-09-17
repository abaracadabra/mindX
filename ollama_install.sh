#!/bin/bash

# Ollama Installation Script for MindX
# This script installs Ollama as a local LLM fallback when Mistral API is not available

echo "🚀 Installing Ollama for MindX LLM fallback..."

# Check if Ollama is already installed
if command -v ollama &> /dev/null; then
    echo "✅ Ollama is already installed"
    ollama --version
else
    echo "📥 Installing Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh
    
    if [ $? -eq 0 ]; then
        echo "✅ Ollama installed successfully"
    else
        echo "❌ Failed to install Ollama"
        exit 1
    fi
fi

echo "📦 Pulling Mistral models for MindX..."

# Pull essential Mistral models
echo "Pulling mistral:7b-instruct (fast, general purpose)..."
ollama pull mistral:7b-instruct

echo "Pulling mistral:8x7b-instruct (better performance)..."
ollama pull mistral:8x7b-instruct

echo "Pulling codestral:latest (code generation)..."
ollama pull codestral:latest

echo "Pulling mistral:large (best performance)..."
ollama pull mistral:large

echo "🔧 Configuring MindX to use Ollama..."

# Create a simple config update script
cat > /tmp/ollama_config_update.py << 'EOF'
import json
import os

# Update the MindX config to enable Ollama
config_path = "data/config/mindx_config.json"

if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Enable Ollama provider
    if 'llm' not in config:
        config['llm'] = {}
    if 'providers' not in config['llm']:
        config['llm']['providers'] = {}
    
    config['llm']['providers']['ollama'] = {"enabled": True}
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✅ Updated MindX config to enable Ollama")
else:
    print("⚠️  MindX config not found, please enable Ollama manually")
EOF

python3 /tmp/ollama_config_update.py
rm /tmp/ollama_config_update.py

    echo ""
echo "🎉 Ollama setup complete!"
    echo ""
echo "📋 Next steps:"
echo "1. Start Ollama service: ollama serve"
echo "2. Restart MindX backend service"
echo "3. AGInt will now use Ollama as a fallback when Mistral API is not available"
    echo ""
echo "🔍 To test Ollama:"
echo "   ollama run mistral:7b-instruct"
echo ""
echo "💡 To see available models:"
echo "   ollama list"