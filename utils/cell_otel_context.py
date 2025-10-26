from typing import Any, Dict


def extract_ctx(envelope: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts the _ctx object from the request envelope.

    It prioritizes looking for _ctx within the 'arguments' dictionary of a tool
    call, as this is how the mcp-proxy will forward the context. It also
    maintains fallbacks for other potential locations.

    Args:
        envelope: The request envelope.

    Returns:
        The _ctx object or a default context.
    """
    ctx = None
    params = envelope.get("params")

    # Prioridad 1: Dentro de 'arguments' para las llamadas a herramientas (call_tool)
    if (isinstance(params, dict) and
            isinstance(params.get("arguments"), dict) and
            "_ctx" in params["arguments"]):
        ctx = params["arguments"].pop("_ctx")

    # Fallback 1: Directamente en 'params'
    elif isinstance(params, dict) and "_ctx" in params:
        ctx = params.pop("_ctx")

    # Fallback 2: En el nivel superior del envelope
    elif "_ctx" in envelope:
        ctx = envelope.pop("_ctx")

    return ctx or {"user_id": "anonymous", "session_id": "n/a"}
