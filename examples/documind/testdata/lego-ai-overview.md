# LegoAI Operating Layer -- Overview

LegoAI is a governed runtime for composing AI capabilities. Every capability
invocation passes through a Catalog, a resolution step, an authorization
check, and a dispatch arbiter before any provider is ever called.

## Governed Capability Invocation

Before any capability runs, it is published to a Catalog, resolved against
a version requirement, and checked against current authorization. No
capability may bypass this governed path, including capabilities that call
an external Model provider such as Ollama.

## Document Capabilities

The Document Capability Pack provides parsing, chunking, embedding,
retrieval, reranking, ingestion, and answering as independent, reusable
capabilities. Retrieval in v0.1 uses a local SQLite-backed store combining
vector similarity and lexical scoring through Reciprocal Rank Fusion.

## Known Limitations

LegoAI v0.1 supports exactly one Model provider, Ollama, running locally.
It does not yet support untrusted Plugins, distributed execution, or a
persisted operation ledger that survives a process restart.
