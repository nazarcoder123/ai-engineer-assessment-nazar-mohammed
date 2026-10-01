## Project: AI Engineer Technical Assessment

This file defines the implementation guidance for building the technical-assessment project described in the provided assessment document.

The goal is to build a small, explainable, production-oriented FastAPI chatbot that can answer questions from:
1. A text dataset selected by the developer.
2. Superhero information retrieved from the Superhero API.
3. Both sources when a question requires information from both.

The application must expose a single public chatbot endpoint:

`POST /ask`

The solution should be approximately 80–90% production-ready, with validation, sensible error handling, and core tests. The architecture and implementation decisions must remain understandable and defensible during the interview.

---

## 1. Assessment Requirements

The implementation MUST satisfy the following requirements from the assessment:

- Build a FastAPI chatbot.
- Provide a single chatbot endpoint: `POST /ask`.
- Accept a natural-language question.
- Answer questions about a chosen text dataset.
- Answer questions about superheroes.
- Determine which source is relevant to the question:
  - text dataset,
  - Superhero API,
  - or both.
- Use the Superhero API endpoint:
  - `/api/{token}/search/{name}`
- Use a real hosted LLM endpoint.
- Do NOT use a local LLM.
- Every response must state where the information came from.
- Include validation and sensible error handling.
- Include tests covering the core logic.
- Keep the README short and focused on setup, execution, and a brief project description.
- The project must be runnable after cloning the public GitHub repository.

Source: provided AI Engineer Technical Assessment. fileciteturn0file0L2-L18

---

## 2. Engineering Principles

Prioritize:

1. Correctness
2. Simplicity
3. Explainability
4. Clear separation of responsibilities
5. Robust error handling
6. Testability
7. Minimal unnecessary dependencies
8. Easy local setup
9. Explicit source attribution

Do NOT build an unnecessarily complex multi-agent framework.

Avoid adding:
- LangChain unless it provides a clear benefit.
- Vector databases unless the selected dataset genuinely requires retrieval.
- Multiple LLM providers unless there is a concrete reason.
- Authentication unless required by the implementation.
- Background workers for synchronous chatbot behavior.
- Kubernetes, Docker Compose, Redis, Celery, or other infrastructure unless justified.

The reviewer should be able to understand the complete request flow quickly.

---

# 3. Recommended Architecture

Use a lightweight layered architecture.

```text
Client
  |
  v
POST /ask
  |
  v
Request Validation
  |
  v
Question Router
  |
  +-----------------------+
  |                       |
  v                       v
Text Dataset        Superhero API
Retriever           Client
  |                       |
  +-----------+-----------+
              |
              v
        Context Builder
              |
              v
        Hosted LLM
              |
              v
      Response Formatter
              |
              v
     Answer + Sources