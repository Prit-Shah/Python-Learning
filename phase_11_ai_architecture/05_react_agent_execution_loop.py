"""
Phase 11: ReAct Agent Architecture & Autonomous Tool Loops
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Concept: A ReAct (Reasoning + Acting) Agent interleaves thought generation
     ("Reasoning") with tool invocations ("Acting"). Rather than a single prompt-
     response, the agent operates in an autonomous loop:
     Query -> [Thought -> Action -> Observation]* -> Final Answer.
   - JS/TS Equivalent: Similar to an event-driven finite state machine (FSM)
     or Redux middleware loop in Node.js, where actions trigger side-effects
     that feed new state back into the reducer until a terminal state is reached.
   - Key Architecture:
     * Memory / Scratchpad: Keeps track of past thoughts, tool inputs, and outputs.
     * Tool Registry: Maps tool names to executable functions with schemas.
     * Guardrails: Halting conditions (Max Iterations, Cycle Detection, Token Cap).

2. UNDER THE HOOD (CPython & Memory):
   - The Agent State Machine maintains an append-only conversation history.
   - Self-Correction Mechanism: When a tool throws an error (e.g. invalid SQL
     syntax or file not found), the error is formatted as an `Observation`
     and returned to the model. The model reads the error and self-corrects its
     next Action.
   - Cycle Detection: Hashes `(tool_name, tool_arguments)`. If the identical
     action is executed 3 times consecutively, the loop detects an infinite
     thrashing pattern and forces an exit or changes the system instructions.

3. COMMON GOTCHA:
   - Runaway Cost & Infinite Loops: An agent that encounters an unexpected tool
     failure can loop 50 times in 2 minutes, burning $20 of API tokens. You
     MUST implement hard ceilings: `max_iterations = 6`, `timeout = 30.0`,
     and `max_cost_usd = 0.50`.
   - Tool Side-Effect Sandboxing: Never give an agent destructive commands
     (`DROP TABLE`, `rm -rf`) without a human-in-the-loop approval gate.

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   - Interview Question: "Explain the ReAct agent architecture and how you
     prevent infinite loops and hallucinations in production."
   - How to Answer Out Loud (60-90 sec verbal script):
     * "The ReAct pattern combines chain-of-thought reasoning with tool execution.
       At each step, the model outputs a `Thought` explaining its hypothesis,
       followed by an `Action` specifying the tool and arguments to execute."
     * "The backend executes the tool and injects the output as an `Observation`.
       The model uses this observation to decide the next step, repeating until
       it concludes with `Final Answer`."
     * "To make this production-safe, I implement three deterministic guardrails:
       First, a hard iteration ceiling (e.g. max 5 steps). Second, cycle detection
       that halts if the agent attempts the exact same action twice. Third, total
       token and cost limits."
     * "If a tool fails, we pass the error back as the observation so the agent
       can self-correct. For irreversible actions like sending an email or
       updating a database, we pause the loop and require Human-in-the-Loop
       approval."
================================================================================
"""

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass

import json
from dataclasses import dataclass, field
from typing import Any, Callable


# ── Agent State Models ───────────────────────────────────────────────────────

@dataclass
class AgentStep:
    thought: str
    action_tool: str | None = None
    action_input: dict[str, Any] | None = None
    observation: str | None = None


@dataclass
class AgentResult:
    final_answer: str
    total_steps: int
    steps_history: list[AgentStep]
    success: bool
    termination_reason: str


# ── Mock Tool Sandbox ────────────────────────────────────────────────────────

def tool_database_lookup(table: str, query: str) -> str:
    """Mock database tool."""
    if table == "users":
        return json.dumps([{"id": 1, "name": "Alice", "role": "admin", "status": "active"}])
    elif table == "orders":
        return json.dumps([{"order_id": "ORD-99", "amount": 250.0, "status": "shipped"}])
    return json.dumps({"error": f"Table '{table}' does not exist."})


