# Prompt folder

This folder contains **prompts** used by mindX and related systems. Prompts are first-class artifacts: they define agent behavior, roadmaps, and structured directives that can be versioned, executed, and reasoned about.

## Reference: prompt.prompt (Professor Codephreak)

The **prompt.prompt** language and ecosystem are defined and maintained by **Professor Codephreak** in the open-source repository:

- **GitHub:** [Professor-Codephreak/prompt.prompt](https://github.com/Professor-Codephreak/prompt.prompt)

That repo describes prompt.prompt as a collection of `.prompt` files using **encapsulation as an object-oriented approach to prompt design**. Files in the prompt.prompt folder are intended to create in the host AI an intense drive to build the components they describe; combined, they form a foundation for AI with strong system-control directives and advanced reasoning. The project includes a **BDI (Belief–Desire–Intention) agent** (e.g. `agent.prompt`, `bdi_agent.prompt`, `rules.prompt`), which has been used in **augmentic** and **AgenticPlace** development of mindX. **Emergent** prompts (e.g. `emergent.roadmap`) are decisions that emerge from the smart agents themselves. The repo provides **ActivatePrompt.py** to convert `.prompt` files into `.txt` for consumption by AIs that do not yet read `.prompt` natively. For full structure, conventions, and tools (config, docs, guides, prompts, scripts, tools), see the repository.

## Prompt.prompt language

The **prompt.prompt** format is a language invented by **Professor Codephreak** for expressing prompts in a way that is:

- **Machine- and human-readable:** Structured so both AI and humans can parse and interpret.
- **Versionable:** Stored as files (e.g. `.prompt`) under this folder for version control and reuse.
- **Metadata-rich:** Supports version, description, author, tags, default models, and sections (e.g. identity, capabilities, roadmap stages).

A prompt may be written in a “dense” form (e.g. space-separated words, minimal punctuation) for compact transmission or storage, and expanded into full prose (as in `emergent.prompt`) for readability and editing. The canonical form in this repo is the expanded, markdown-friendly version.

**.prompt as a substrate layer:** `.prompt` files can themselves be **encapsulated by XML** (e.g. for transport, signing, or embedding in documents). In that form they function as a **substrate layer** between Web2 and Web3 and/or **offline** execution: the same prompt artifact can be carried over HTTP, stored on-chain or in decentralized storage, or used locally without a network, providing a portable, versionable unit of agent directive that bridges traditional and decentralized environments.

## Contents of this folder

| File | Purpose |
|------|--------|
| **prompt.md** | This file: explains the prompt folder and the prompt.prompt language. |
| **CLAIR.prompt** | Identity and operating principles for Clair (Agent of Clarity): strategic vision, leverage, moral inversion, architecture. |
| **codephreak/** | Upstream `.prompt` files; see *Files in codephreak/* below. |
| **emergent.prompt** | **Augmentic Agency – Evolutionary Roadmap (v2.0.0-rc2+).** Staged development path for the Agent Framework: foundational BDI (DesireSynthesizer, Deliberation, ResourceManagement), augmented reasoning and memory, autonomous operation and learning, advanced autonomy and blockchain exploration. Written in expanded prompt.prompt form; source derived from Professor Codephreak’s prompt language. |

### Files in `codephreak/` (from upstream)

These files are copied from the [prompt.prompt repository](https://github.com/Professor-Codephreak/prompt.prompt) for reference and integration. They define the prompt language rules, BDI model, and example agents.

| File | Purpose |
|------|--------|
| **rules.prompt** | Core language rules and design principles (syntax, typing, OOP, prompt features, documentation style); includes `LANGUAGE_RULES` and `RuleViewer`. |
| **prompt.prompt** | Meta spec generator: produces canonical specification from rules.prompt and bdi.prompt. |
| **bdi.prompt** | Core BDI classes: Belief, Desire, Intention, Goal, Reward (MASTERMIND context). |
| **bdi_agent.prompt** | Full BDI agent: perceive → deliberate → plan → execute with tools (WebSearch, NoteTaking). |
| **agent.prompt** | Research Assistant Agent: perceive–plan–act loop, web search and summarizer tools. |
| **README.prompt** | Upstream project overview: philosophy, features, file layout, examples, status, future directions. |

## Use in mindX

- **PromptTool** (`tools/prompt_tool.py`) treats prompts as infrastructure: versioned, stored in memory, and executable.
- Prompts in this folder can be loaded by agents (e.g. for identity, roadmaps, or directives) and referenced by ID or path.
- Roadmaps and directives (e.g. `emergent.prompt`) can drive staged development, BDI goals, and self-improvement plans.

## Adding a new prompt

1. Create a new `.prompt` file in this folder (e.g. `my-agent.prompt`).
2. Use clear structure: title, optional metadata (version, author, tags, default models), then sections (identity, capabilities, roadmap, etc.).
3. Prefer the expanded, readable form (full sentences, markdown-style headers) for maintainability.
4. Update this `prompt.md` with a short row in the table and a sentence describing the prompt’s role.

For a fuller review of the prompt.prompt language, file layout, and tooling (e.g. ActivatePrompt, BDI agent scripts), see the upstream repository: [Professor-Codephreak/prompt.prompt](https://github.com/Professor-Codephreak/prompt.prompt).
