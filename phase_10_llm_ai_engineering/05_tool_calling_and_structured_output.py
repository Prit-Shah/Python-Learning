"""
Phase 10: Tool Calling & Structured Output
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Concept: Tool calling (function calling) lets the LLM invoke external
     functions/APIs by generating structured JSON arguments. Structured output
     forces the LLM to respond in a specific JSON schema. Together, they turn
     LLMs from text generators into programmable decision engines.
   - JS/TS Equivalent: Same concept. OpenAI's function calling returns JSON
     that you parse and dispatch. In TS you'd define schemas with Zod; in
     Python you use Pydantic models for both tool argument schemas and
     response validation.
   - Key insight: The LLM doesn't execute tools — it generates a JSON payload
     specifying which tool to call and with what arguments. YOUR code executes
     the tool and feeds the result back to the LLM.

2. UNDER THE HOOD (CPython & Memory):
   - Tool definitions are sent as part of the API request (in the `tools`
     parameter). The LLM sees them as part of its context and generates a
     `tool_calls` response with function name + JSON arguments.
   - Pydantic model schemas are converted to JSON Schema format, which is
     what the API expects. `Model.model_json_schema()` generates this.
   - The execution loop: User msg -> LLM -> tool_call -> execute function ->
     tool result -> LLM -> final answer. This is the foundation of AI agents.

3. COMMON GOTCHA:
   - Not validating tool arguments: The LLM might generate invalid JSON or
     wrong argument types. ALWAYS validate with Pydantic before execution.
   - Infinite tool loops: Without a max-iterations guard, the LLM might keep
     calling tools forever. Always cap the loop (e.g., max 5 iterations).
   - Security: The LLM decides which tools to call. Never expose destructive
     operations (DELETE, DROP TABLE) without human approval.

4. INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   - Interview Question: "How does tool/function calling work with LLMs?"
   - How to Answer Out Loud (60-90 sec verbal script):
     * "Tool calling lets the LLM invoke external functions. I define tools
       as Pydantic models with name, description, and argument schema. These
       are sent to the API in the `tools` parameter."
     * "When the LLM determines it needs external data or actions, it returns
       a `tool_calls` response instead of text. Each tool call has a function
       name and JSON arguments. My code validates the arguments with Pydantic,
       executes the function, and sends the result back as a tool message."
     * "The LLM then generates a final natural language answer incorporating
       the tool results. This loop can be multi-step — the LLM might call
       multiple tools sequentially to build up context."
     * "In production, I add guardrails: input validation, max iteration
       limits, tool-level authorization, and logging of all tool executions
       for audit and debugging."
================================================================================
"""

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass

import json
from dataclasses import dataclass, field
from typing import Any, Callable
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════════════
# PYDANTIC-STYLE TOOL DEFINITIONS
# In production, you'd use actual Pydantic BaseModel for these.
# ══════════════════════════════════════════════════════════════════════

@dataclass
class ToolParameter:
    name: str
    type: str  # "string", "integer", "number", "boolean", "array"
    description: str
    required: bool = True
    enum: list[str] | None = None


