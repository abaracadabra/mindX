# Getting Started with Ollama

## Installation

### Linux (Recommended for mindX)

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Docker

```bash
# CPU
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama

# NVIDIA GPU
docker run -d --gpus=all -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama

# AMD GPU
docker run -d --device /dev/kfd --device /dev/dri -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama:rocm
```

### macOS / Windows

Download from [ollama.com/download](https://ollama.com/download)

## First Run

```bash
# Start the server (if not running as service)
ollama serve

# Pull a model
ollama pull qwen3:1.7b

# Run interactively
ollama run qwen3:1.7b "Hello!"

# Pull embedding model
ollama pull mxbai-embed-large
```

## Interactive Menu

```bash
ollama
# Navigate with arrows, Enter to launch, Esc to quit
```

## Verify

```bash
# Version
ollama -v

# List models
ollama list

# API test
curl http://localhost:11434/api/tags

# Generate test
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3:1.7b",
  "prompt": "Hello!",
  "stream": false
}'
```

## Systemd Service (Linux)

The install script sets this up automatically. To manage:

```bash
sudo systemctl status ollama
sudo systemctl restart ollama
journalctl -u ollama --follow
```

### Custom Configuration

```bash
sudo systemctl edit ollama
# Add under [Service]:
# Environment="OLLAMA_HOST=0.0.0.0:11434"
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

## Uninstall (Linux)

```bash
sudo systemctl stop ollama
sudo systemctl disable ollama
sudo rm /etc/systemd/system/ollama.service
sudo rm -r $(which ollama | tr 'bin' 'lib')
sudo rm $(which ollama)
sudo userdel ollama
sudo groupdel ollama
sudo rm -r /usr/share/ollama
```

## mindX Quick Setup

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull models for mindX
ollama pull qwen3:1.7b           # Default autonomous model
ollama pull mxbai-embed-large    # Embeddings for RAGE
ollama pull nomic-embed-text     # Alternative embeddings

# 3. Set in .env
echo 'MINDX_LLM__OLLAMA__BASE_URL=http://localhost:11434' >> .env

# 4. Test connection
python scripts/test_ollama_connection.py

# 5. Start mindX
./mindX.sh --frontend
```
