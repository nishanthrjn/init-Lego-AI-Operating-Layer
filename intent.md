# Lego AI Operating Layer — Intent

**Document:** `intent.md`
**Project:** Lego AI Operating Layer
**Status:** Foundational
**Purpose:** Product Intent, Architectural Constitution, and Engineering North Star

---

## 1. Vision

Lego AI is a **technology-neutral, platform-agnostic, composable AI Operating Layer** for building intelligent applications, AI applications, agentic systems, multi-agent systems, autonomous workflows, copilots, enterprise AI systems, and future forms of intelligent software.

The fundamental objective is simple:

> **Build the common AI infrastructure once. Compose future intelligent applications from reusable capabilities.**

Lego AI MUST enable developers to create applications primarily by **selecting, configuring, and composing reusable modules**, rather than repeatedly implementing models, agents, workflows, memory, retrieval, tools, integrations, security, observability, evaluation, and infrastructure.

The desired long-term developer experience is:

```text
Idea
 │
 ▼
Select Blueprint
 │
 ▼
Select Capabilities
 │
 ├── Models
 ├── Agents
 ├── Workflows
 ├── Skills
 ├── Tools
 ├── Memory
 ├── Knowledge
 ├── Policies
 ├── Guardrails
 └── Integrations
 │
 ▼
Configure
 │
 ▼
Compose
 │
 ▼
Run
```

Lego AI is therefore not intended to be another AI application.

It is intended to become the **operating layer upon which AI applications are assembled**.

---

# 2. Core Intent

The platform MUST maximize:

* Reusability
* Composability
* Modularity
* Interoperability
* Portability
* Replaceability
* Extensibility
* Testability
* Security
* Observability
* Governability
* Developer productivity

Future applications SHOULD contain primarily:

```text
Domain Logic
+
Domain Configuration
+
Domain Agents
+
Domain Skills
+
Domain Tools
+
Domain Policies
```

while reusing the majority of infrastructure from Lego AI.

The target is:

```text
             FUTURE APPLICATION

          ┌───────────────────────┐
          │   Domain-specific     │
          │      10–20%           │
          ├───────────────────────┤
          │                       │
          │      Lego AI          │
          │      80–90%           │
          │                       │
          └───────────────────────┘
```

These percentages are an architectural aspiration rather than a contractual metric.

The objective is to continually increase the reusable portion of future intelligent applications.

---

# 3. Fundamental Principle

## Applications declare WHAT they need.

## Lego AI determines HOW those capabilities are provided.

An application SHOULD request:

```yaml
requires:
  model:
    capability:
      - reasoning
      - structured-output

  workflow:
    capability:
      - durable-execution
      - checkpointing

  memory:
    capability:
      - semantic-search

  tools:
    capability:
      - external-data-access
```

The application SHOULD NOT need to specify:

```yaml
openai: ...
langgraph: ...
redis: ...
postgres: ...
kafka: ...
kubernetes: ...
```

Those belong to implementation and deployment configuration.

This separation between **capability intent** and **technology realization** is foundational to Lego AI.

---

# 4. Architecture Principle #1 — Technology Neutrality

Lego AI MUST NOT depend conceptually on any specific:

* LLM vendor
* AI model
* Agent framework
* Workflow engine
* Vector database
* Database
* Programming language
* Cloud provider
* Container platform
* Messaging system
* Observability vendor
* API technology
* AI protocol
* Deployment platform

Technologies are implementations of Lego AI contracts.

They are not Lego AI itself.

Therefore:

```text
OpenAI           = Adapter
Anthropic        = Adapter
Gemini           = Adapter
Local Model      = Adapter

LangGraph        = Adapter
Semantic Kernel  = Adapter
ADK              = Adapter

PostgreSQL       = Adapter
Redis            = Adapter
Qdrant           = Adapter

Kafka            = Adapter
NATS             = Adapter

MCP              = Protocol Adapter
A2A              = Protocol Adapter

OpenTelemetry    = Observability Adapter

Kubernetes       = Deployment Option
AWS              = Deployment Option
Azure            = Deployment Option
GCP              = Deployment Option
```

