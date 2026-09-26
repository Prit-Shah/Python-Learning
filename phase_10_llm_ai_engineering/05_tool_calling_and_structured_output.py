r"""
05_tool_calling_and_structured_output.py

============================================================
1. CONCEPT
============================================================

Tool Calling (Function Calling) and Structured Output transform Large Language Models
from passive conversational interfaces into autonomous reasoning engines capable of
taking actions, interacting with APIs, querying databases, and emitting contract-guaranteed JSON:

1. The Tool Calling Execution Lifecycle:
   - Step 1 (Registration): Expose Python functions to the model as JSON Schema definitions.
   - Step 2 (Intent & Generation): User sends a prompt. The model analyzes the request, selects
     the appropriate tool, and generates structured JSON arguments with `role="assistant"` and
     `tool_calls=[{"id": "call_abc", "function": {"name": "...", "arguments": "{...}"}}]`.
   - Step 3 (Execution): The client application intercepts the tool call, validates the arguments
     against a Pydantic schema, and executes the actual Python function (e.g. database query, API ping).
   - Step 4 (Result Injection): The application returns the function output in a message with
     `role="tool"`, `name="fn_name"`, and `tool_call_id="call_abc"`.
   - Step 5 (Final Synthesis): The model receives the tool result and generates a final natural
     language response or initiates additional subsequent tool calls.

2. Constrained Structured Outputs & Grammar Masking:
   - Prompted JSON: Requesting JSON via prompt. Highly brittle; prone to conversational preamble
     or trailing markdown backticks (````json ... ````).
   - JSON Mode: Guarantees the output parses as valid JSON, but does NOT enforce a specific schema.
   - Strict Structured Outputs (`json_schema` with `strict: true`):
     * Compiles the JSON Schema into a Context-Free Grammar (CFG) or Finite State Machine (FSM).
     * At each token step, logits that would violate the schema are masked with $-\infty$,
       guaranteeing 100% adherence to the requested Pydantic schema.

3. Automated Schema Generation with Pydantic v2:
   - Avoid hand-writing brittle JSON schemas:
     ```python
     class SearchParams(BaseModel):
         query: str = Field(..., description="Keywords to search")
         limit: int = Field(default=5, ge=1, le=20)
     
     json_schema = SearchParams.model_json_schema()
     ```


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (Pydantic / Instructor)     | JavaScript / TypeScript (Zod)      |
+------------------------------+------------------------------------+------------------------------------+
| Schema Definition            | Pydantic v2 `BaseModel`            | `z.object({...})` (Zod)            |
| Schema Export                | `Model.model_json_schema()`        | `zod-to-json-schema` npm package   |
| Tool Router                  | Dict dispatch `REGISTRY[name](**)` | Object map / switch statement      |
| Structured Output Parser     | `Model.model_validate_json()`      | `schema.parse(JSON.parse(str))`    |
| Multi-Turn Tool Loop         | While loop appending messages      | Async while loop with message array|
| Self-Healing Retries         | Tenacity / Pydantic retry loop     | Manual try/catch with re-prompting |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Architecture Differences:
1. In TypeScript, Zod validates output after string generation. If the model hallucinated an extra
   field or malformed JSON, Zod throws a runtime exception that must be caught and re-prompted.
2. In Python, libraries like Outlines and Instructor integrate with grammar-constrained sampling
   at the inference engine level (vLLM / llama.cpp / OpenAI Structured Outputs), preventing invalid
   tokens from being generated in the first place.


============================================================
3. UNDER THE HOOD (Grammar-Constrained Decoding & Wire State)
============================================================

1. Finite State Machine (FSM) Logit Masking:
   - When a strict JSON schema is requested, the inference engine builds an FSM where states
     represent valid positions in the JSON syntax.
   - Before the softmax layer samples token $T_{i+1}$, the FSM identifies all tokens in the
     entire vocabulary that represent valid transitions (e.g. if inside a string literal, only
     valid characters or closing quote `"` are permitted; commas and brackets are barred).
   - Forbidden tokens are assigned a logit of $-\infty$, making their probability $0.0$.
   - This guarantees that parse errors, missing fields, or incorrect types are mathematically impossible!

2. Wire Protocol Message Pairing Rules:
   - Providers enforce strict validation rules on the message array:
     * If an assistant message contains `tool_calls`, the IMMEDIATELY following message(s)
       MUST have `role="tool"` and match every `tool_call_id` emitted.
     * Sending a user message before resolving pending tool calls triggers an immediate 400 Bad Request.


============================================================
4. COMMON GOTCHAS
============================================================

1. Insecure Execution (`eval()` or Shell Injection):
   - Passing model-generated strings directly into `eval()`, `exec()`, or raw SQL queries
     introduces critical Remote Code Execution (RCE) vulnerabilities.
   - FIX: Always validate arguments through strict Pydantic schemas and use parameterized DB queries.

2. Unhandled Validation Errors:
   - Assuming unconstrained LLM outputs will always parse cleanly.
   - FIX: Implement a self-healing retry handler: catch `ValidationError`, serialize the error
     message into a new user message, and ask the model to fix its JSON.

3. Mismatched `tool_call_id`:
   - Returning a tool response with an incorrect or missing `tool_call_id` crashes multi-turn
     conversations.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Explain how Tool Calling (Function Calling) works in modern LLMs from end to end."
A1: "Tool calling follows a five-step cyclical state machine:
     First, we declare functions using Pydantic models and export their JSON Schemas into the API request.
     Second, the LLM processes the user prompt and determines that an external action is needed. It stops
     generation and returns an assistant message containing `tool_calls` with a unique `id`, the function name,
     and arguments serialized as JSON.
     Third, our backend inspects the tool call, routes the function name through a secure registry, validates
     the arguments with Pydantic, and executes the native Python function.
     Fourth, we append the function result to the conversation history as a message with `role='tool'`
     and the matching `tool_call_id`.
     Fifth, we invoke the model again with the updated conversation history. The model consumes the tool
     output and synthesizes a final natural language answer for the user."

Q2: "What is the difference between JSON Mode and Strict Structured Outputs?"
A2: "JSON Mode guarantees that the model will emit syntactically valid JSON (valid curly braces, quotes,
     and keys), but it provides zero guarantees regarding schema compliance; the model can still omit
     mandatory fields, hallucinate extra keys, or use incorrect types (like a string instead of an integer).
     Strict Structured Outputs compiles a specific JSON Schema into a Context-Free Grammar or Finite State
     Machine directly at the decoding layer. At every token generation step, it masks the logits of any
     vocabulary tokens that would violate the schema with $-\infty$. This provides mathematical certainty
     that the generated output strictly conforms to our Pydantic model contracts without runtime schema errors."

Q3: "How do you implement self-healing error correction when an LLM fails structured validation?"
A3: "When using providers that do not support grammar masking, I implement a self-healing reflection loop.
     I attempt to parse the raw output using `Model.model_validate_json(raw_text)`. If a `ValidationError`
     is raised, I capture Pydantic's structured error list (`err.errors()`).
     I append the invalid response to the conversation history, followed by a new user message containing
     the exact validation error details: 'Your previous response failed validation on fields X and Y with error Z.
     Please output a corrected JSON object conforming strictly to the schema.'
     The LLM inspects its mistake, corrects the missing or mis-typed fields, and succeeds on the retry attempt."
"""

