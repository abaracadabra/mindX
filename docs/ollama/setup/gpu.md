# GPU Support

## NVIDIA

**Requires**: Compute capability 5.0+, driver 531+

Key families: RTX 50xx (CC 12.0), RTX 40xx (CC 8.9), RTX 30xx (CC 8.6), GTX 10xx (CC 6.1), Tesla (CC 5.0-9.0)

Full list: [developer.nvidia.com/cuda-gpus](https://developer.nvidia.com/cuda-gpus)

### GPU Selection

```bash
# Use specific GPUs (UUID preferred over numeric ID)
CUDA_VISIBLE_DEVICES=0,1 ollama serve

# Force CPU only
CUDA_VISIBLE_DEVICES=-1 ollama serve

# Find UUIDs
nvidia-smi -L
```

### Linux Suspend/Resume Fix

```bash
sudo rmmod nvidia_uvm && sudo modprobe nvidia_uvm
```

## AMD Radeon

**Requires**: ROCm v7 driver on Linux, ROCm v6.1 on Windows

Supported: RX 9000/7000/6000/5000 series, Radeon PRO, Ryzen AI, Instinct MI100-MI350X

### Override GFX Version (Unsupported GPUs)

```bash
# For RX 5400 (gfx1034, closest supported: gfx1030)
HSA_OVERRIDE_GFX_VERSION="10.3.0" ollama serve

# Per-GPU override
HSA_OVERRIDE_GFX_VERSION_0=10.3.0 HSA_OVERRIDE_GFX_VERSION_1=11.0.0 ollama serve
```

### GPU Selection

```bash
ROCR_VISIBLE_DEVICES=0 ollama serve
```

## Apple Metal

Supported automatically on Apple Silicon (M1/M2/M3/M4).

## Vulkan (Experimental)

Additional GPU support on Windows and Linux:

```bash
OLLAMA_VULKAN=1 ollama serve
```

Requires Vulkan drivers. For VRAM reporting:

```bash
sudo setcap cap_perfmon+ep /usr/local/bin/ollama
```

### Docker with GPU

```bash
# NVIDIA
docker run -d --gpus=all -v ollama:/root/.ollama -p 11434:11434 ollama/ollama

# AMD
docker run -d --device /dev/kfd --device /dev/dri -v ollama:/root/.ollama -p 11434:11434 ollama/ollama:rocm

# Vulkan in Docker
docker run -d --device /dev/kfd --device /dev/dri -e OLLAMA_VULKAN=1 -v ollama:/root/.ollama -p 11434:11434 ollama/ollama
```

## mindX GPU Server (10.0.0.155)

When the GPU server is online:
- Primary inference at `http://10.0.0.155:18080`
- Larger models (llama3:70b, mistral-nemo)
- Automatic failover to localhost:11434 when unreachable

```bash
# Test GPU server
curl http://10.0.0.155:18080/api/tags
```