If replacing one of these technologies requires redesigning Lego AI's core domain model, the architecture is incorrectly coupled.

---

# 5. Architecture Principle #2 — Contract First

Lego AI MUST be designed **contract-first**.

The canonical architecture is defined by technology-neutral concepts such as:

```text
Capability
Application
Agent
Model
Task
Message
Context
Tool
Skill
Workflow
Memory
Knowledge
Retriever
Artifact
Event
Policy
Guardrail
Evaluator
Checkpoint
HumanApproval
Identity
Secret
Trace
Plugin
Adapter
```

These concepts MUST have stable, implementation-independent contracts.

Technology-specific SDKs implement those contracts.

Conceptually:

```text
                  LEGO AI SPECIFICATION
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
          Python SDK    Java SDK     .NET SDK
              │            │            │
              ▼            ▼            ▼
          Adapters      Adapters      Adapters
```

The specification MUST remain independent from any SDK implementation.

---

# 6. Architecture Principle #3 — Ports and Adapters

Every infrastructure dependency MUST sit behind an explicit port wherever practical.

Examples include:

```text
ModelPort
AgentRuntimePort
WorkflowPort
ToolPort
MemoryPort
KnowledgePort
RetrieverPort
EventPort
PolicyPort
IdentityPort
SecretPort
ObservabilityPort
EvaluationPort
ArtifactPort
SandboxPort
HumanApprovalPort
```

Implementations connect through adapters.

Example:

```text
                    ModelPort
                       │
          ┌────────────┼────────────┐
          │            │            │
          ▼            ▼            ▼
       OpenAI       Anthropic     Local Model
       Adapter       Adapter        Adapter
```

Core domain logic MUST depend on ports.

Ports MUST NOT depend on concrete adapters.

---

# 7. Architecture Principle #4 — Everything Is a Capability

Lego AI SHOULD model reusable functionality as capabilities.

Examples:

```text
model.reasoning
model.vision
model.embedding
model.structured-output

agent.execution
agent.delegation
agent.planning

workflow.graph
workflow.durable
workflow.parallel
workflow.checkpoint

memory.session
memory.semantic
memory.episodic

retrieval.vector
retrieval.keyword
retrieval.graph
retrieval.hybrid

tool.execution
tool.discovery

human.approval

security.policy
security.authorization

evaluation.correctness
evaluation.safety

observability.tracing
```

Applications request capabilities.

The platform resolves providers capable of satisfying those requirements.

---

# 8. Architecture Principle #5 — Plugin-First Extensibility

Every major subsystem SHOULD support extension through a common Plugin SPI.

A plugin MUST describe:

```text
Identity
Version
Plugin Type
Capabilities Provided
Dependencies
Configuration Schema
Compatibility
Lifecycle
Health
Permissions
Metadata
```

Example conceptual manifest:

```yaml
plugin:
  id: example-agent-runtime
  type: agent-runtime
  version: 1.0.0

  provides:
    - agent.execution
    - workflow.graph
    - workflow.checkpoint

  requires:
    lego-spec: ">=1.0"

  lifecycle:
    - initialize
    - start
    - health
    - stop
```

The platform SHOULD discover and load compatible plugins without requiring modifications to the core.

---

# 9. Architecture Principle #6 — Modules Must Be Independently Reusable

Major capabilities MUST be logically decoupled.

An application MUST NOT be required to use agents simply because it wants retrieval.

For example:

```text
Application ─────► Retrieval
```

MUST be valid.

Likewise:

```text
Application ─────► Model
Application ─────► Workflow
Application ─────► Memory
Application ─────► Tool
Application ─────► Policy
Application ─────► Evaluation
```

must be valid independently where semantically appropriate.

The architecture MUST NOT assume:

```text
Application
    ↓
Agent
    ↓
Everything Else
```

Agents are one capability among many.

---

# 10. Architecture Principle #7 — AI Is Optional

