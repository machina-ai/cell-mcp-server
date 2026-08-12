# Implementation Plan: Bound MCP Dependency Version (<2.0.0)

## Objective
Upper-bound the `mcp` library dependency to `<2.0.0` in project configuration files to prevent runtime crashes caused by breaking changes in `mcp 2.0.0` (such as the removal of `@server.list_tools()`).

---

## Key Files & Context

1. **`requirements.txt`**: Specifies production dependencies. Currently has `mcp>=1.0.0`.
2. **`pyproject.toml`**: Specifies project package metadata and build dependencies. Currently has `"mcp>=1.0.0",`.

---

## Implementation Steps

### Phase 1: Update Dependency Definitions
- Modify `requirements.txt`: Update line 1 from `mcp>=1.0.0` to `mcp>=1.0.0,<2.0.0`.
- Modify `pyproject.toml`: Update dependency entry from `"mcp>=1.0.0",` to `"mcp>=1.0.0,<2.0.0",`.

---

## Verification & Testing

1. **Verify Code Quality & Tests**:
   ```bash
   .zen_venv/bin/activate && ./code_quality_checks.sh
   ```
2. **Verify Quick Simulator Tests**:
   ```bash
   .zen_venv/bin/activate && python communication_simulator_test.py --quick
   ```
