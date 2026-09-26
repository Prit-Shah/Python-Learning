r"""
05_react_agent_execution_loop.py

============================================================
1. CONCEPT
============================================================

The ReAct (Reasoning + Acting) design pattern represents the foundational architecture
of autonomous AI agents. Unlike passive single-turn chatbots, a ReAct agent operates in an
iterative cognitive loop, decomposing complex goals into sequential reasoning steps, executing
external tools, observing results, and self-correcting:

1. The ReAct Cognitive State Machine:
   - The loop proceeds cyclically through four distinct phases:
     $$\text{Goal} \longrightarrow [\text{Thought}_t \longrightarrow \text{Action}_t \longrightarrow \text{Observation}_t]^* \longrightarrow \text{Final Answer}$$
     * Thought: The model generates explicit chain-of-thought reasoning explaining its hypothesis,
       deductive logic, and current intent.
     * Action: The model selects a specific tool and emits structured parameters:
       `Action: search_database(table="users", query="alice")`.
     * Observation: The host application executes the tool and injects the raw output back into
       the agent's trajectory.
     * Final Answer: When sufficient evidence has been accumulated, the agent synthesizes the
       terminal response and halts the loop.

2. Deterministic Guardrails & Termination Predicates:
   - In production, agents MUST NEVER be allowed to run unconstrained:
     * Iteration Ceiling (`max_iterations`): Hard cap (typically 5 to 10 steps) preventing runaway loops.
     * Cycle / Thrashing Detection: Tracks action hashes $H(t) = \text{hash}(tool, args)$. If the
       agent repeats the identical action consecutively, the loop interrupts the cycle.
     * Total Cost / Token Ceiling: Aborts execution if cumulative token expenditure exceeds budget.

3. Self-Correction via Environmental Feedback:
   - Tools inevitably fail (e.g. database syntax error, 404 Not Found, invalid date format).
   - Rather than crashing the process, the error is caught and formatted as an `Observation`:
     `Observation: Error: Table 'user' does not exist. Did you mean 'users'?`
   - The model observes its mistake and self-corrects its next Action.

4. Human-in-the-Loop (HITL) Authorization Gate:
   - Tools are partitioned by risk level:
     * Safe / Read-Only (Search, Query, Calculate): Executed autonomously.
     * Mutating / High-Impact (Send Email, Transfer Funds, Drop Table): Pauses the loop and
       awaits explicit cryptographic or UI token confirmation from a human supervisor.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (ReAct Agent Pattern)       | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| State Machine Loop           | While loop maintaining trajectory  | Async while loop / state machine   |
| Trajectory Representation    | List of typed Pydantic dataclasses | Array of step objects / Redux log  |
| Tool Execution Dispatch      | Dict lookup: `REGISTRY[name](**)`  | Object map: `tools[name].call()`   |
| Cycle Detection              | Set of hashed action tuples        | Set of JSON-serialized strings     |
| Human-in-the-Loop Gate       | Suspended generator / callback     | Async Promise resolution / webhook |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Architecture Differences:
1. In Node.js, agent frameworks often rely on asynchronous event emitters or Promise chains.
2. In Python, an agent loop is typically modeled as a clean, synchronous or asynchronous state
   machine where trajectory states are strictly typed, serializable, and auditable for debugging
   and compliance replays.


============================================================
3. UNDER THE HOOD (Token Compounding & Cycle Detection)
============================================================

1. The $O(N^2)$ Trajectory Token Compounding Effect:
   - On step 1, the model receives: `[System, Goal]`.
   - On step 2, the model receives: `[System, Goal, Thought 1, Action 1, Observation 1]`.
   - On step 3, the model receives: `[System, Goal, T1, A1, O1, T2, A2, O2]`.
   - As trajectory length $N$ increases, input tokens scale quadratically: $\sum_{i=1}^N i \approx \frac{N^2}{2}$.
   - Mitigation: Sliding window scratchpads or compacting intermediate observations into
     summarized key-value bullet points.

2. Loop Cycle Hashing:
   - A cycle detector maintains an action history ring buffer.
   - At each step: `action_signature = (action_name, frozenset(action_args.items()))`.
   - If the same signature appears 2 times consecutively, the agent is stuck in an infinite
     feedback trap. The engine interrupts the loop with a directive prompt:
     `"You have repeated this action. You must choose an alternative approach or conclude."`


============================================================
4. COMMON GOTCHAS
============================================================

1. Uncaught Tool Exceptions Crashing the Process:
   - Allowing Python exceptions (e.g. `KeyError`, `IndexError`) to propagate out of tools.
   - This terminates the entire agent runtime instead of feeding the error back as an Observation.
   - FIX: Always wrap tool execution in `try...except Exception as e:` and return the stringified error.

2. Unbounded Runaway Loops Burning Capital:
   - Deploying an agent with `while True:` without a strict `max_iterations` counter.
   - An infinite loop can execute 100 API calls in 3 minutes, burning tens of dollars and
     exhausting rate limit quotas.
   - FIX: Hardcode `max_iterations = 6` with automated alerting on limit breach.

3. Autonomous Execution of Destructive Mutations:
   - Giving agents unfettered write access to production APIs or databases.
   - FIX: Implement a mandatory Human-in-the-Loop authorization gate for all non-idempotent actions.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Explain the ReAct pattern and how it fundamentally differs from standard prompt-response generation."
A1: "The ReAct (Reasoning + Acting) pattern transforms an LLM from a one-shot text generator into an
     autonomous decision-making agent.
     In a standard prompt-response, the model generates an answer in a single forward pass without external feedback.
     In ReAct, the model operates in a cyclical cognitive loop: it outputs a 'Thought' explaining its reasoning,
     followed by an 'Action' requesting a tool execution. The application executes the tool and injects the
     result as an 'Observation'. The model uses this observation to plan its next step, repeating until it
     concludes with a 'Final Answer'.
     This enables the model to gather real-time data, query private databases, and verify its own intermediate
     hypotheses before providing an answer."

Q2: "How do you make an autonomous ReAct agent production-ready and prevent runaway infinite loops?"
A2: "I enforce four deterministic production guardrails:
     First, a hard iteration limit ceiling (typically 5 to 8 steps). If exceeded, the agent halts and gracefully
     reports that the task could not be resolved within budget.
     Second, Cycle Detection: I hash the tool name and arguments at every step; if the agent attempts the identical
     action consecutively, the engine breaks the loop to prevent thrashing.
     Third, Error Reflection: all tool exceptions are caught and formatted as Observations, allowing the agent to
     self-correct without crashing the host process.
     Fourth, Human-in-the-Loop (HITL) gates: any mutating or high-risk action (such as deleting records or
     executing financial transactions) pauses the loop and requires an explicit authorization token from a human
     operator before proceeding."

Q3: "Why does the ReAct loop experience quadratic token growth, and how do you optimize it?"
A3: "At each step of a ReAct loop, the entire historical trajectory—every prior thought, action, and observation—must
     be re-sent to the model so it retains memory of what it has already accomplished. This causes input tokens to
     grow quadratically ($O(N^2)$) with the number of steps.
     To optimize this, I implement two strategies:
     First, Observation Truncation: raw tool responses (such as a 100-row database result) are truncated or summarized
     before being added to the scratchpad, preserving only the relevant keys.
     Second, Trajectory Compaction: for long-horizon tasks exceeding 6 steps, an intermediate summarization pass
     compresses older thought-action-observation turns into a concise executive summary, keeping prompt sizes
     bounded and predictable."
"""