import sys
import json
import warnings
warnings.filterwarnings("ignore")
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, ValidationError

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# 1. TOOL SCHEMAS & REGISTRY
# ==============================================================================

class CurrencyConversionArgs(BaseModel):
    amount: float = Field(..., gt=0.0, description="Amount of money to convert")
    from_currency: str = Field(..., min_length=3, max_length=3, description="Source 3-letter currency code (e.g. USD)")
    to_currency: str = Field(..., min_length=3, max_length=3, description="Target 3-letter currency code (e.g. EUR)")


class DatabaseLookupArgs(BaseModel):
    user_id: int = Field(..., ge=1, description="Unique primary key of the customer")
    include_orders: bool = Field(default=False, description="Whether to include customer order history")


# Concrete tool execution implementations
def execute_currency_conversion(amount: float, from_currency: str, to_currency: str) -> Dict[str, Any]:
    rates = {
        ("USD", "EUR"): 0.92,
        ("EUR", "USD"): 1.09,
        ("USD", "GBP"): 0.79,
    }
    key = (from_currency.upper(), to_currency.upper())
    rate = rates.get(key, 1.0)
    converted = round(amount * rate, 2)
    return {
        "original_amount": amount,
        "from": from_currency.upper(),
        "to": to_currency.upper(),
        "rate": rate,
        "converted_amount": converted
    }