def tool_calculator(expression: str) -> str:
    """Mock calculator tool."""
    allowed = set("0123456789+-*/.() ")
    if not all(c in allowed for c in expression):
        return json.dumps({"error": "Disallowed characters in math expression."})
    try:
        val = eval(expression)  # In production, use AST-based safe evaluator
        return json.dumps({"result": val})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Autonomous ReAct Execution Engine ────────────────────────────────────────

class ReActAgent:
    """
    Production-grade ReAct agent loop with:
    1. Multi-step reasoning
    2. Tool dispatch & self-correction
    3. Action cycle detection
    4. Max iteration ceiling
    """

    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.tools: dict[str, Callable[..., str]] = {
            "database_lookup": tool_database_lookup,
            "calculator": tool_calculator,
        }

    def _mock_llm_decide_step(self, question: str, history: list[AgentStep]) -> tuple[str, str | None, dict[str, Any] | None]:
        """
        Simulates LLM next-step decision based on scratchpad history.
        Returns: (Thought, ActionTool, ActionInput)
        """
        step_num = len(history) + 1

        if "user" in question.lower() and "order" in question.lower():
            if step_num == 1:
                return (
                    "I need to check user information first to find the user ID.",
                    "database_lookup",
                    {"table": "users", "query": "name=Alice"},
                )
            elif step_num == 2:
                return (
                    "User Alice has ID 1. Now I should query orders for user 1.",
                    "database_lookup",
                    {"table": "orders", "query": "user_id=1"},
                )
            elif step_num == 3:
                return (
                    "Order ORD-99 was found with amount $250. Now compute 10% discount.",
                    "calculator",
                    {"expression": "250 * 0.90"},
                )
            else:
                return (
                    "I have gathered the user details, order ORD-99, and discounted total of $225.",
                    None,  # Terminal state: Final Answer
                    None,
                )

        # Fallback for simple calculation
        if "calc" in question.lower():
            if step_num == 1:
                return ("Calculate the total.", "calculator", {"expression": "100 + 45"})
            return ("Calculation complete.", None, None)

        return ("I can answer this directly without tools.", None, None)

    def run(self, user_question: str) -> AgentResult:
        """Executes the autonomous reasoning loop."""
        history: list[AgentStep] = []
        action_signatures_seen: list[str] = []

        print(f"  [AGENT START] Goal: '{user_question}'")

        for iteration in range(1, self.max_iterations + 1):
            thought, tool_name, tool_input = self._mock_llm_decide_step(user_question, history)

            step = AgentStep(thought=thought, action_tool=tool_name, action_input=tool_input)

            # Check for Final Answer (terminal state)
            if tool_name is None:
                history.append(step)
                print(f"    Step {iteration} [FINAL ANSWER]: {thought}")
                return AgentResult(
                    final_answer=thought,
                    total_steps=iteration,
                    steps_history=history,
                    success=True,
                    termination_reason="goal_achieved",
                )

            # Cycle Detection: Detect if identical action was already executed
            action_sig = f"{tool_name}:{json.dumps(tool_input, sort_keys=True)}"
            if action_signatures_seen.count(action_sig) >= 2:
                print(f"    [CYCLE DETECTED] Action '{action_sig}' repeated 3 times. Breaking loop!")
                return AgentResult(
                    final_answer="Aborted due to cyclic thrashing.",
                    total_steps=iteration,
                    steps_history=history,
                    success=False,
                    termination_reason="cycle_detected",
                )
            action_signatures_seen.append(action_sig)

            print(f"    Step {iteration} [THOUGHT]: {thought}")
            print(f"           [ACTION]:  {tool_name}({tool_input})")

            # Execute tool safely
            tool_fn = self.tools.get(tool_name)
            if not tool_fn:
                observation = json.dumps({"error": f"Tool '{tool_name}' not found."})
            else:
                try:
                    observation = tool_fn(**(tool_input or {}))
                except Exception as e:
                    observation = json.dumps({"error": f"Tool exception: {str(e)}"})

            step.observation = observation
            print(f"           [OBSERV]:  {observation[:60]}...")
            history.append(step)

        # Max iterations reached
        print(f"    [HALTED] Max iterations ({self.max_iterations}) exceeded.")
        return AgentResult(
            final_answer="Reached maximum iteration limit without terminal state.",
            total_steps=self.max_iterations,
            steps_history=history,
            success=False,
            termination_reason="max_iterations_exceeded",
        )