@dataclass
class ToolDefinition:
    """
    Defines a tool the LLM can call.

    REAL CODE (OpenAI format):
        tools = [{
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather for a city",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "City name"},
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    },
                    "required": ["city"],
                },
            },
        }]
    """
    name: str
    description: str
    parameters: list[ToolParameter]
    handler: Callable[..., str] = field(repr=False, default=lambda **kw: "{}")

    def to_openai_schema(self) -> dict:
        """Convert to OpenAI function calling format."""
        properties = {}
        required = []
        for p in self.parameters:
            prop: dict[str, Any] = {"type": p.type, "description": p.description}
            if p.enum:
                prop["enum"] = p.enum
            properties[p.name] = prop
            if p.required:
                required.append(p.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


@dataclass
class ToolCall:
    """Represents the LLM's decision to call a tool."""
    id: str
    function_name: str
    arguments: dict[str, Any]


@dataclass
class ToolResult:
    """Result of executing a tool."""
    tool_call_id: str
    result: str  # Always stringified for the LLM


# ══════════════════════════════════════════════════════════════════════
# TOOL REGISTRY & EXECUTOR
# ══════════════════════════════════════════════════════════════════════

class ToolRegistry:
    """Registry of available tools. Maps tool names to definitions."""

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def get_schemas(self) -> list[dict]:
        """Get all tool schemas for the API request."""
        return [t.to_openai_schema() for t in self._tools.values()]

    def execute(self, tool_call: ToolCall) -> ToolResult:
        """
        Validate and execute a tool call.

        CRITICAL: Always validate arguments before execution.
        The LLM might generate invalid or malicious arguments.
        """
        tool = self._tools.get(tool_call.function_name)
        if not tool:
            return ToolResult(
                tool_call_id=tool_call.id,
                result=json.dumps({"error": f"Unknown tool: {tool_call.function_name}"}),
            )

        # Validate required parameters
        required_params = {p.name for p in tool.parameters if p.required}
        provided_params = set(tool_call.arguments.keys())
        missing = required_params - provided_params
        if missing:
            return ToolResult(
                tool_call_id=tool_call.id,
                result=json.dumps({"error": f"Missing required parameters: {missing}"}),
            )

        # Execute the handler
        try:
            result = tool.handler(**tool_call.arguments)
            return ToolResult(tool_call_id=tool_call.id, result=result)
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id,
                result=json.dumps({"error": f"Tool execution failed: {str(e)}"}),
            )

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())


# ══════════════════════════════════════════════════════════════════════
# MOCK TOOL-CALLING LLM
# ══════════════════════════════════════════════════════════════════════

class MockToolCallingLLM:
    """
    Simulates an LLM that can decide to call tools.

    In production, the LLM API returns either:
    1. A text response (finish_reason="stop")
    2. A tool_calls response (finish_reason="tool_calls")
    """

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def chat(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> dict:
        """
        Simulate a chat completion that might call tools.
        Returns a response dict with either 'content' or 'tool_calls'.
        """
        last_msg = messages[-1].get("content", "").lower()

        # Simulate tool calling decisions based on user intent
        if "weather" in last_msg and tools:
            # Extract city from message
            city = "London"  # Default
            for word in last_msg.split():
                if word[0].isupper() if word else False:
                    city = word
                    break

            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_001",
                        "function": {
                            "name": "get_weather",
                            "arguments": json.dumps({"city": city, "unit": "celsius"}),
                        },
                    }
                ],
            }

        elif "calculate" in last_msg and tools:
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_002",
                        "function": {
                            "name": "calculate",
                            "arguments": json.dumps({"expression": "2 + 2"}),
                        },
                    }
                ],
            }

        elif "search" in last_msg and tools:
            query = last_msg.replace("search for", "").replace("search", "").strip()
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_003",
                        "function": {
                            "name": "search_knowledge",
                            "arguments": json.dumps({"query": query or "Python"}),
                        },
                    }
                ],
            }

        else:
            # No tool needed — direct response
            return {
                "role": "assistant",
                "content": f"I'll answer directly: Your question about '{last_msg[:50]}' is interesting.",
                "tool_calls": None,
            }


# ══════════════════════════════════════════════════════════════════════
# TOOL-CALLING EXECUTION LOOP (Agent Pattern)
# ══════════════════════════════════════════════════════════════════════