def execute_database_lookup(user_id: int, include_orders: bool = False) -> Dict[str, Any]:
    mock_db = {
        101: {"name": "Grace Hopper", "status": "ACTIVE", "tier": "ENTERPRISE"},
        102: {"name": "Alan Turing", "status": "ACTIVE", "tier": "PRO"}
    }
    user = mock_db.get(user_id)
    if not user:
        return {"error": f"User #{user_id} not found."}
    
    result = {"user_id": user_id, **user}
    if include_orders:
        result["orders"] = [f"ORD-{user_id}-1", f"ORD-{user_id}-2"]
    return result


class ToolRegistry:
    """Manages tool registration, JSON schema generation, and safe execution."""

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register_tool(self, name: str, description: str, schema_cls: type[BaseModel], fn: Callable):
        self._tools[name] = {
            "name": name,
            "description": description,
            "schema": schema_cls,
            "function": fn,
            "openai_spec": {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": schema_cls.model_json_schema()
                }
            }
        }

    def get_tool_specs(self) -> List[Dict[str, Any]]:
        return [tool["openai_spec"] for tool in self._tools.values()]

    def execute_call(self, name: str, raw_arguments_json: str) -> Dict[str, Any]:
        if name not in self._tools:
            return {"error": f"Unknown tool: '{name}'"}

        tool = self._tools[name]
        schema_cls = tool["schema"]
        fn = tool["function"]

        # Validate arguments through Pydantic
        try:
            validated_args = schema_cls.model_validate_json(raw_arguments_json)
        except ValidationError as e:
            return {"error": "Argument validation failed", "details": e.errors()}

        # Execute native function
        return fn(**validated_args.model_dump())


# ==============================================================================
# 2. MULTI-TURN TOOL AGENT ORCHESTRATOR
# ==============================================================================

