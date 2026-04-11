# Docker Deployment

## CPU Only

```bash
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
```

## NVIDIA GPU

### 1. Install NVIDIA Container Toolkit

```bash
# Debian/Ubuntu
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
    | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
    | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
    | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# RHEL/CentOS
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo \
    | sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo
sudo yum install -y nvidia-container-toolkit
```

### 2. Configure Docker

```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### 3. Run

```bash
docker run -d --gpus=all -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
```

## AMD GPU

```bash
docker run -d --device /dev/kfd --device /dev/dri \
    -v ollama:/root/.ollama -p 11434:11434 \
    --name ollama ollama/ollama:rocm
```

## Vulkan

```bash
docker run -d --device /dev/kfd --device /dev/dri \
    -e OLLAMA_VULKAN=1 \
    -v ollama:/root/.ollama -p 11434:11434 \
    --name ollama ollama/ollama
```

## Run Models

```bash
docker exec -it ollama ollama run qwen3:1.7b
docker exec -it ollama ollama pull mxbai-embed-large
```

## With Proxy

```bash
docker run -d -e HTTPS_PROXY=https://proxy.example.com \
    -p 11434:11434 ollama/ollama
```

### Custom CA Certificate

```dockerfile
FROM ollama/ollama
COPY my-ca.pem /usr/local/share/ca-certificates/my-ca.crt
RUN update-ca-certificates
```

```bash
docker build -t ollama-with-ca .
docker run -d -e HTTPS_PROXY=https://my.proxy.example.com -p 11434:11434 ollama-with-ca
```

## Docker Compose (mindX + Ollama)

```yaml
version: '3.8'
services:
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_KEEP_ALIVE=5m
      - OLLAMA_MAX_LOADED_MODELS=1
    restart: unless-stopped

  mindx:
    build: .
    ports:
      - "8000:8000"
      - "3000:3000"
    environment:
      - MINDX_LLM__OLLAMA__BASE_URL=http://ollama:11434
    depends_on:
      - ollama

volumes:
  ollama_data:
```

## Troubleshooting

### GPU Switches to CPU After Time

Edit `/etc/docker/daemon.json`:

```json
{"exec-opts": ["native.cgroupdriver=cgroupfs"]}
```

### SELinux Container GPU Access

```bash
sudo setsebool container_use_devices=1
```

### JetPack (NVIDIA Jetson)

```bash
docker run -d --gpus=all -e JETSON_JETPACK=6 -v ollama:/root/.ollama -p 11434:11434 ollama/ollama
```