Lego AI MUST NOT require an LLM for every execution path.

The platform MUST permit deterministic and probabilistic components to coexist.

```text
                     TASK
                       │
                       ▼
                    ROUTER
           ┌───────────┼───────────┐
           ▼           ▼           ▼
       Rule Engine     LLM      ML Model
           │           │           │
           └───────────┼───────────┘
                       ▼
                    Workflow
                       │
              ┌────────┼────────┐
              ▼        ▼        ▼
             Tool     Agent    Human
```

The preferred execution hierarchy is:

```text
Deterministic Code
        ↓
Deterministic Workflow
        ↓
Model
        ↓
Agent
        ↓
Multi-Agent System
```

Higher autonomy SHOULD only be introduced when lower-complexity approaches cannot adequately solve the problem.

---

# 11. Architecture Principle #8 — Agents Are Untrusted Decision Makers

Agents MUST operate within trusted execution boundaries.

An agent MUST NOT automatically receive unrestricted:

* Database access
* Filesystem access
* Network access
* Production credentials
* Administrative permissions
* Arbitrary code execution
* Infrastructure access
* Financial transaction authority
* Sensitive data access

The execution model SHOULD resemble:

```text
Agent
  │
  ▼
Intent / Tool Request
  │
  ▼
Policy Engine
  │
  ├── Identity
  ├── Authorization
  ├── Input Validation
  ├── Data Classification
  ├── Risk Classification
  ├── Budget
  ├── Rate Limit
  └── Approval Requirement
  │
  ▼
Optional Human Approval
  │
  ▼
Controlled Execution
  │
  ▼
Audit
```

Autonomy MUST be bounded by policy.

---

# 12. Architecture Principle #9 — Interoperability by Design

Lego AI MUST communicate through open, explicit contracts.

It SHOULD support appropriate interoperability mechanisms including:

```text
REST
OpenAPI
gRPC
Protocol Buffers
Events
Webhooks
MCP
A2A
```

No single interoperability protocol MUST become mandatory for all use cases.

Protocol selection MUST follow the interaction semantics.

Conceptually:

```text
Application ↔ Platform       API / SDK
System      ↔ System         API / Events
Agent       ↔ Tool/Data      Tool Port / MCP
Agent       ↔ Agent          Agent Port / A2A
Service     ↔ Service        REST / gRPC / Events
```

---

# 13. Architecture Principle #10 — Configuration Over Coding

Repeated architectural behavior SHOULD become configuration.

Future applications SHOULD increasingly be definable declaratively.

Example:

```yaml
application:
  name: investment-research

requires:

  agents:
    - researcher
    - analyst
    - reviewer

  skills:
    - web-research
    - financial-analysis
    - report-writing

  tools:
    - market-data
    - filings

  memory:
    semantic: true

  workflow:
    durable: true

  security:
    profile: enterprise

  evaluation:
    profile: production

  observability:
    enabled: true
```

The platform converts this intent into an executable runtime topology.

---

# 14. Architecture Principle #11 — Composable Blueprints

Lego AI SHOULD provide reusable application blueprints.

Examples:

```text
chatbot
rag-application
copilot
single-agent
multi-agent
research-agent
coding-agent
document-ai
data-agent
automation-agent
decision-support
event-driven-agent
human-in-the-loop-workflow
```

Blueprints MUST themselves be compositions of Lego capabilities.

Blueprints MUST NOT introduce privileged architectural mechanisms unavailable to normal applications.

---

# 15. Architecture Principle #12 — Reuse at Multiple Boundaries

A Lego capability SHOULD be consumable through one or more appropriate mechanisms.

### Embedded

```text
Application
    │
    ▼
Lego SDK
```

### Plugin

```text
Application
    │
    ▼
Lego Runtime
    │
    ▼
Plugin
```

### Service

```text
Application
    │
    ▼
REST / gRPC / Events
    │
    ▼
Lego Service
```

### AI-native interoperability

```text
Agent
   │
   ├── MCP ──► Capability
   │
   └── A2A ──► Agent
```

