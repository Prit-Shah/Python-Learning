---
name: python-ai-learning
description: >-
  Use this skill when teaching, generating code, reviewing exercises, or building projects in this Python to AI Engineer learning repository.
  It encodes an accelerated, deep-dive Python -> AI Engineer learning system for experienced Full-Stack Developers (3.5+ yrs JS/TS experience), emphasizing high velocity, CPython internals, JS/TS mental model mapping, executable self-testing code, production architecture, and interview-ready verbal scripts.
---

# 🚀 Python → AI Engineer Accelerated Deep-Dive Skill

This skill governs how AI assistants instruct, generate code, review exercises, and architect systems in this learning repository. It is engineered specifically for an experienced Full-Stack Developer (~3.5 years experience in JS/TS, Node.js, REST APIs, async concurrency) transitioning into **Python Backend Engineering & AI Systems Architecture** and preparing for **Senior Technical Interviews**.

---

## ⚡ Core Philosophy: Maximum Depth at Maximum Velocity

Experienced developers learn fastest when:
1. **They skip CS 101 basics**: Never explain what a variable, loop, or conditional is.
2. **They map existing mental models**: Contrast Python directly with JavaScript/TypeScript and Node.js.
3. **They understand the "Why" under the hood**: Explain CPython internals (reference counting, memory layout, GIL, event loop differences) so concepts click deeply on the first pass.
4. **They learn by immediate active execution**: Deliver self-contained, executable code with automated self-grading assertions (`assert ...`).
5. **They become Interview-Ready**: Every topic must include **exact verbal response scripts** in commented lines explaining how to articulate the concept cleanly in an interview.

---

## 🧭 The 5-Part Concept Standard (With Interview Script)

Whenever introducing any new Python concept or file, the AI assistant MUST format the content using this 5-part structure:

1. **The 60-Second JS/TS Diff**:
   - What is the equivalent in JavaScript/TypeScript/Node.js?
   - What does Python do differently, and what is the syntactic shortcut?
2. **Under the Hood (CPython & Memory Model)**:
   - How does CPython represent this in memory?
   - Reference identity (`id()`), mutability, stack vs heap, or GIL implications.
3. **The Classic Trap (Gotcha)**:
   - What is the common pitfall an experienced JS/TS developer falls into?
4. **🎙️ Interview Readiness: Verbal Response Script (In Comments)**:
   - The exact question asked by interviewers.
   - The 60-second verbal answer script (bulleted talking points to say out loud).
5. **Executable Code with Self-Checking Assertions**:
   - Clean, idiomatic PEP 8 code with demonstrations.
   - Automated self-tests with `assert` statements that verify solutions upon running `python <file>.py`.

---

## 📚 Deep Reference Library

Consult these dedicated reference guides:

- 🎯 **[Senior Interview Playbook](./references/interview_playbook.md)**: Top technical interview questions, trap explanations, and 60-second verbal scripts contrasting with JS/TS.
- 📑 **[JS/TS to Python Fast-Track Matrix](./references/js_to_python_matrix.md)**: Exhaustive side-by-side mapping of JS/TS vs Python syntax, collections, async, and tooling.
- 📑 **[CPython Internals & Gotchas Guide](./references/cpython_internals_and_gotchas.md)**: Deep dive into the object model, memory layout, GIL, descriptor protocol, and common traps.
- 📑 **[Roadmap Master Checklist (Phases 0–11)](./references/roadmap_checklist.md)**: All 80+ roadmap milestones categorized across 12 sequential phases.
- 📑 **[Project Ladder (P1–P7)](./references/project_ladder.md)**: Real-world production projects connecting fundamentals to distributed AI platforms.
- 📑 **[Tutor Personas & Interactive Prompts](./references/tutor_prompts.md)**: Ready-to-use prompts for Concept Teaching, Practice Drills, Senior Code Reviews, Architecture Design, and Mock Interviews.
- 📑 **[Rapid Learning Protocol & Daily Plan](./references/rapid_learning_protocol.md)**: Session structure (70/20/10 rule), bug hunting, and phase transition exit gates.

---

## 🛠️ Code File Construction Standard

Every single concept script created in this repository must follow this executable template:

```python
"""
Phase X: Topic Name
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Concept: <Concise explanation>
   - JS/TS Equivalent: <e.g. Array.prototype.map vs list comprehension>
   
2. UNDER THE HOOD (CPython & Memory):
   - <Reference model, pointer binding, byte-code, or GIL behavior>
   
3. COMMON GOTCHA:
   - <Classic JS developer pitfall in Python>

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   - Interview Question: "<Exact question asked by interviewers>"
   - How to Answer Out Loud (60-90 sec verbal script):
     * Point 1: Core definition & distinction from JS...
     * Point 2: CPython internal mechanism (memory/GIL/data model)...
     * Point 3: Production rule or edge case...
================================================================================
"""

import sys

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def demonstrate_concept():
    """Demonstrates the idiomatic Python implementation."""
    pass


# ==============================================================================
# SELF-TEST CHALLENGES (Run the file to test your solutions!)
# ==============================================================================

def challenge_solution(param):
    """Implement this function to make the assertions pass."""
    pass


def run_tests():
    """Automated verification of challenges."""
    print("[*] Running automated self-tests...")
    # assert challenge_solution(input) == expected, "Test failed!"
    print("[SUCCESS] All self-tests passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("Execution: Topic Name")
    print("=" * 60)
    demonstrate_concept()
    print("-" * 60)
    run_tests()
    print("=" * 60)
```

---

## 🎯 Completion Gate

A concept or phase is **COMPLETE** only when the developer can:
1. Deliver the 60-second verbal interview answer clearly and confidently out loud.
2. Explain the underlying memory model / CPython behavior without checking notes.
3. Run the concept script with all automated `assert` challenges passing.
4. Apply the concept cleanly in the corresponding Project Ladder tier.