def run_tool_calling_loop(
    llm: MockToolCallingLLM,
    registry: ToolRegistry,
    messages: list[dict],
    max_iterations: int = 5,
) -> str:
    """
    The core agent execution loop:
    1. Send messages to LLM (with tool definitions)
    2. If LLM returns tool_calls: execute tools, add results, loop
    3. If LLM returns text: return the final answer

    This is the foundation of AI agents (ReAct pattern).
    """
    tools = registry.get_schemas()

    for iteration in range(max_iterations):
        response = llm.chat(messages, tools=tools)

        if response.get("tool_calls"):
            # LLM wants to call tools
            messages.append(response)

            for tc in response["tool_calls"]:
                tool_call = ToolCall(
                    id=tc["id"],
                    function_name=tc["function"]["name"],
                    arguments=json.loads(tc["function"]["arguments"]),
                )

                print(f"    [Tool Call] {tool_call.function_name}({tool_call.arguments})")

                # Execute the tool
                result = registry.execute(tool_call)
                print(f"    [Tool Result] {result.result}")

                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": result.tool_call_id,
                    "content": result.result,
                })

            # After executing all tools, we need the LLM to process results.
            # In mock: generate a final answer incorporating tool results
            tool_results_text = " ".join(
                m["content"] for m in messages if m.get("role") == "tool"
            )
            return f"Based on the tool results: {tool_results_text}"

        else:
            # LLM returned a direct text response
            return response.get("content", "No response")

    return "Max iterations reached without a final answer."


# ── Demonstration Functions ──────────────────────────────────────────────

def demonstrate_tool_definitions():
    """Defining tools with schemas."""
    registry = ToolRegistry()

    # Define tools with handlers
    def get_weather(city: str, unit: str = "celsius") -> str:
        # Mock weather data
        data = {"city": city, "temp": 22, "unit": unit, "condition": "sunny"}
        return json.dumps(data)

    def calculate(expression: str) -> str:
        # Safe calculator (in production, use a sandboxed evaluator)
        allowed = set("0123456789+-*/.(). ")
        if all(c in allowed for c in expression):
            try:
                result = eval(expression)  # DON'T use eval in production!
                return json.dumps({"expression": expression, "result": result})
            except Exception:
                return json.dumps({"error": "Invalid expression"})
        return json.dumps({"error": "Expression contains disallowed characters"})

    def search_knowledge(query: str) -> str:
        # Mock knowledge base search
        results = [
            {"title": f"Result about {query}", "snippet": f"Relevant info about {query}..."}
        ]
        return json.dumps({"results": results, "count": len(results)})

    # Register tools
    weather_tool = ToolDefinition(
        name="get_weather",
        description="Get the current weather for a city",
        parameters=[
            ToolParameter("city", "string", "The city name"),
            ToolParameter("unit", "string", "Temperature unit", required=False, enum=["celsius", "fahrenheit"]),
        ],
        handler=get_weather,
    )

    calc_tool = ToolDefinition(
        name="calculate",
        description="Evaluate a mathematical expression",
        parameters=[
            ToolParameter("expression", "string", "Math expression to evaluate"),
        ],
        handler=calculate,
    )

    search_tool = ToolDefinition(
        name="search_knowledge",
        description="Search the knowledge base for information",
        parameters=[
            ToolParameter("query", "string", "Search query"),
        ],
        handler=search_knowledge,
    )

    for tool in [weather_tool, calc_tool, search_tool]:
        registry.register(tool)

    # Show schemas
    print("  Registered tools:")
    for schema in registry.get_schemas():
        func = schema["function"]
        params = list(func["parameters"]["properties"].keys())
        print(f"    - {func['name']}: {func['description']}")
        print(f"      Parameters: {params}")

    return registry


def demonstrate_tool_execution():
    """Tool calling execution loop."""
    registry = demonstrate_tool_definitions()
    llm = MockToolCallingLLM(registry)

    print("\n  === Tool Calling Loop ===")

    # Query that triggers tool use
    messages = [
        {"role": "system", "content": "You are a helpful assistant with access to tools."},
        {"role": "user", "content": "What's the weather in London?"},
    ]

    print(f"  User: {messages[-1]['content']}")
    result = run_tool_calling_loop(llm, registry, messages)
    print(f"  Final: {result}")

    return result


