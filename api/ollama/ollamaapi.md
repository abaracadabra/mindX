# Ollama API — Working Reference

**Last updated:** 2026-01-31

This file is a **working reference** derived from the official Ollama API docs.

## Find and kill Ollama (doubletap)

When you need to free the Ollama port or terminate Ollama (e.g. before re-running bootstrap, or for startup_agent when the host must clear the port), use the **doubletap** script in this directory:

- **Script:** `api/ollama/doubletap.sh` (c) 2025 Gregory L. Magnusson  
- **Usage (from project root):** `./api/ollama/doubletap.sh` or `bash api/ollama/doubletap.sh`  
- **What it does:** find and kill Ollama/llama on a custom port (default 11434), Ollama shepherd boot y/N control, UFW rules to keep Ollama as localhost-only, and a local-access audit. Interactive; run by an operator when needed. Handy for startup_agent workflows where the host must ensure the port is free or Ollama is stopped before bootstrap. Use it for day-to-day development; for the canonical source and to get updates, use the official repository:

- **Get updates (canonical source):** [github.com/ollama/ollama — docs/api.md](https://github.com/ollama/ollama/edit/main/docs/api.md)
- **Official API docs:** [docs.ollama.com/api](https://docs.ollama.com/api)
- **Python library:** [github.com/ollama/ollama-python](https://github.com/ollama/ollama-python) — `pip install ollama`; chat, generate, list, embed, streaming, async client.
- **JavaScript library:** [github.com/ollama/ollama-js](https://github.com/ollama/ollama-js) — `npm i ollama`; chat, generate, list, embed, streaming, browser module.

## Endpoints

- [Generate a completion](#generate-a-completion)
- [Generate a chat completion](#generate-a-chat-completion)
- [Create a Model](#create-a-model)
- [List Local Models](#list-local-models)
- [Show Model Information](#show-model-information)
- [Copy a Model](#copy-a-model)
- [Delete a Model](#delete-a-model)
- [Pull a Model](#pull-a-model)
- [Push a Model](#push-a-model)
- [Generate Embeddings](#generate-embeddings)
- [List Running Models](#list-running-models)
- [Version](#version)
- [Experimental: Image Generation](#image-generation-experimental)

## Conventions

### Model names

Model names follow a `model:tag` format, where `model` can have an optional namespace such as `example/model`. Some examples are `orca-mini:3b-q8_0` and `llama3:70b`. The tag is optional and, if not provided, will default to `latest`. The tag is used to identify a specific version.

### Durations

All durations are returned in nanoseconds.

### Streaming responses

Certain endpoints stream responses as JSON objects. Streaming can be disabled by providing `{"stream": false}` for these endpoints.

## Generate a completion

```
POST /api/generate
```

Generate a response for a given prompt with a provided model. This is a streaming endpoint, so there will be a series of responses. The final response object will include statistics and additional data from the request.

### Parameters

- `model`: (required) the [model name](#model-names)
- `prompt`: the prompt to generate a response for
- `suffix`: the text after the model response
- `images`: (optional) a list of base64-encoded images (for multimodal models such as `llava`)
- `think`: (for thinking models) should the model think before responding?

Advanced parameters (optional):

- `format`: the format to return a response in. Format can be `json` or a JSON schema
- `options`: additional model parameters listed in the documentation for the [Modelfile](./modelfile.mdx#valid-parameters-and-values) such as `temperature`
- `system`: system message to (overrides what is defined in the `Modelfile`)
- `template`: the prompt template to use (overrides what is defined in the `Modelfile`)
- `stream`: if `false` the response will be returned as a single response object, rather than a stream of objects
- `raw`: if `true` no formatting will be applied to the prompt. You may choose to use the `raw` parameter if you are specifying a full templated prompt in your request to the API
- `keep_alive`: controls how long the model will stay loaded into memory following the request (default: `5m`)
- `context` (deprecated): the context parameter returned from a previous request to `/generate`, this can be used to keep a short conversational memory

Experimental image generation parameters (for image generation models only):

> [!WARNING]
> These parameters are experimental and may change in future versions.

- `width`: width of the generated image in pixels
- `height`: height of the generated image in pixels
- `steps`: number of diffusion steps

#### Structured outputs

Structured outputs are supported by providing a JSON schema in the `format` parameter. The model will generate a response that matches the schema. See the [structured outputs](#request-structured-outputs) example below.

#### JSON mode

Enable JSON mode by setting the `format` parameter to `json`. This will structure the response as a valid JSON object. See the JSON mode [example](#request-json-mode) below.

> [!IMPORTANT]
> It's important to instruct the model to use JSON in the `prompt`. Otherwise, the model may generate large amounts whitespace.

### Examples

#### Generate request (Streaming)

##### Request

```shell
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Why is the sky blue?"
}'
```

##### Response

A stream of JSON objects is returned:

```json
{
  "model": "llama3.2",
  "created_at": "2023-08-04T08:52:19.385406455-07:00",
  "response": "The",
  "done": false
}
```

The final response in the stream also includes additional data about the generation:

- `total_duration`: time spent generating the response
- `load_duration`: time spent in nanoseconds loading the model
- `prompt_eval_count`: number of tokens in the prompt
- `prompt_eval_duration`: time spent in nanoseconds evaluating the prompt
- `eval_count`: number of tokens in the response
- `eval_duration`: time in nanoseconds spent generating the response
- `context`: an encoding of the conversation used in this response, this can be sent in the next request to keep a conversational memory
- `response`: empty if the response was streamed, if not streamed, this will contain the full response

To calculate how fast the response is generated in tokens per second (token/s), divide `eval_count` / `eval_duration` \* `10^9`.

```json
{
  "model": "llama3.2",
  "created_at": "2023-08-04T19:22:45.499127Z",
  "response": "",
  "done": true,
  "context": [1, 2, 3],
  "total_duration": 10706818083,
  "load_duration": 6338219291,
  "prompt_eval_count": 26,
  "prompt_eval_duration": 130079000,
  "eval_count": 259,
  "eval_duration": 4232710000
}
```

#### Request (No streaming)

##### Request

A response can be received in one reply when streaming is off.

```shell
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Why is the sky blue?",
  "stream": false
}'
```

##### Response

If `stream` is set to `false`, the response will be a single JSON object:

```json
{
  "model": "llama3.2",
  "created_at": "2023-08-04T19:22:45.499127Z",
  "response": "The sky is blue because it is the color of the sky.",
  "done": true,
  "context": [1, 2, 3],
  "total_duration": 5043500667,
  "load_duration": 5025959,
  "prompt_eval_count": 26,
  "prompt_eval_duration": 325953000,
  "eval_count": 290,
  "eval_duration": 4709213000
}
```

#### Request (with suffix)

##### Request

```shell
curl http://localhost:11434/api/generate -d '{
  "model": "codellama:code",
  "prompt": "def compute_gcd(a, b):",
  "suffix": "    return result",
  "options": {
    "temperature": 0
  },
  "stream": false
}'
```

##### Response

```json5
{
  "model": "codellama:code",
  "created_at": "2024-07-22T20:47:51.147561Z",
  "response": "\n  if a == 0:\n    return b\n  else:\n    return compute_gcd(b % a, a)\n\ndef compute_lcm(a, b):\n  result = (a * b) / compute_gcd(a, b)\n",
  "done": true,
  "done_reason": "stop",
  "context": [...],
  "total_duration": 1162761250,
  "load_duration": 6683708,
  "prompt_eval_count": 17,
  "prompt_eval_duration": 201222000,
  "eval_count": 63,
  "eval_duration": 953997000
}
```

#### Request (Structured outputs)

##### Request

```shell
curl -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d '{
  "model": "llama3.1:8b",
  "prompt": "Ollama is 22 years old and is busy saving the world. Respond using JSON",
  "stream": false,
  "format": {
    "type": "object",
    "properties": {
      "age": {
        "type": "integer"
      },
      "available": {
        "type": "boolean"
      }
    },
    "required": [
      "age",
      "available"
    ]
  }
}'
```

##### Response

```json
{
  "model": "llama3.1:8b",
  "created_at": "2024-12-06T00:48:09.983619Z",
  "response": "{\n  \"age\": 22,\n  \"available\": true\n}",
  "done": true,
  "done_reason": "stop",
  "context": [1, 2, 3],
  "total_duration": 1075509083,
  "load_duration": 567678166,
  "prompt_eval_count": 28,
  "prompt_eval_duration": 236000000,
  "eval_count": 16,
  "eval_duration": 269000000
}
```

#### Request (JSON mode)

> [!IMPORTANT]
> When `format` is set to `json`, the output will always be a well-formed JSON object. It's important to also instruct the model to respond in JSON.

##### Request

```shell
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "What color is the sky at different times of the day? Respond using JSON",
  "format": "json",
  "stream": false
}'
```

##### Response

```json
{
  "model": "llama3.2",
  "created_at": "2023-11-09T21:07:55.186497Z",
  "response": "{\n\"morning\": {\n\"color\": \"blue\"\n},\n\"noon\": {\n\"color\": \"blue-gray\"\n},\n\"afternoon\": {\n\"color\": \"warm gray\"\n},\n\"evening\": {\n\"color\": \"orange\"\n}\n}\n",
  "done": true,
  "context": [1, 2, 3],
  "total_duration": 4648158584,
  "load_duration": 4071084,
  "prompt_eval_count": 36,
  "prompt_eval_duration": 439038000,
  "eval_count": 180,
  "eval_duration": 4196918000
}
```

The value of `response` will be a string containing JSON similar to:

```json
{
  "morning": { "color": "blue" },
  "noon": { "color": "blue-gray" },
  "afternoon": { "color": "warm gray" },
  "evening": { "color": "orange" }
}
```

#### Request (Raw Mode)

In some cases, you may wish to bypass the templating system and provide a full prompt. In this case, you can use the `raw` parameter to disable templating. Also note that raw mode will not return a context.

##### Request

```shell
curl http://localhost:11434/api/generate -d '{
  "model": "mistral",
  "prompt": "[INST] why is the sky blue? [/INST]",
  "raw": true,
  "stream": false
}'
```

#### Request (Reproducible outputs)

For reproducible outputs, set `seed` to a number:

##### Request

```shell
curl http://localhost:11434/api/generate -d '{
  "model": "mistral",
  "prompt": "Why is the sky blue?",
  "options": { "seed": 123 }
}'
```

#### Generate request (With options)

##### Request

```shell
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Why is the sky blue?",
  "stream": false,
  "options": {
    "num_keep": 5,
    "seed": 42,
    "num_predict": 100,
    "top_k": 20,
    "top_p": 0.9,
    "min_p": 0.0,
    "typical_p": 0.7,
    "repeat_last_n": 33,
    "temperature": 0.8,
    "repeat_penalty": 1.2,
    "presence_penalty": 1.5,
    "frequency_penalty": 1.0,
    "penalize_newline": true,
    "stop": ["\n", "user:"],
    "numa": false,
    "num_ctx": 1024,
    "num_batch": 2,
    "num_gpu": 1,
    "main_gpu": 0,
    "use_mmap": true,
    "num_thread": 8
  }
}'
```

#### Load a model

If an empty prompt is provided, the model will be loaded into memory.

##### Request

```shell
curl http://localhost:11434/api/generate -d '{ "model": "llama3.2" }'
```

#### Unload a model

If an empty prompt is provided and the `keep_alive` parameter is set to `0`, a model will be unloaded from memory.

##### Request

```shell
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "keep_alive": 0
}'
```

##### Response

```json
{
  "model": "llama3.2",
  "created_at": "2024-09-12T03:54:03.516566Z",
  "response": "",
  "done": true,
  "done_reason": "unload"
}
```

## Generate a chat completion

```
POST /api/chat
```

Generate the next message in a chat with a provided model. This is a streaming endpoint, so there will be a series of responses. Streaming can be disabled using `"stream": false`. The final response object will include statistics and additional data from the request.

### Parameters

- `model`: (required) the [model name](#model-names)
- `messages`: the messages of the chat, this can be used to keep a chat memory
- `tools`: list of tools in JSON for the model to use if supported
- `think`: (for thinking models) should the model think before responding?

The `message` object has the following fields:

- `role`: the role of the message, either `system`, `user`, `assistant`, or `tool`
- `content`: the content of the message
- `thinking`: (for thinking models) the model's thinking process
- `images` (optional): a list of images to include in the message (for multimodal models such as `llava`)
- `tool_calls` (optional): a list of tools in JSON that the model wants to use
- `tool_name` (optional): add the name of the tool that was executed to inform the model of the result

Advanced parameters (optional):

- `format`: the format to return a response in. Format can be `json` or a JSON schema.
- `options`: additional model parameters listed in the documentation for the [Modelfile](./modelfile.mdx#valid-parameters-and-values) such as `temperature`
- `stream`: if `false` the response will be returned as a single response object, rather than a stream of objects
- `keep_alive`: controls how long the model will stay loaded into memory following the request (default: `5m`)

### Examples

#### Chat request (Streaming)

##### Request

```shell
curl http://localhost:11434/api/chat -d '{
  "model": "llama3.2",
  "messages": [ { "role": "user", "content": "why is the sky blue?" } ]
}'
```

##### Response

A stream of JSON objects is returned. Final response includes `total_duration`, `load_duration`, `prompt_eval_count`, `eval_count`, `eval_duration`, etc.

#### Chat request (No streaming)

##### Request

```shell
curl http://localhost:11434/api/chat -d '{
  "model": "llama3.2",
  "messages": [ { "role": "user", "content": "why is the sky blue?" } ],
  "stream": false
}'
```

##### Response

```json
{
  "model": "llama3.2",
  "created_at": "2023-12-12T14:13:43.416799Z",
  "message": { "role": "assistant", "content": "Hello! How are you today?" },
  "done": true,
  "total_duration": 5191566416,
  "load_duration": 2154458,
  "prompt_eval_count": 26,
  "prompt_eval_duration": 383809000,
  "eval_count": 298,
  "eval_duration": 4799921000
}
```

#### Chat request (With History)

##### Request

```shell
curl http://localhost:11434/api/chat -d '{
  "model": "llama3.2",
  "messages": [
    { "role": "user", "content": "why is the sky blue?" },
    { "role": "assistant", "content": "due to rayleigh scattering." },
    { "role": "user", "content": "how is that different than mie scattering?" }
  ]
}'
```

#### Load a model (chat)

If the messages array is empty, the model will be loaded into memory.

##### Request

```shell
curl http://localhost:11434/api/chat -d '{ "model": "llama3.2", "messages": [] }'
```

#### Unload a model (chat)

If the messages array is empty and `keep_alive` is set to `0`, a model will be unloaded from memory.

##### Request

```shell
curl http://localhost:11434/api/chat -d '{
  "model": "llama3.2",
  "messages": [],
  "keep_alive": 0
}'
```

##### Response

```json
{
  "model": "llama3.2",
  "created_at": "2024-09-12T21:33:17.547535Z",
  "message": { "role": "assistant", "content": "" },
  "done_reason": "unload",
  "done": true
}
```

## Create a Model

```
POST /api/create
```

Create a model from: another model; a safetensors directory; or a GGUF file. If creating from safetensors or GGUF, you must [create a blob](#push-a-blob) for each file and use the file name and SHA256 digest in the `files` field.

### Parameters

- `model`: name of the model to create
- `from`: (optional) name of an existing model to create the new model from
- `files`: (optional) a dictionary of file names to SHA256 digests of blobs to create the model from
- `adapters`: (optional) a dictionary of file names to SHA256 digests of blobs for LORA adapters
- `template`, `license`, `system`, `parameters`, `messages`, `stream`, `quantize`: (optional)

### Examples

#### Create a new model

```shell
curl http://localhost:11434/api/create -d '{
  "model": "mario",
  "from": "llama3.2",
  "system": "You are Mario from Super Mario Bros."
}'
```

Response: a stream of JSON objects with `status` (e.g. "reading model metadata", "creating system layer", "success").

#### Quantize a model

```shell
curl http://localhost:11434/api/create -d '{
  "model": "llama3.2:quantized",
  "from": "llama3.2:3b-instruct-fp16",
  "quantize": "q4_K_M"
}'
```

## Check if a Blob Exists

```shell
HEAD /api/blobs/:digest
```

Ensures that the file blob used with create a model exists on the server.

### Examples

#### Request

```shell
curl -I http://localhost:11434/api/blobs/sha256:29fdb92e57cf0827ded04ae6461b5931d01fa595843f55d36f5b275a52087dd2
```

#### Response

Return 200 OK if the blob exists, 404 Not Found if it does not.

## Push a Blob

```
POST /api/blobs/:digest
```

Push a file to the Ollama server to create a "blob" (Binary Large Object).

### Query Parameters

- `digest`: the expected SHA256 digest of the file

### Examples

#### Request

```shell
curl -T model.gguf -X POST http://localhost:11434/api/blobs/sha256:29fdb92e57cf0827ded04ae6461b5931d01fa595843f55d36f5b275a52087dd2
```

#### Response

Return 201 Created if the blob was successfully created, 400 Bad Request if the digest used is not expected.

## List Local Models

```
GET /api/tags
```

List models that are available locally.

### Examples

#### Request

```shell
curl http://localhost:11434/api/tags
```

#### Response

```json
{
  "models": [
    {
      "name": "deepseek-r1:latest",
      "model": "deepseek-r1:latest",
      "modified_at": "2025-05-10T08:06:48.639712648-07:00",
      "size": 4683075271,
      "digest": "0a8c266910232fd3291e71e5ba1e058cc5af9d411192cf88b6d30e92b6e73163",
      "details": {
        "parent_model": "",
        "format": "gguf",
        "family": "qwen2",
        "families": ["qwen2"],
        "parameter_size": "7.6B",
        "quantization_level": "Q4_K_M"
      }
    }
  ]
}
```

## Show Model Information

```
POST /api/show
```

Show information about a model including details, modelfile, template, parameters, license, system prompt.

### Parameters

- `model`: name of the model to show
- `verbose`: (optional) if set to `true`, returns full data for verbose response fields

### Examples

#### Request

```shell
curl http://localhost:11434/api/show -d '{ "model": "llava" }'
```

#### Response

Returns `modelfile`, `parameters`, `template`, `details`, `model_info`, `capabilities`, etc.

## Copy a Model

```
POST /api/copy
```

Copy a model. Creates a model with another name from an existing model.

### Examples

#### Request

```shell
curl http://localhost:11434/api/copy -d '{
  "source": "llama3.2",
  "destination": "llama3-backup"
}'
```

#### Response

Returns 200 OK if successful, 404 Not Found if the source model doesn't exist.

## Delete a Model

```
DELETE /api/delete
```

Delete a model and its data.

### Parameters

- `model`: model name to delete

### Examples

#### Request

```shell
curl -X DELETE http://localhost:11434/api/delete -d '{ "model": "llama3:13b" }'
```

#### Response

Returns 200 OK if successful, 404 Not Found if the model to be deleted doesn't exist.

## Pull a Model

```
POST /api/pull
```

Download a model from the ollama library. Cancelled pulls are resumed from where they left off.

### Parameters

- `model`: name of the model to pull
- `insecure`: (optional) allow insecure connections to the library
- `stream`: (optional) if `false` the response will be returned as a single response object, rather than a stream of objects

### Examples

#### Request

```shell
curl http://localhost:11434/api/pull -d '{ "model": "llama3.2" }'
```

#### Response

If `stream` is not specified or set to `true`, a stream of JSON objects is returned (e.g. `{"status":"pulling manifest"}`, then download progress, then `{"status":"success"}`). If `stream` is `false`, a single JSON object: `{ "status": "success" }`.

## Push a Model

```
POST /api/push
```

Upload a model to a model library. Requires registering for ollama.ai and adding a public key first.

### Parameters

- `model`: name of the model to push in the form of `<namespace>/<model>:<tag>`
- `insecure`: (optional) allow insecure connections
- `stream`: (optional) if `false` the response will be returned as a single response object

### Examples

#### Request

```shell
curl http://localhost:11434/api/push -d '{ "model": "mattw/pygmalion:latest" }'
```

#### Response

Stream of JSON objects (e.g. "retrieving manifest", "starting upload", "success") or single object if `stream`: false.

## Generate Embeddings

```
POST /api/embed
```

Generate embeddings from a model.

### Parameters

- `model`: name of model to generate embeddings from
- `input`: text or list of text to generate embeddings for
- `truncate`, `options`, `keep_alive`, `dimensions`: (optional)

### Examples

#### Request

```shell
curl http://localhost:11434/api/embed -d '{
  "model": "all-minilm",
  "input": "Why is the sky blue?"
}'
```

#### Response

```json
{
  "model": "all-minilm",
  "embeddings": [[ 0.010071029, -0.0017594862, 0.05007221, ... ]],
  "total_duration": 14143917,
  "load_duration": 1019500,
  "prompt_eval_count": 8
}
```

## List Running Models

```
GET /api/ps
```

List models that are currently loaded into memory.

### Examples

#### Request

```shell
curl http://localhost:11434/api/ps
```

#### Response

```json
{
  "models": [
    {
      "name": "mistral:latest",
      "model": "mistral:latest",
      "size": 5137025024,
      "digest": "2ae6f6dd7a3dd734790bbbf58b8909a606e0e7e97e94b7604e0aa7ae4490e6d8",
      "details": { "parent_model": "", "format": "gguf", "family": "llama", "families": ["llama"], "parameter_size": "7.2B", "quantization_level": "Q4_0" },
      "expires_at": "2024-06-04T14:38:31.83753-07:00",
      "size_vram": 5137025024
    }
  ]
}
```

## Generate Embedding (legacy)

> Note: this endpoint has been superseded by `/api/embed`

```
POST /api/embeddings
```

Generate embeddings from a model. Parameters: `model`, `prompt`. Advanced: `options`, `keep_alive`.

### Examples

#### Request

```shell
curl http://localhost:11434/api/embeddings -d '{
  "model": "all-minilm",
  "prompt": "Here is an article about llamas..."
}'
```

#### Response

```json
{
  "embedding": [ 0.5670403838157654, 0.009260174818336964, ... ]
}
```

## Version

```
GET /api/version
```

Retrieve the Ollama version.

### Examples

#### Request

```shell
curl http://localhost:11434/api/version
```

#### Response

```json
{ "version": "0.5.1" }
```

## Experimental Features

### Image Generation (Experimental)

> [!WARNING]
> Image generation is experimental and may change in future versions.

Image generation is supported through the standard `/api/generate` endpoint when using image generation models. The API automatically detects when an image generation model is being used. Experimental parameters: `width`, `height`, `steps`.

#### Example

##### Request

```shell
curl http://localhost:11434/api/generate -d '{
  "model": "x/z-image-turbo",
  "prompt": "a sunset over mountains",
  "width": 1024,
  "height": 768
}'
```

##### Response (streaming)

Progress updates during generation:

```json
{
  "model": "x/z-image-turbo",
  "created_at": "2024-01-15T10:30:00.000000Z",
  "completed": 5,
  "total": 20,
  "done": false
}
```

##### Final Response

```json
{
  "model": "x/z-image-turbo",
  "created_at": "2024-01-15T10:30:15.000000Z",
  "image": "iVBORw0KGgoAAAANSUhEUg...",
  "done": true,
  "done_reason": "stop",
  "total_duration": 15000000000,
  "load_duration": 2000000000
}
```

---

**Source & updates:** Working reference from the official Ollama API. To get updates, use the canonical source: [github.com/ollama/ollama — docs/api.md](https://github.com/ollama/ollama/edit/main/docs/api.md). Official docs: [docs.ollama.com/api](https://docs.ollama.com/api). SDKs: [ollama-python](https://github.com/ollama/ollama-python), [ollama-js](https://github.com/ollama/ollama-js).