Deployment topology MUST NOT unnecessarily leak into domain semantics.

---

# 16. Architecture Principle #13 — Modular Monolith First

Logical modularity MUST NOT imply premature distributed architecture.

The initial reference implementation SHOULD prefer:

```text
Modular Monolith
+
Plugin Architecture
+
Ports & Adapters
+
Dependency Injection
+
Explicit Contracts
```

Modules MAY later become independently deployed services when justified by:

* Independent scaling
* Security isolation
* Team ownership
* Availability requirements
* Deployment independence
* Regulatory requirements
* Performance characteristics

The evolutionary path SHOULD be:

```text
Module
  ↓
Package
  ↓
Plugin
  ↓
Service
```

Distribution is a deployment decision, not a prerequisite for modularity.

---

# 17. Architecture Principle #14 — Explicit State

Agentic and workflow systems MUST NOT rely exclusively on implicit conversational state.

Execution state SHOULD be explicitly represented.

Examples:

```text
Task State
Workflow State
Agent State
Conversation State
Checkpoint State
Approval State
Artifact State
Execution State
```

State SHOULD be:

* Serializable
* Inspectable
* Versionable
* Recoverable where required
* Auditable where required

Durable workflows SHOULD support interruption and resumption.

---

# 18. Architecture Principle #15 — Memory Is Not a Vector Database

Lego AI MUST distinguish different forms of memory.

```text
Working Memory
Session Memory
Semantic Memory
Episodic Memory
Procedural Memory
Organizational Knowledge
```

Each memory type MUST be represented through appropriate contracts.

No particular storage technology MUST define the semantic meaning of memory.

Therefore:

```text
Memory ≠ Vector Database
Knowledge ≠ RAG
RAG ≠ Agent
```

These are separate concepts that MAY be composed.

---

# 19. Architecture Principle #16 — Skills Are First-Class Assets

Reusable domain intelligence SHOULD be packaged as Skills.

A Skill MAY contain:

```text
Instructions
Prompts
Examples
Schemas
Tools
Scripts
Resources
Evaluation Cases
Policies
Metadata
```

Skills SHOULD be:

* Discoverable
* Versioned
* Testable
* Composable
* Portable
* Independently releasable where appropriate

Agents SHOULD acquire domain behavior through reusable skills rather than accumulating monolithic prompts.

---

# 20. Architecture Principle #17 — Observability Is Built In

Observability MUST NOT be an application-by-application afterthought.

Lego AI SHOULD provide consistent tracing across:

```text
Application
   ↓
Workflow
   ↓
Agent
   ↓
Model
   ↓
Tool
   ↓
Memory / Retrieval
   ↓
External System
```

Where appropriate, telemetry SHOULD capture:

```text
trace_id
request_id
application_id
workflow_id
task_id
agent_id
tool_id
model/provider metadata
latency
token usage
cost
state transitions
tool invocations
policy decisions
approvals
errors
evaluation scores
```

Sensitive information MUST be handled according to policy and MUST NOT be indiscriminately recorded.

Private model reasoning MUST NOT be treated as required telemetry.

---

# 21. Architecture Principle #18 — Evaluation Is a Runtime Primitive

Testing AI systems requires more than traditional unit tests.

Lego AI MUST treat evaluation as a first-class capability.

The evaluation architecture SHOULD support:

```text
Unit Tests
Contract Tests
Integration Tests
Workflow Tests
Agent Tests
Tool Tests
Retrieval Tests
Prompt Tests
Regression Evals
Model Evals
Safety Evals
Adversarial Tests
Performance Tests
Cost Tests
Production Evals
```

Model, prompt, skill, tool, workflow, policy, and agent changes SHOULD be independently evaluable.

---

# 22. Architecture Principle #19 — Security Is Structural

Security MUST be implemented as a cross-cutting platform capability.

The architecture SHOULD support:

```text
Authentication
Authorization
RBAC
ABAC
Policy Enforcement
Secrets Management
Data Classification
Tenant Isolation
Sandboxing
Tool Authorization
Prompt-Injection Defense
Input/Output Validation
Audit
Supply-Chain Security
Human Approval
Rate Limits
Resource Budgets
```

Security controls SHOULD be enforced outside the probabilistic decision boundary wherever possible.

---

# 23. Architecture Principle #20 — Human-in-the-Loop Is Native

Human participation MUST NOT be treated as an exceptional failure path.

Humans MAY participate as first-class workflow actors.

```text
Agent
   │
   ▼
Decision
   │
   ▼
Approval Required?
   │
   ├── NO ─────► Continue
   │
   └── YES
          │
          ▼
        Human
          │
       ┌──┴──┐
       ▼     ▼
    Approve Reject
```

Policies SHOULD determine when human involvement is required.

---

# 24. Architecture Principle #21 — Event Native

Lego AI SHOULD support both synchronous and asynchronous execution.

The platform SHOULD be capable of reacting to:

```text
API Requests
User Messages
Events
Schedules
Webhooks
Data Changes
External Agent Requests
Workflow Transitions
Human Approvals
System Signals
```

Agents SHOULD NOT require a chat interface.

An intelligent application may be entirely event-driven.

---

# 25. Architecture Principle #22 — Cloud and Deployment Neutrality

Lego AI MUST be capable of being implemented for environments including:

```text
Developer Laptop
Container
Virtual Machine
Kubernetes
AWS
Azure
GCP
Private Cloud
On-Premises
Hybrid
Edge
```

The canonical Lego AI specification MUST NOT assume Kubernetes or any particular cloud provider.

Deployment adapters and reference architectures MAY optimize for specific environments.

---

# 26. Architecture Principle #23 — Language Neutrality

The Lego AI specification MUST NOT be defined exclusively through Python, Java, TypeScript, .NET, Go, or any other programming language.

Canonical contracts SHOULD use language-neutral representations where appropriate:

```text
JSON Schema
OpenAPI
Protocol Buffers
AsyncAPI / Event Schemas
Portable manifests
Protocol specifications
```

Language SDKs MAY provide idiomatic abstractions.

For example:

```text
lego-ai-spec
     │
     ├── Python SDK
     ├── Java SDK
     ├── TypeScript SDK
     ├── .NET SDK
     ├── Go SDK
     └── Future SDKs
```

---

# 27. Architecture Principle #24 — Replaceability Test

Every major architectural decision SHOULD be subjected to the following question:

> **Can this implementation be replaced without changing application domain logic or Lego AI's canonical contracts?**

For example:

```text
OpenAI       → another provider
LangGraph    → another runtime
PostgreSQL   → another database
Redis        → another cache
Kafka        → another event system
Kubernetes   → another runtime
MCP          → another tool protocol
A2A          → another agent protocol
```

If the answer is **no**, the architecture SHOULD be reviewed for accidental coupling.

---

# 28. Architecture Principle #25 — Escape Hatches

Abstraction MUST NOT become imprisonment.

Lego AI SHOULD provide sensible defaults and portable abstractions while permitting applications to access implementation-specific capabilities deliberately.

The preferred model is:

```text
Portable Core
     │
     ├── Standard Capability
     │
     └── Provider Extension
```

Provider-specific extensions MUST be explicit.

Applications using them accept reduced portability knowingly.

The platform MUST NOT reduce every provider to the lowest common denominator merely to preserve abstraction purity.

---

# 29. Lego AI Layer Model

The conceptual architecture is:

```text
┌────────────────────────────────────────────────────────────┐
│                    APPLICATIONS                            │
│ Web │ Mobile │ Enterprise │ API │ Agent │ Automation      │
└───────────────────────────┬────────────────────────────────┘
                            │
════════════════════════════▼════════════════════════════════
                 LEGO AI PUBLIC CONTRACT
════════════════════════════┬════════════════════════════════
                            │
                 ┌──────────▼──────────┐
                 │    LEGO AI CORE     │
                 │                     │
                 │ Capability Model    │
                 │ Contracts           │
                 │ Context             │
                 │ Lifecycle           │
                 │ Registry            │
                 │ Events              │
                 │ Configuration       │
                 └──────────┬──────────┘
                            │
════════════════════════════▼════════════════════════════════
                       PORT LAYER
════════════════════════════┬════════════════════════════════
                            │
       ┌──────────┬─────────┼─────────┬──────────┐
       ▼          ▼         ▼         ▼          ▼
     Model      Agent    Workflow   Memory      Tool
      Port       Port      Port      Port        Port

       ▼          ▼         ▼         ▼          ▼
    Knowledge   Skill     Policy    Event    Observability
      Port       Port      Port      Port        Port

════════════════════════════┬════════════════════════════════
                      ADAPTER / PLUGIN LAYER
════════════════════════════┬════════════════════════════════
                            │
            Concrete technologies live here.
                            │
════════════════════════════▼════════════════════════════════
                   INFRASTRUCTURE / PROVIDERS
═════════════════════════════════════════════════════════════
```

Dependency direction MUST point toward stable abstractions.

---

# 30. Lego AI Is NOT

Lego AI is NOT:

```text
A LangGraph wrapper
An OpenAI wrapper
A chatbot framework
A RAG framework
A prompt library
An MCP server
An A2A implementation
A vector database abstraction
A Kubernetes platform
A Python-only library
A collection of microservices
A low-code UI
```

It MAY provide all of these capabilities through modules or adapters.

But none defines the identity of Lego AI.

---

# 31. Lego AI IS

Lego AI is:

> **A technology-neutral capability composition and execution layer for intelligent applications.**

It provides standardized abstractions for:

```text
Intelligence
Agents
Models
Workflows
Tools
Skills
Memory
Knowledge
Context
Events
Policies
Security
Evaluation
Observability
Human Interaction
Interoperability
Execution
```

and allows implementations to be selected independently.

---

# 32. Developer Experience Goal

The long-term application authoring experience SHOULD approach:

```yaml
apiVersion: lego.ai/v1
kind: Application

metadata:
  name: financial-research

spec:

  capabilities:

    reasoning:
      required: true

    semantic-memory:
      required: true

    durable-workflow:
      required: true

  agents:
    - researcher
    - analyst
    - reviewer

  skills:
    - research
    - financial-analysis
    - report-writing

  tools:
    - market-data
    - filings

  security:
    profile: enterprise

  evaluation:
    profile: production

  observability:
    enabled: true
```

Then:

```text
                Application Intent
                        │
                        ▼
                Capability Resolver
                        │
                        ▼
                  Plugin Registry
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
       Models        Runtime       Storage
          │             │             │
          └─────────────┼─────────────┘
                        ▼
                  Execution Plan
                        │
                        ▼
                       RUN
```

The developer specifies intent.

Lego AI assembles the runtime.

---

# 33. AI-Native SDLC Intent

Lego AI itself MUST be developed using an AI-native software development lifecycle.

```text
Intent
   ↓
Specification
   ↓
Architecture
   ↓
Contracts
   ↓
Implementation
   ↓
Tests
   ↓
AI Evaluations
   ↓
Security / Red Teaming
   ↓
Deployment
   ↓
Runtime Evaluation
   ↓
Observability
   ↓
Feedback
   └────────────────► Intent
```

AI SHOULD assist with:

```text
Requirements refinement
Architecture analysis
ADR generation
Implementation
Code review
Test generation
Evaluation generation
Threat modeling
Documentation
Migration analysis
Dependency analysis
Operational diagnosis
```

Human engineers remain responsible for architectural intent, risk decisions, governance, and acceptance.

---

# 34. Specification Hierarchy

Project decisions SHOULD flow downward from stable intent toward replaceable implementation.

```text
intent.md
    │
    ▼
principles/
    │
    ▼
spec/
    │
    ▼
architecture/
    │
    ▼
contracts/
    │
    ▼
modules/
    │
    ▼
adapters/
    │
    ▼
deployments/
```