def demonstrate_structured_output():
    """Structured output — forcing LLM responses into schemas."""
    print("  === Structured Output Patterns ===")
    print()

    # Pattern 1: JSON mode with Pydantic validation
    print("  Pattern 1: Pydantic Response Validation")
    print("  -----------------------------------------")

    # In production with Pydantic:
    # class SentimentResult(BaseModel):
    #     text: str
    #     sentiment: Literal["positive", "negative", "neutral"]
    #     confidence: float = Field(ge=0, le=1)
    #     keywords: list[str]

    # Simulate LLM JSON response
    mock_llm_json = json.dumps({
        "text": "This product is amazing!",
        "sentiment": "positive",
        "confidence": 0.95,
        "keywords": ["amazing", "product"],
    })
    parsed = json.loads(mock_llm_json)
    print(f"    LLM JSON: {mock_llm_json}")
    print(f"    Parsed sentiment: {parsed['sentiment']}")
    print(f"    Confidence: {parsed['confidence']}")

    # Pattern 2: OpenAI response_format
    print("\n  Pattern 2: response_format (OpenAI API)")
    print("  ------------------------------------------")
    print("    client.chat.completions.create(")
    print("        model='gpt-4o',")
    print("        messages=[...],")
    print("        response_format={")
    print("            'type': 'json_schema',")
    print("            'json_schema': {")
    print("                'name': 'sentiment_analysis',")
    print("                'schema': SentimentResult.model_json_schema(),")
    print("            },")
    print("        },")
    print("    )")

    # Pattern 3: Validation with retry
    print("\n  Pattern 3: Validate + Retry on Parse Failure")
    print("  -----------------------------------------------")

    def parse_with_retry(llm_output: str, max_retries: int = 2) -> dict | None:
        for attempt in range(max_retries + 1):
            try:
                data = json.loads(llm_output)
                # Validate required fields
                assert "sentiment" in data, "Missing 'sentiment'"
                assert data["sentiment"] in ("positive", "negative", "neutral")
                assert "confidence" in data
                assert 0 <= data["confidence"] <= 1
                return data
            except (json.JSONDecodeError, AssertionError) as e:
                print(f"    Attempt {attempt + 1}: Validation failed - {e}")
                if attempt < max_retries:
                    llm_output = mock_llm_json  # Re-call LLM in production
        return None

    result = parse_with_retry(mock_llm_json)
    print(f"    Validated result: {result}")

    return parsed


def demonstrate_security():
    """AI security considerations."""
    print("  === AI Security Best Practices ===")
    print()
    print("  1. Prompt Injection Defense:")
    print("     - Use delimiters for user input: <user_input>...</user_input>")
    print("     - Validate LLM output before execution")
    print("     - Never put raw user input in system prompts")
    print()
    print("  2. Tool Calling Security:")
    print("     - Allowlist: Only expose safe, read-only tools by default")
    print("     - Authorization: Check permissions before tool execution")
    print("     - Sandboxing: Run tool code in restricted environments")
    print("     - Audit logging: Log every tool call with arguments")
    print()
    print("  3. Output Validation:")
    print("     - Schema validation: Force structured output with Pydantic")
    print("     - Content filtering: Check for PII, harmful content")
    print("     - Rate limiting: Cap tool calls per request")
    print()
    print("  4. Cost Control:")
    print("     - Max token limits per request")
    print("     - Budget alerts and hard caps")
    print("     - Cheaper models for simple tasks (routing)")


# ══════════════════════════════════════════════════════════════════════
# SELF-TEST CHALLENGES
# ══════════════════════════════════════════════════════════════════════