import sys
import json
import warnings
warnings.filterwarnings("ignore")
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# 1. TRAJECTORY STEP MODELS
# ==============================================================================

class StepType(str, Enum):
    THOUGHT = "THOUGHT"
    ACTION = "ACTION"
    OBSERVATION = "OBSERVATION"
    FINAL_ANSWER = "FINAL_ANSWER"


@dataclass
class AgentStep:
    step_type: StepType
    content: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None


# ==============================================================================
# 2. TOOL REGISTRY WITH HUMAN-IN-THE-LOOP (HITL) GATES
# ==============================================================================

class ToolMetadata:
    def __init__(self, name: str, description: str, fn: Callable, is_mutating: bool = False):
        self.name = name
        self.description = description
        self.fn = fn
        self.is_mutating = is_mutating


class AgentToolRegistry:
    """Manages agent tools and enforces Human-in-the-Loop authorization for mutations."""

    def __init__(self):
        self.tools: Dict[str, ToolMetadata] = {}

    def register(self, name: str, description: str, fn: Callable, is_mutating: bool = False):
        self.tools[name] = ToolMetadata(name, description, fn, is_mutating)

    def execute(self, name: str, args: Dict[str, Any], human_approved: bool = False) -> str:
        if name not in self.tools:
            return f"Error: Tool '{name}' does not exist in registry."

        tool = self.tools[name]

        # Enforce Human-in-the-Loop authorization gate on mutating actions
        if tool.is_mutating and not human_approved:
            return f"BLOCKED: Action '{name}' is a mutating action requiring Human-in-the-Loop approval."

        try:
            result = tool.fn(**args)
            return json.dumps(result) if not isinstance(result, str) else result
        except Exception as e:
            # Self-correction: Return error string so agent can observe its mistake
            return f"Tool Execution Error: {type(e).__name__}: {str(e)}"