class ToolCallingAgent:
    """Orchestrates multi-turn message loops between user, model, and tools."""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def process_turn(
        self,
        conversation_history: List[Dict[str, Any]],
        model_tool_call_response: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes a single cycle:
        1. Takes assistant tool call.
        2. Dispatches tool execution.
        3. Appends tool response message.
        """
        history = list(conversation_history)

        if not model_tool_call_response:
            return history

        # Append assistant's tool call message
        history.append(model_tool_call_response)

        # Process each tool call
        tool_calls = model_tool_call_response.get("tool_calls", [])
        for call in tool_calls:
            call_id = call["id"]
            fn_name = call["function"]["name"]
            fn_args = call["function"]["arguments"]

            # Execute tool safely
            output = self.registry.execute_call(fn_name, fn_args)

            # Append tool result message adhering strictly to wire protocol
            history.append({
                "role": "tool",
                "tool_call_id": call_id,
                "name": fn_name,
                "content": json.dumps(output)
            })

        return history


# ==============================================================================
# 3. SELF-HEALING STRUCTURED OUTPUT PARSER
# ==============================================================================

class UserExtractionSchema(BaseModel):
    full_name: str = Field(..., min_length=2)
    age: int = Field(..., ge=0, le=120)
    skills: List[str] = Field(..., min_length=1)


class SelfHealingParser:
    """Simulates reflection loop to heal malformed or schema-invalid LLM outputs."""

    @staticmethod
    def parse_with_repair(
        raw_json_str: str,
        repair_fn: Callable[[str, str], str]
    ) -> Tuple[bool, Optional[UserExtractionSchema], int]:
        attempts = 0
        current_input = raw_json_str

        while attempts < 2:
            attempts += 1
            try:
                parsed = UserExtractionSchema.model_validate_json(current_input)
                return True, parsed, attempts
            except ValidationError as err:
                error_summary = json.dumps(err.errors())
                # Invoke repair function passing the bad JSON and the error
                current_input = repair_fn(current_input, error_summary)

        return False, None, attempts


# ==============================================================================
# 4. SELF-TESTING SUITE
# ==============================================================================

def run_tests() -> None:
    print("\n[*] Starting automated test suite for 05_tool_calling_and_structured_output.py...")

    # ------------------------------------------------------------
    # Test 1: JSON Schema Auto-Generation via Pydantic
    # ------------------------------------------------------------
    print("  -> Testing Pydantic JSON Schema extraction for tool definitions...")
    registry = ToolRegistry()
    registry.register_tool(
        name="convert_currency",
        description="Converts money between world currencies",
        schema_cls=CurrencyConversionArgs,
        fn=execute_currency_conversion
    )
    registry.register_tool(
        name="lookup_user",
        description="Fetches user details from customer database",
        schema_cls=DatabaseLookupArgs,
        fn=execute_database_lookup
    )

    specs = registry.get_tool_specs()
    assert len(specs) == 2
    conv_spec = next(s for s in specs if s["function"]["name"] == "convert_currency")
    params = conv_spec["function"]["parameters"]
    assert params["type"] == "object"
    assert "amount" in params["properties"]
    assert "from_currency" in params["properties"]
    assert "to_currency" in params["properties"]

    # ------------------------------------------------------------
    # Test 2: Safe Tool Execution & Argument Validation
    # ------------------------------------------------------------
    print("  -> Testing safe tool execution and Pydantic argument validation...")
    valid_args = json.dumps({"amount": 100.0, "from_currency": "USD", "to_currency": "EUR"})
    res = registry.execute_call("convert_currency", valid_args)
    assert res["converted_amount"] == 92.0
    assert res["rate"] == 0.92

    # Invalid arguments (violates gt=0 constraint)
    invalid_args = json.dumps({"amount": -50.0, "from_currency": "USD", "to_currency": "EUR"})
    err_res = registry.execute_call("convert_currency", invalid_args)
    assert "error" in err_res
    assert err_res["error"] == "Argument validation failed"

    # Database lookup tool
    db_args = json.dumps({"user_id": 101, "include_orders": True})
    db_res = registry.execute_call("lookup_user", db_args)
    assert db_res["name"] == "Grace Hopper"
    assert len(db_res["orders"]) == 2

    # ------------------------------------------------------------
    # Test 3: Multi-Turn Tool Call State Machine
    # ------------------------------------------------------------
    print("  -> Testing multi-turn tool message sequence and wire state...")
    agent = ToolCallingAgent(registry)

    # Initial history with user query
    history = [{"role": "user", "content": "Convert 200 USD to EUR please."}]

    # Simulated LLM response requesting tool call
    simulated_model_tool_call = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "call_mock_999",
            "type": "function",
            "function": {
                "name": "convert_currency",
                "arguments": json.dumps({"amount": 200.0, "from_currency": "USD", "to_currency": "EUR"})
            }
        }]
    }

    updated_history = agent.process_turn(history, simulated_model_tool_call)
    assert len(updated_history) == 3

    # Check assistant message
    assert updated_history[1]["role"] == "assistant"
    assert updated_history[1]["tool_calls"][0]["id"] == "call_mock_999"

    # Check tool response message
    tool_msg = updated_history[2]
    assert tool_msg["role"] == "tool"
    assert tool_msg["tool_call_id"] == "call_mock_999"
    assert tool_msg["name"] == "convert_currency"
    tool_data = json.loads(tool_msg["content"])
    assert tool_data["converted_amount"] == 184.0

    # ------------------------------------------------------------
    # Test 4: Self-Healing Structured Output Repair
    # ------------------------------------------------------------
    print("  -> Testing self-healing reflection loop on schema validation error...")
    # Malformed initial response (age is negative, skills is empty)
    bad_initial_json = json.dumps({"full_name": "Ada Lovelace", "age": -1, "skills": []})

    def mock_repair_agent(bad_json: str, errors: str) -> str:
        # Repairs errors by setting valid age and skills
        data = json.loads(bad_json)
        data["age"] = 36
        data["skills"] = ["Algorithms", "Mathematics", "Analytical Engine"]
        return json.dumps(data)

    success, parsed_obj, attempts = SelfHealingParser.parse_with_repair(
        bad_initial_json, mock_repair_agent
    )
    assert success is True
    assert attempts == 2
    assert parsed_obj.full_name == "Ada Lovelace"
    assert parsed_obj.age == 36
    assert len(parsed_obj.skills) == 3

    print("[SUCCESS] All 4 Tool Calling & Structured Output tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 10 - 05: Tool Calling, Structured Outputs & JSON Schemas")
    print("=" * 70)
    run_tests()
    print("=" * 70)