The rule is:

> **Lower layers MUST NOT silently redefine higher-layer intent.**

When an implementation conflicts with this document, either:

1. the implementation is wrong, or
2. this intent must be deliberately revised through an architectural decision.

Technology convenience alone is insufficient justification for violating a foundational principle.

---

# 35. Decision Priority

When architectural goals conflict, use the following priority:

```text
1. Security & Correctness
2. Contract Stability
3. Technology Independence
4. Modularity
5. Interoperability
6. Replaceability
7. Testability
8. Operability
9. Developer Experience
10. Performance
11. Implementation Convenience
```

This ordering is guidance rather than a substitute for engineering judgment.

Document significant trade-offs through Architecture Decision Records.

---

# 36. Success Criteria

Lego AI is succeeding when a new application can reuse existing capabilities without understanding their internal implementation.

A mature Lego AI application SHOULD be able to:

```text
Select
   ↓
Compose
   ↓
Configure
   ↓
Extend only domain-specific behavior
   ↓
Evaluate
   ↓
Deploy
```

rather than:

```text
Rebuild infrastructure
   ↓
Reimplement integrations
   ↓
Reimplement memory
   ↓
Reimplement agents
   ↓
Reimplement security
   ↓
Reimplement observability
   ↓
Reimplement evaluation
```

---

# 37. Ultimate North Star

The ultimate objective is:

> **Any intelligent application should be constructible by composing Lego AI capabilities while remaining independent of the technologies that implement those capabilities.**

A future application should be able to say:

```text
I need:

Reasoning
+
Retrieval
+
Memory
+
Three Agents
+
A Durable Workflow
+
Two Enterprise Tools
+
Human Approval
+
Security
+
Evaluation
+
Observability
```

and Lego AI should determine how those requirements are satisfied.

Technology changes.

Models change.

Agent frameworks change.

Protocols change.

Cloud platforms change.

Databases change.

Programming languages change.

**The application's intent should survive those changes.**

---

# 38. Architectural Litmus Test

Every major contribution to Lego AI MUST be evaluated against these questions:

1. Is it technology-neutral at the contract boundary?
2. Can the implementation be replaced?
3. Can the capability be used independently?
4. Can another application reuse it?
5. Can another programming language consume it?
6. Can another runtime implement it?
7. Does it expose capability rather than vendor terminology?
8. Is configuration separated from implementation?
9. Is state explicit where necessary?
10. Is security enforced outside probabilistic components where possible?
11. Is it observable?
12. Is it testable and evaluable?
13. Does it support versioning?
14. Does it introduce unnecessary coupling?
15. Does it reduce future application code?
16. Does it preserve an escape hatch for implementation-specific capabilities?

If several answers are **no**, the design SHOULD be reconsidered.

---

# 39. Final Principle

> **Lego AI owns the contracts. Plugins own the implementations. Applications own the intent.**

Or, expressed architecturally:

```text
APPLICATION
     │
     │ declares intent
     ▼
 LEGO AI
     │
     │ resolves capabilities
     ▼
  PLUGINS
     │
     │ implement capabilities
     ▼
TECHNOLOGY
```

This separation is the foundation of the Lego AI Operating Layer.

---

## End State

```text
                 ┌──────────────────────┐
                 │      YOUR IDEA       │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ APPLICATION INTENT   │
                 └──────────┬───────────┘
                            │
                            ▼
              ╔════════════════════════════╗
              ║   LEGO AI OPERATING LAYER ║
              ║                            ║
              ║  Compose • Resolve • Run  ║
              ╚═════════════╤══════════════╝
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
          Models          Agents         Tools
             │              │              │
          Memory         Workflows       Skills
             │              │              │
         Security         Evals       Observability
             │              │              │
             └──────────────┼──────────────┘
                            ▼
                  SWAPPABLE ADAPTERS
                            │
                            ▼
                    ANY TECHNOLOGY
```

**Build capabilities once. Compose applications repeatedly. Replace technologies freely. Preserve intent indefinitely.**
