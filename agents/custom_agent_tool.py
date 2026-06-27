import contextvars
from typing import Any
from google.adk.tools import AgentTool
from google.adk.events.event import Event, EventActions
from google.genai import types

# Context variables to propagate parent context and paths down async tasks
parent_ic_var = contextvars.ContextVar('parent_ic_var', default=None)
parent_path_var = contextvars.ContextVar('parent_path_var', default=None)

class HighlightAgentTool(AgentTool):
    async def run_async(
        self,
        *,
        args: dict[str, Any],
        tool_context: Any,
    ) -> Any:
        # Determine parent InvocationContext
        ic = parent_ic_var.get()
        if ic is None:
            ic = getattr(tool_context, "_invocation_context", None)
            if ic is not None:
                parent_ic_var.set(ic)

        # Determine parent node path
        parent_path = parent_path_var.get()
        if not parent_path:
            node = getattr(tool_context, "node", None)
            if node and getattr(node, "name", None):
                parent_path = f"{node.name}@1"
            else:
                parent_path = getattr(tool_context, "node_path", None) or "concierge@1"

        child_name = self.agent.name
        child_path = f"{parent_path}/{child_name}@1"

        # If this is a nested sub-agent (e.g. prediction calling prior), the native FunctionCall
        # event is trapped in the child's session_id and missed by the UI. Inject it into the parent queue.
        if ic and getattr(ic, "_event_queue", None) is not None and "/" in parent_path:
            parent_name = parent_path.split("/")[-1].split("@")[0]
            tool_event = Event(
                invocation_id=ic.invocation_id,
                author=parent_name,
                node_path=parent_path,
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_function_call(
                        name=child_name,
                        args=args
                    )]
                )
            )
            import asyncio
            asyncio.create_task(ic._enqueue_event(tool_event))

        # Set path for nested tool calls
        token = parent_path_var.set(child_path)

        try:
            return await super().run_async(args=args, tool_context=tool_context)
        finally:
            parent_path_var.reset(token)
