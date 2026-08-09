# The Data and the Vector: What an Embedding Actually Is

In any system built on vector search — a retrieval-augmented pipeline, an associative memory, a semantic index — there are always two objects sitting side by side: the data, and the vector that stands in for it. They are constantly confused for one another. People say "the embedding *is* the document" or treat a vector database as though it stored meaning the way a filesystem stores bytes. It does not. The vector is something stranger and more specific: a learned, lossy, deterministic geometric proxy for the data. Understanding exactly what that proxy preserves, what it throws away, and how it relates back to the thing it represents is the difference between using vector search and trusting it blindly.

This article works through that relationship layer by layer, and ends at a place that matters for any system bridging machine learning and cryptographic verification: the vector is not the only way to bind data to a representation, and the alternative — a commitment — is its exact dual.

## A map, not a container

An embedding is the output of a learned function applied to a piece of data. Write it as `v = f(x)`. Here `x` is the thing itself — a sentence, a document, a memory record, an image — and `v` is a list of numbers, typically a few hundred to a few thousand of them, that locates `x` at a particular point in a high-dimensional space the model constructed during training.

The critical word is *located*. The vector does not contain the data. It does not hold a compressed copy of it the way a ZIP file holds a recoverable original. What it holds is a position, and that position is only meaningful in relation to the positions of everything else the same model would embed.

What makes the function `f` useful is the property it was trained to have: semantic relationships in the data become geometric relationships among the vectors. Two sentences that mean nearly the same thing land close together, separated by a small angle. Two unrelated documents land far apart, nearly orthogonal. The model has learned to arrange the entire universe of possible inputs so that *distance encodes dissimilarity of meaning*. This is why we can search by meaning at all: we convert the question of "what is similar in meaning?" into the question of "what is nearby in space?", and the second question is one a computer can answer quickly.

So the embedding is a structure-preserving map. It preserves the data's **relational** structure — its similarity ordering relative to everything else — while discarding the data's **substance** — the exact wording, the surface form, the byte-level identity. A paraphrase and its original collapse to almost the same point precisely because the map was built to ignore the things that make them different.

## Lossy and, in practice, irreversible

Because the map throws away substance, it is many-to-one. Countless different inputs can land at or near the same point, and the vector gives you no way to tell which one produced it. You generally cannot run the function backward and recover `x` from `v`. The embedding keeps a compressed, abstracted notion of what the data is *about* and discards nearly everything needed to reconstruct it verbatim.

This irreversibility is usually a feature — it is what lets the representation generalize — but it comes with a caveat that anyone handling sensitive data should internalize. "Irreversible in practice" is not the same as "secure." A line of research on embedding inversion, most prominently the vec2text work, has shown that a surprising amount of the original text can be reconstructed from its embedding alone, given access to the embedding model. A raw embedding of a private memory or a confidential record is therefore not a safe anonymization of that content. If the vector leaks, a meaningful fraction of the underlying data may leak with it. The map is lossy, but it is not a shredder.

## Deterministic, yet meaningless in isolation

The function `f` is deterministic. The same data passed through the same model yields the same vector, bit for bit, every time. This is what makes vector search reproducible and what makes caching embeddings sensible.

But determinism at the level of the whole vector does not translate into meaning at the level of any single number inside it. No individual dimension corresponds to a human-legible concept. There is no axis you can point to and say "this one measures formality" or "this one measures whether the text is about finance." Meaning is *distributed*: it lives in the pattern across all the dimensions at once, not in any one of them. Reading a single coordinate of an embedding tells you nothing, in the same way that reading a single neuron's activation tells you nothing about a thought.

The consequence is that a vector has meaning only relative to other vectors produced by the same model. The number `0.0431` in position 200 is not a fact about the data; it is a fact about where the data sits in one particular learned coordinate system. Change the coordinate system and the number is meaningless.

And the coordinate system changes far more easily than people expect. A different model produces an entirely different space. So does a different *version* of the same model. So does truncating the vector to a different length. In every one of these cases, every vector moves, and because search depends on relative distances, the entire geometry is silently redrawn. All distances change at once.