# Concrete mock tools
def mock_search_kb(query: str) -> str:
    db = {
        "refund_policy": "Full refunds are permitted within 30 days of purchase with receipt.",
        "shipping_time": "Standard shipping takes 3-5 business days."
    }
    for k, v in db.items():
        if k in query.lower():
            return v
    return "No matching records found in knowledge base."


def mock_database_query(user_id: int) -> Dict[str, Any]:
    if user_id == 42:
        return {"id": 42, "name": "Arthur Dent", "purchase_days_ago": 14, "item": "Sub-Etha Sensor"}
    raise ValueError(f"Customer #{user_id} not found in database.")


def mock_issue_refund(user_id: int, amount_usd: float) -> str:
    return f"SUCCESS: Refund of ${amount_usd:.2f} issued to customer #{user_id}."


# ==============================================================================
# 3. REACT AGENT CORE ENGINE
# ==============================================================================

class ReActAgent:
    """
    Autonomous ReAct execution loop with:
    - Thought -> Action -> Observation -> Final Answer sequence
    - Hard iteration limit guardrail
    - Consecutive action cycle detection
    - Self-correction on tool errors
    - Human-in-the-Loop authorization
    """

    def __init__(self, registry: AgentToolRegistry, max_iterations: int = 5):
        self.registry = registry
        self.max_iterations = max_iterations
        self.trajectory: List[AgentStep] = []
        self._action_history: List[str] = []

    def _hash_action(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        serialized_args = json.dumps(tool_args, sort_keys=True)
        return f"{tool_name}:{serialized_args}"

    def run(
        self,
        goal: str,
        simulated_llm_planner: Callable[[str, List[AgentStep]], Tuple[StepType, str, Optional[str], Optional[Dict[str, Any]]]],
        human_approved_actions: Set[str] = set()
    ) -> str:
        self.trajectory.clear()
        self._action_history.clear()

        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1

            # 1. LLM plans next step based on goal and past trajectory
            step_type, text_content, tool_name, tool_args = simulated_llm_planner(goal, self.trajectory)

            if step_type == StepType.FINAL_ANSWER:
                self.trajectory.append(AgentStep(StepType.FINAL_ANSWER, content=text_content))
                return text_content

            if step_type == StepType.THOUGHT:
                self.trajectory.append(AgentStep(StepType.THOUGHT, content=text_content))

            elif step_type == StepType.ACTION:
                assert tool_name is not None and tool_args is not None
                action_hash = self._hash_action(tool_name, tool_args)

                # Cycle Detection: halt if exact same action executed twice consecutively
                if len(self._action_history) >= 1 and self._action_history[-1] == action_hash:
                    error_msg = f"Loop Cycle Detected: Agent repeated action '{tool_name}' with identical parameters."
                    self.trajectory.append(AgentStep(StepType.OBSERVATION, content=error_msg))
                    return f"Agent Halted: {error_msg}"

                self._action_history.append(action_hash)
                self.trajectory.append(AgentStep(StepType.ACTION, content=text_content, tool_name=tool_name, tool_args=tool_args))

                # Check Human-in-the-Loop approval
                is_approved = action_hash in human_approved_actions

                # 2. Execute tool and inject Observation
                observation = self.registry.execute(tool_name, tool_args, human_approved=is_approved)
                self.trajectory.append(AgentStep(StepType.OBSERVATION, content=observation))

        return "Agent Halted: Maximum iteration limit reached without concluding."


# ==============================================================================
# 4. SELF-TESTING SUITE
# ==============================================================================

def run_tests() -> None:
    print("\n[*] Starting automated test suite for 05_react_agent_execution_loop.py...")

    registry = AgentToolRegistry()
    registry.register("search_kb", "Search company knowledge base", mock_search_kb, is_mutating=False)
    registry.register("get_customer", "Lookup customer purchase record", mock_database_query, is_mutating=False)
    registry.register("issue_refund", "Refund customer funds", mock_issue_refund, is_mutating=True)

    agent = ReActAgent(registry, max_iterations=6)

    # ------------------------------------------------------------
    # Test 1: Full Autonomous Goal Completion (Thought -> Action -> Observation -> Final Answer)
    # ------------------------------------------------------------
    print("  -> Testing full autonomous ReAct trajectory to Final Answer...")
    # Mock planner that simulates an LLM resolving a refund inquiry
    plan_step = 0
    def mock_planner_success(goal: str, traj: List[AgentStep]):
        nonlocal plan_step
        plan_step += 1
        if plan_step == 1:
            return StepType.ACTION, "Looking up customer record", "get_customer", {"user_id": 42}
        elif plan_step == 2:
            return StepType.ACTION, "Checking refund policy", "search_kb", {"query": "refund_policy"}
        else:
            return StepType.FINAL_ANSWER, "Customer Arthur Dent is eligible for refund (purchased 14 days ago, policy is 30 days).", None, None

    final_ans = agent.run("Can customer 42 get a refund?", mock_planner_success)
    assert "Arthur Dent is eligible" in final_ans
    assert len(agent.trajectory) == 5  # Action1, Obs1, Action2, Obs2, FinalAnswer
    assert agent.trajectory[0].step_type == StepType.ACTION
    assert agent.trajectory[1].step_type == StepType.OBSERVATION
    assert agent.trajectory[-1].step_type == StepType.FINAL_ANSWER

    # ------------------------------------------------------------
    # Test 2: Error Self-Correction via Observation
    # ------------------------------------------------------------
    print("  -> Testing agent self-correction after tool execution error...")
    error_step = 0
    def mock_planner_error_recovery(goal: str, traj: List[AgentStep]):
        nonlocal error_step
        error_step += 1
        if error_step == 1:
            # Mistake: queries non-existent user 999
            return StepType.ACTION, "Checking user", "get_customer", {"user_id": 999}
        elif error_step == 2:
            # Inspect previous observation: saw error, now self-corrects to user 42
            last_obs = traj[-1].content
            assert "ValueError" in last_obs
            return StepType.ACTION, "Correcting to user 42", "get_customer", {"user_id": 42}
        else:
            return StepType.FINAL_ANSWER, "Found customer Arthur Dent after correction.", None, None

    ans_recovered = agent.run("Find customer details", mock_planner_error_recovery)
    assert "Arthur Dent" in ans_recovered
    # Trajectory must show the error observation followed by the self-corrected action
    assert "ValueError" in agent.trajectory[1].content
    assert agent.trajectory[2].tool_args == {"user_id": 42}

    # ------------------------------------------------------------
    # Test 3: Cycle / Thrashing Detection Guardrail
    # ------------------------------------------------------------
    print("  -> Testing cycle detector halts infinite loop on duplicate actions...")
    def mock_planner_infinite_cycle(goal: str, traj: List[AgentStep]):
        # Erroneously repeats the exact same action repeatedly
        return StepType.ACTION, "Retrying query", "search_kb", {"query": "missing_item"}

    halt_msg = agent.run("Find missing item", mock_planner_infinite_cycle)
    assert "Loop Cycle Detected" in halt_msg
    assert "Agent Halted" in halt_msg

    # ------------------------------------------------------------
    # Test 4: Maximum Iterations Ceiling Guardrail
    # ------------------------------------------------------------
    print("  -> Testing maximum iteration ceiling prevents runaway execution...")
    infinite_step = 0
    def mock_planner_never_concludes(goal: str, traj: List[AgentStep]):
        nonlocal infinite_step
        infinite_step += 1
        # Slightly modifies query so cycle detector doesn't trip, but never concludes
        return StepType.ACTION, f"Step {infinite_step}", "search_kb", {"query": f"item_{infinite_step}"}

    short_agent = ReActAgent(registry, max_iterations=3)
    limit_msg = short_agent.run("Run forever", mock_planner_never_concludes)
    assert "Maximum iteration limit reached" in limit_msg

    # ------------------------------------------------------------
    # Test 5: Human-in-the-Loop (HITL) Authorization Gate
    # ------------------------------------------------------------
    print("  -> Testing Human-in-the-Loop authorization gate for mutating actions...")
    def mock_planner_refund(goal: str, traj: List[AgentStep]):
        return StepType.ACTION, "Issuing refund", "issue_refund", {"user_id": 42, "amount_usd": 85.00}

    # Case A: Without human approval -> BLOCKED (trips cycle detection or halts)
    blocked_res = agent.run("Refund Arthur", mock_planner_refund)
    assert "Agent Halted" in blocked_res
    assert "BLOCKED: Action 'issue_refund' is a mutating action" in agent.trajectory[1].content

    # Case B: With human approval token -> ALLOWED
    action_signature = agent._hash_action("issue_refund", {"user_id": 42, "amount_usd": 85.00})
    success_refund_agent = ReActAgent(registry, max_iterations=2)

    def mock_planner_single_refund(goal: str, traj: List[AgentStep]):
        if len(traj) == 0:
            return StepType.ACTION, "Issuing refund", "issue_refund", {"user_id": 42, "amount_usd": 85.00}
        return StepType.FINAL_ANSWER, "Refund successfully completed.", None, None

    approved_res = success_refund_agent.run(
        "Refund Arthur",
        mock_planner_single_refund,
        human_approved_actions={action_signature}
    )
    assert approved_res == "Refund successfully completed."
    assert "SUCCESS: Refund of $85.00" in success_refund_agent.trajectory[1].content

    print("[SUCCESS] All 5 ReAct Agent Execution Loop tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 11 - 05: ReAct Autonomous Agent Execution Loop & Guardrails")
    print("=" * 70)
    run_tests()
    print("=" * 70)
