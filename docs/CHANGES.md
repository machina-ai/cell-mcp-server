# `feat/cell` Branch: Key Feature Overview

This document outlines the critical features introduced in the `feat/cell` branch. It serves as a contextual reference for the unique capabilities of this branch compared to the base project.

## 1. Redis Integration for Conversation Persistence

### Overview

The `feat/cell` branch introduces robust conversation state management by integrating a Redis backend. Previously, conversation `continuation_id`s were stored in-memory, making them vulnerable to data loss in the event of a server restart, disconnection, or load balancing event.

### Key Enhancements

-   **State Persistence:** Conversation threads are now stored in a Redis database, ensuring that user sessions can be seamlessly resumed even after an interruption.
-   **Improved Reliability:** This change significantly improves the reliability of multi-turn conversations, protecting against data loss and providing a more stable user experience.
-   **Flexible Configuration:** The Redis connection is configured via environment variables (`REDIS_HOST`, `REDIS_PORT`, `REDIS_AUTH`), with a graceful fallback to the original in-memory storage if Redis is not available. This ensures that the application remains functional in different environments.

### Implementation Details

The `utils/storage_backend.py` module was introduced to abstract the storage layer. It dynamically selects the appropriate backend at runtime:
-   If `REDIS_HOST` is set, it connects to the specified Redis instance.
-   If `REDIS_HOST` is not set, it defaults to a thread-safe, in-memory store.

This design ensures backward compatibility and allows for flexible deployments, both with and without a Redis dependency.

## 2. `brainstorm` Tool (Formerly `chat`)

### Overview

To avoid a naming conflict with the `gemini-cli`, which also has a `chat` tool, the `chat` tool in this project has been renamed to `brainstorm`.

### Key Enhancements

-   **Conflict Resolution:** The name change prevents ambiguity and potential conflicts when using this server with `gemini-cli`.
-   **Clearer Intent:** The name `brainstorm` more accurately reflects the tool's purpose as a collaborative thinking partner for development discussions.

### Implementation Details

The renaming was applied across the codebase, including:
-   Tool registration in `server.py`.
-   The tool's class name and `get_name()` method in `tools/chat.py`.
-   All relevant documentation, tests, and configuration files.

## 3. Telemetry for LLM Calls (Langfuse Format)

### Overview

The `feat/cell` branch introduces a telemetry system to capture detailed information about Large Language Model (LLM) calls. This system is designed to be compatible with the Langfuse format, allowing for powerful observability and analytics.

### Key Enhancements

-   **Usage Insights:** The telemetry data provides valuable insights into model performance, token usage, and costs, which can be used to optimize the application.
-   **Standardized Format:** By adhering to the Langfuse format, the telemetry data can be easily ingested by a wide range of observability platforms.
-   **Improved Debugging:** Detailed logs of LLM interactions are invaluable for debugging and troubleshooting complex issues.

### Implementation Details

The telemetry system is integrated into the core model provider logic, capturing key metrics for each LLM call, such as:
-   Model name
-   Prompt and response content
-   Token counts
-   Latency

This data is then formatted and logged, ready for analysis.

## 5. Standardized Context Propagation (`_ctx`)

### Overview

To enable robust telemetry, session management, and security, a standardized mechanism for propagating context from the `mcp-proxy` to the `zen-mcp-server` has been implemented. This is achieved via a `_ctx` object injected into each tool call.

### Expected `_ctx` Structure

The `mcp-proxy` is responsible for injecting a `_ctx` object into the `arguments` of every tool call. This object must contain essential metadata for the request lifecycle.

**Key Fields:**
-   `user_id`: The unique identifier for the user making the request.
-   `session_id`: A unique identifier for the user's session.

**Example JSON Payload:**
The proxy should construct the `call_tool` request payload as follows:

```json
{
  "jsonrpc": "2.0",
  "method": "call_tool",
  "params": {
    "name": "name_of_the_tool",
    "arguments": {
      "_ctx": {
        "user_id": "user_id_value",
        "session_id": "session_id_value"
      },
      "other_tool_arguments": "..."
    }
  }
}
```

This structure ensures that critical session and authentication information is consistently available to all tools, enabling better logging, debugging, and secure integration with other services.