This is the root cause of several hard operational rules that otherwise look arbitrary:

- **You cannot mix two models' embeddings in one index.** Their vectors live in incompatible spaces; the distances between them are noise.
- **Re-embedding is a migration, not an edit.** Switching models or versions means recomputing every vector and rebuilding every index, because the old and new vectors cannot be compared.
- **Dimension truncation is a special, deliberate exception.** Matryoshka-trained embeddings are constructed so that the early dimensions carry most of the meaning, which means you *can* cut them shorter and keep the relational structure approximately intact. Truncating an ordinary embedding, or changing dimensions any other way, does not preserve that structure — it scrambles it.

The throughline is that the vector is not an absolute description of the data. It is a coordinate in a specific, fragile frame of reference.

## How the pair lives together in storage

Given all of this, the vector cannot replace the data. It is an address for the data, not a substitute for it. This shows up concretely in how a vector store like pgvector is actually used.

A typical row does not contain only an embedding. It contains the payload — the text, the JSON, the memory record, whatever the data actually is — *and* the embedding column beside it. The vector's job is to be a **content-addressable key**: you embed an incoming query with the same model, find the rows whose vectors are nearest to the query vector, and then return the *data* in those rows. The vector is how you find the data. The data is what you actually read and use. Retrieval is a two-step motion — geometry first to locate, then a lookup to resolve back to substance — and both halves are necessary.

For an associative memory system this *is* the entire mechanism rather than an implementation detail. A belief or a memory is the data. Its embedding is the memory's address in an associative space. Recall is the operation "find the memories whose addresses are geometrically near this cue," and every hit is then resolved back into the actual stored record. The system thinks in meaning-space and remembers in data-space, and the embedding is the bridge between them.

## The dual binding: embedding and commitment

There is a second way to bind a piece of data to a fixed-size representation, and setting it next to the embedding sharpens what each one really is.

A cryptographic commitment — a hash like keccak256, or a Merkle root over a set of items — also takes data and produces a short, fixed-size value. On the surface it looks like the same kind of object as an embedding: arbitrary input, compact output. But it is built for the opposite purpose, and the contrast is exact.

- An **embedding** `f(x)` binds data to a *region of meaning*. It is deliberately smooth and fuzzy: nearby inputs produce nearby outputs, paraphrases collide, small changes barely move the vector. It answers the question *"what is this like?"*
- A **commitment** `H(x)` binds data to an *exact identity*. It is deliberately brittle and collision-resistant: flip a single bit of the input and the output is completely, unrecognizably different, with no relationship to the original. It answers the question *"is this exactly the thing?"*

One preserves meaning and discards identity. The other preserves identity and discards meaning. They are two complementary projections of the same underlying data, each throwing away precisely what the other keeps. Neither can do the other's job — you cannot do similarity search over hashes, and you cannot prove exact integrity with embeddings.

This duality is what justifies architectures that maintain both. In a system that needs verifiable on-chain identity *and* off-chain semantic search, the natural division is to put the commitment where exact identity must be checked and tamper-evidence matters — on-chain, where it is a fixed 32 bytes regardless of how large or high-dimensional the underlying data is — and to put the embedding where similarity must be computed — off-chain, in the vector store. The commitment says *this is provably the exact record we anchored*; the embedding says *this record is about what you're looking for*. A system that needs both guarantees does not choose between them. It keeps the data once and projects it two ways.

## The whole relationship in one view

Pulling the layers together: a vector is a learned, lossy, deterministic, model-relative coordinate that encodes the data's relationships while discarding its content. It is not the data and cannot reconstruct the data; it is stored alongside the data as the data's semantic address, the key by which similarity search locates the real record. It is meaningful only within the specific space its model defines, which is why changing the model redraws everything at once. And it stands as the dual of a cryptographic commitment, which binds the same data to its exact identity while discarding the meaning the embedding preserves.

The practical upshot is a discipline about which object you are holding at any moment. When you want to know what something resembles, you reach for the vector. When you want to know whether something is exactly what it claims to be, you reach for the commitment. When you want the thing itself, you follow the vector back to the data it was only ever pointing at.