def run_tests():
    """Automated verification."""
    print("\n[*] Running automated self-tests...")

    # Test 1: Tool definition creates valid schema
    tool = ToolDefinition(
        name="test_tool",
        description="A test tool",
        parameters=[
            ToolParameter("arg1", "string", "First arg"),
            ToolParameter("arg2", "integer", "Second arg", required=False),
        ],
        handler=lambda arg1, arg2=0: json.dumps({"result": arg1}),
    )
    schema = tool.to_openai_schema()
    assert schema["type"] == "function", "Schema type should be 'function'"
    assert schema["function"]["name"] == "test_tool", "Name mismatch"
    assert "arg1" in schema["function"]["parameters"]["properties"], "arg1 missing"
    assert "arg1" in schema["function"]["parameters"]["required"], "arg1 should be required"
    assert "arg2" not in schema["function"]["parameters"]["required"], "arg2 should not be required"

    # Test 2: Tool registry
    registry = ToolRegistry()
    registry.register(tool)
    assert "test_tool" in registry.list_tools(), "Tool should be registered"
    assert registry.get("test_tool") is tool, "Should retrieve the tool"
    assert registry.get("nonexistent") is None, "Should return None for unknown"

    # Test 3: Tool execution
    tc = ToolCall(id="tc1", function_name="test_tool", arguments={"arg1": "hello"})
    result = registry.execute(tc)
    assert result.tool_call_id == "tc1", "Tool call ID should match"
    parsed = json.loads(result.result)
    assert parsed["result"] == "hello", "Tool should return correct result"

    # Test 4: Missing required parameter
    tc_bad = ToolCall(id="tc2", function_name="test_tool", arguments={})
    result_bad = registry.execute(tc_bad)
    parsed_bad = json.loads(result_bad.result)
    assert "error" in parsed_bad, "Should return error for missing params"

    # Test 5: Unknown tool
    tc_unknown = ToolCall(id="tc3", function_name="unknown", arguments={})
    result_unknown = registry.execute(tc_unknown)
    parsed_unknown = json.loads(result_unknown.result)
    assert "error" in parsed_unknown, "Should error on unknown tool"

    # Test 6: Schema generation with enum
    enum_tool = ToolDefinition(
        name="enum_tool",
        description="test",
        parameters=[
            ToolParameter("color", "string", "A color", enum=["red", "blue", "green"]),
        ],
    )
    enum_schema = enum_tool.to_openai_schema()
    assert "enum" in enum_schema["function"]["parameters"]["properties"]["color"],         "Enum should be in schema"
    assert enum_schema["function"]["parameters"]["properties"]["color"]["enum"] == ["red", "blue", "green"],         "Enum values should match"

    # Test 7: Structured output parsing
    valid_json = '{"sentiment": "positive", "confidence": 0.9}'
    parsed = json.loads(valid_json)
    assert parsed["sentiment"] == "positive", "Should parse sentiment"
    assert 0 <= parsed["confidence"] <= 1, "Confidence should be in range"

    # Test 8: Invalid JSON handling
    invalid_json = "not json at all"
    try:
        json.loads(invalid_json)
        assert False, "Should raise JSONDecodeError"
    except json.JSONDecodeError:
        pass  # Expected

    # Test 9: Tool schemas list
    registry2 = ToolRegistry()
    registry2.register(tool)
    registry2.register(enum_tool)
    schemas = registry2.get_schemas()
    assert len(schemas) == 2, "Should have 2 tool schemas"
    names = {s["function"]["name"] for s in schemas}
    assert names == {"test_tool", "enum_tool"}, "Schema names should match"

    # Test 10: Tool call loop simulation
    def mock_handler(**kwargs):
        return json.dumps({"status": "ok", "data": kwargs})

    simple_tool = ToolDefinition(
        name="simple",
        description="Simple tool",
        parameters=[ToolParameter("x", "string", "input")],
        handler=mock_handler,
    )
    reg = ToolRegistry()
    reg.register(simple_tool)
    tc = ToolCall(id="loop_test", function_name="simple", arguments={"x": "test"})
    result = reg.execute(tc)
    data = json.loads(result.result)
    assert data["status"] == "ok", "Tool should execute successfully"
    assert data["data"]["x"] == "test", "Arguments should pass through"

    print("[SUCCESS] All 10 Tool Calling self-tests passed!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 10: Tool Calling & Structured Output")
    print("=" * 70)
    print("\n--- Tool Definitions ---")
    demonstrate_tool_definitions()
    print("\n--- Tool Execution Loop ---")
    demonstrate_tool_execution()
    print("\n--- Structured Output ---")
    demonstrate_structured_output()
    print("\n--- AI Security ---")
    demonstrate_security()
    print("-" * 70)
    run_tests()
    print("=" * 70)