# ── Demonstration Functions ──────────────────────────────────────────────────

def demonstrate_react_agent_execution():
    """Demonstrates multi-step ReAct agent achieving a multi-hop goal."""
    print("  --- Demonstration: Multi-Step Autonomous ReAct Loop ---")
    agent = ReActAgent(max_iterations=6)
    question = "Find Alice's orders and calculate the price with 10% discount"
    result = agent.run(question)

    print(f"\n    Status: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"    Termination Reason: {result.termination_reason}")
    print(f"    Total Steps: {result.total_steps}")
    print(f"    Final Answer: {result.final_answer}")
    return result


# ══════════════════════════════════════════════════════════════════════
# SELF-TEST CHALLENGES
# ══════════════════════════════════════════════════════════════════════

def run_tests():
    """Automated verification for Phase 11 File 5."""
    print("\n[*] Running automated self-tests...")

    agent = ReActAgent(max_iterations=5)

    # Test 1: Direct answer without tools
    res1 = agent.run("What is your name?")
    assert res1.success is True
    assert res1.total_steps == 1
    assert res1.termination_reason == "goal_achieved"

    # Test 2: Single tool invocation
    res2 = agent.run("Please calc 100 + 45")
    assert res2.success is True
    assert res2.total_steps == 2
    assert res2.steps_history[0].action_tool == "calculator"

    # Test 3: Multi-step tool execution
    res3 = agent.run("Find Alice's user info and order")
    assert res3.success is True
    assert res3.total_steps == 4
    assert len(res3.steps_history) == 4

    # Test 4: Database tool handles unknown table
    err_res = tool_database_lookup("nonexistent", "")
    assert "error" in err_res

    # Test 5: Calculator tool handles disallowed characters
    calc_err = tool_calculator("import os; os.system('ls')")
    assert "error" in calc_err

    # Test 6: Calculator tool evaluates valid math
    calc_ok = tool_calculator("25 * 4")
    assert json.loads(calc_ok)["result"] == 100

    # Test 7: Max iteration ceiling halts execution
    capped_agent = ReActAgent(max_iterations=2)
    res_capped = capped_agent.run("Find Alice's user info and order")
    assert res_capped.success is False
    assert res_capped.termination_reason == "max_iterations_exceeded"
    assert res_capped.total_steps == 2

    # Test 8: Agent step data structure
    step = AgentStep(thought="Thinking", action_tool="calc", action_input={"x": 1}, observation="10")
    assert step.thought == "Thinking"
    assert step.observation == "10"

    # Test 9: Tool lookup error handling
    agent_bad_tool = ReActAgent()
    # Replace decide step to call missing tool
    agent_bad_tool._mock_llm_decide_step = lambda q, h: ("Thought", "unknown_tool", {})
    bad_res = agent_bad_tool.run("Test unknown tool")
    assert not bad_res.success
    assert "unknown_tool" in bad_res.steps_history[0].action_tool

    # Test 10: Cycle detection guardrail
    cycle_agent = ReActAgent(max_iterations=10)
    cycle_agent._mock_llm_decide_step = lambda q, h: ("Looping thought", "calculator", {"expression": "1+1"})
    cycle_res = cycle_agent.run("Force cycle")
    assert cycle_res.success is False
    assert cycle_res.termination_reason == "cycle_detected"

    print("[SUCCESS] All 10 ReAct Agent self-tests passed!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 11: ReAct Agent Architecture & Autonomous Tool Loops")
    print("=" * 70)
    demonstrate_react_agent_execution()
    print("-" * 70)
    run_tests()
    print("=" * 70)
