# Civic Navigator — Software Requirements Specification

```
Document ID   : CNV-SRS-001
Version       : 1.1.0
Status        : APPROVED — ready for development
Portal target : Cổng Dịch vụ công Quốc gia (DVCQG) · dichvucong.gov.vn
Language      : Agent UI fully Vietnamese
Decisions     : Instruction-only · DVCQG only · Vietnamese UI · Hard Handoff login
LLM provider  : OpenRouter (https://openrouter.ai/api/v1)
```

### Changelog from v1.0.0

| # | Area | Change |
|---|---|---|
| 1 | **Agent Architecture** | Redesigned as conversation-first agent. Conversation is the primary interface; tools (search, screenshot, highlight) are capabilities the agent equips itself with — not co-equal subsystems. |
| 2 | **Agent Memory** | Introduced `ConversationMemory` as a first-class component. The agent maintains a persistent, scoped conversation history that is passed with every LLM call, giving the agent full context of what has been said, confirmed, and actioned. |
| 3 | **Highlight Subsystem** | Redesigned as an independent LLM-powered tool. The agent calls `highlight_tool(intent)` in natural language; the tool's own LLM decides what to highlight using a fresh screenshot. This decouples highlight logic from the main agent and eliminates selector/bbox inconsistency. |
| 4 | **Tool Priority** | Agent capability stack is now explicit: (1) Conversation LLM with memory, (2) Search tool, (3) Screenshot tool, (4) Highlight tool. The agent reaches for tools only when conversation alone is insufficient. |
| 5 | **User Authority** | User messages during `awaiting_user` state are processed by the agent — the agent reads, interprets, and reacts. If the user says "I don't see that button" or "the instructions are wrong," the agent must take corrective action, not ignore the input. |
| 6 | **State Consistency** | A new `sync_ui` step after every agent action ensures the highlight, progress bar, and chat message all reflect the same step and the same intent before the agent waits for the user. |
| 7 | **AgentState Schema** | Expanded with memory fields, tool call audit trail, and UI sync tracking. |
| 8 | **Node Graph** | Simplified and restructured around conversation turns rather than a rigid sequential pipeline. |

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Component Specifications](#3-component-specifications)
   - 3.1 [Chrome Extension — Sidebar Panel](#31-chrome-extension--sidebar-panel)
   - 3.2 [Chrome Extension — Content Script](#32-chrome-extension--content-script)
   - 3.3 [FastAPI Backend](#33-fastapi-backend)
   - 3.4 [LangGraph Agent](#34-langgraph-agent)
   - 3.5 [OpenRouter LLM Integration](#35-openrouter-llm-integration)
   - 3.6 [Tavily Search Integration](#36-tavily-search-integration)
   - 3.7 [Highlight Tool (Independent LLM Subsystem)](#37-highlight-tool-independent-llm-subsystem)
4. [Agent Behavior Specification](#4-agent-behavior-specification)
   - 4.1 [Action Tier Model](#41-action-tier-model)
   - 4.2 [Agent State Machine](#42-agent-state-machine)
   - 4.3 [Conversation Memory Model](#43-conversation-memory-model)
   - 4.4 [User Authority — Handling Corrections](#44-user-authority--handling-corrections)
   - 4.5 [UI Consistency — The sync_ui Contract](#45-ui-consistency--the-sync_ui-contract)
   - 4.6 [Login Handling — Hard Handoff](#46-login-handling--hard-handoff)
   - 4.7 [Personal Data Handling — Handoff](#47-personal-data-handling--handoff)
   - 4.8 [Recovery Behavior](#48-recovery-behavior)
5. [Message & Data Contracts](#5-message--data-contracts)
   - 5.1 [WebSocket Message Protocol](#51-websocket-message-protocol)
   - 5.2 [Screenshot Payload](#52-screenshot-payload)
   - 5.3 [Session State Schema](#53-session-state-schema)
6. [UI/UX Requirements](#6-uiux-requirements)
   - 6.1 [Sidebar Panel Layout](#61-sidebar-panel-layout)
   - 6.2 [Overlay Highlight Specification](#62-overlay-highlight-specification)
   - 6.3 [Vietnamese Copy — Standard Phrases](#63-vietnamese-copy--standard-phrases)
7. [Non-Functional Requirements](#7-non-functional-requirements)
8. [Privacy & Security Constraints](#8-privacy--security-constraints)
9. [Scope Boundaries](#9-scope-boundaries)
10. [Glossary](#10-glossary)

---

## 1. Project Overview

### 1.1 Purpose

Civic Navigator is a Chrome extension + AI backend that guides Vietnamese citizens through administrative procedures on Cổng Dịch vụ công Quốc gia (DVCQG, dichvucong.gov.vn). The system acts as an intelligent, conversational guide: the user talks to it in Vietnamese, and it guides them step by step — telling them where to click, what to do, and confirming progress.

The system does NOT autonomously click, fill, or submit on behalf of the user. The user always performs actions. The agent always instructs.

### 1.2 Core Mental Model (v1.1.0)

```
Agent role  : A knowledgeable companion who talks TO the user, looks at the screen
              when needed, and highlights elements to support the conversation
User role   : A person in control of their own browser who can always correct or
              question the agent
Primary     : Conversation — the agent TALKS the user through the procedure
interface
Tools       : Search (background, silent), Screenshot (agent looks at screen),
              Highlight (agent points at elements to support its words)
Memory      : The agent remembers everything said in the session and uses it to
              stay consistent across turns
```

**Key design principle: conversation drives everything.** The agent speaks first, uses tools to support its speech, and keeps memory of what has happened so it never contradicts itself.

### 1.3 Decisions Log

The following product decisions are FIXED and must not be re-opened during development:

| Decision | Chosen Option | Rationale |
|---|---|---|
| Interaction mode | Instruction-only (no autonomous clicking) | Simplicity, user trust, safety |
| Target portal | DVCQG (dichvucong.gov.vn) only | Single focused demo scope |
| Agent UI language | Vietnamese only | Authentic to target users |
| Login handling | Hard Handoff — agent pauses and looks away | Privacy, trust |
| LLM provider | OpenRouter API | Convenience, model flexibility |
| Agent first principle | Conversation-first | Tools serve the conversation, not the other way around |
| Memory model | Full scoped conversation history per session | Consistency, user authority, context |
| Highlight architecture | Independent LLM tool | Decouples highlight logic, eliminates sync bugs |

### 1.4 Demo Scenario (Primary)

The single scenario that must work flawlessly for the hackathon demo:

```
Procedure : Gia hạn hộ chiếu (Passport renewal)
Portal    : dichvucong.gov.vn
User flow : User opens portal in Chrome → opens extension sidebar → types intent
            in Vietnamese → agent guides through full procedure → user completes
```

---

## 2. System Architecture

### 2.1 High-Level Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                      CHROME BROWSER                          │
│                                                              │
│  ┌─────────────────────┐    ┌────────────────────────────┐  │
│  │   SIDEBAR PANEL     │    │   ACTIVE TAB               │  │
│  │   (React app,       │    │   dichvucong.gov.vn         │  │
│  │    extension page)  │    │                            │  │
│  │                     │    │  ┌──────────────────────┐  │  │
│  │  • Chat messages    │    │  │  CONTENT SCRIPT      │  │  │
│  │  • Progress bar     │◄───┼──┤  • Overlay injection │  │  │
│  │  • Step indicator   │    │  │  • DOM reading       │  │  │
│  │  • Status display   │    │  │  • captureVisibleTab │  │  │
│  └────────┬────────────┘    │  └──────────────────────┘  │  │
│           │                 └────────────────────────────┘  │
│           │ WebSocket (ws://)                                │
└───────────┼──────────────────────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                           │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              CONVERSATION-FIRST AGENT                 │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  CONVERSATION LLM  ←→  ConversationMemory       │  │  │
│  │  │  (primary decision maker, always has context)   │  │  │
│  │  └────────────────────┬────────────────────────────┘  │  │
│  │                       │ calls when needed              │  │
│  │       ┌───────────────┼───────────────┐               │  │
│  │       ▼               ▼               ▼               │  │
│  │  [search_tool]  [screenshot_tool]  [highlight_tool]   │  │
│  │  (Tavily, silent)(capture + vision) (independent LLM) │  │
│  │                                                       │  │
│  │  LangGraph orchestrates: turn routing, state,         │  │
│  │  sync_ui enforcement, user authority handling         │  │
│  └────────┬────────────────┬──────────────┬─────────────┘  │
│           │                │              │                  │
│           ▼                ▼              ▼                  │
│     OpenRouter API    Tavily API    Session State            │
│     (LLM + vision)   (web search)  (in-memory dict)         │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 Communication Flow

```
1. User types message in sidebar
2. Sidebar sends WS message {type: "user_message", text: "..."}
3. Backend appends message to ConversationMemory
4. Conversation LLM processes with full history → decides next action
5. Agent emits streaming tokens via WS {type: "agent_token", token: "..."}
6. If agent decides to look at screen: sends WS {type: "request_screenshot"}
7. Content script captures tab, sidebar relays {type: "screenshot", data: "<base64>"}
8. Screenshot sent to screenshot_tool → analysis stored in AgentState
9. Agent decides whether to highlight: calls highlight_tool(intent, screenshot)
10. highlight_tool's own LLM produces selector/bbox → WS {type: "inject_overlay", ...}
11. Content script injects visual highlight on portal page
12. Agent finishes streaming its instruction (already in progress or fresh)
13. sync_ui step: verifies chat message, highlight, and progress bar describe the SAME step
14. Agent sets status = "awaiting_user" if step requires user action
15. User acts on portal; may say "Xong rồi", click done button, OR type a message
16. Any user message (including corrections) is processed by the agent with full memory
17. Agent verifies, advances, or adapts — loop continues
```

### 2.3 Technology Stack

| Layer | Technology | Version |
|---|---|---|
| Extension UI framework | React | 18.x |
| Extension build tool | Vite | 5.x |
| Extension manifest | Manifest V3 | — |
| Backend framework | FastAPI | 0.111.x |
| Backend language | Python | 3.11+ |
| Agent framework | LangGraph | 0.2.x |
| LLM provider | OpenRouter | API v1 |
| LLM model (text + conversation) | `google/gemini-2.0-flash-001` (default) | — |
| LLM model (vision / screenshot analysis) | `google/gemini-2.0-flash-001` (supports vision) | — |
| LLM model (highlight tool) | `google/gemini-2.0-flash-001` (independent call) | — |
| Search API | Tavily | v1 |
| Real-time comms | WebSocket (native FastAPI) | — |
| Session state | Python in-memory dict | — |
| CSS framework | Tailwind CSS | 3.x |

> **Note on model selection:** OpenRouter is the API gateway. The actual model can be changed by updating the `model` string in the config. The default `google/gemini-2.0-flash-001` supports text and vision. If the team prefers `openai/gpt-4o` or `anthropic/claude-sonnet-4-5`, change only the config constant — no other code changes needed.

---

## 3. Component Specifications

### 3.1 Chrome Extension — Sidebar Panel

**Type:** Extension side panel (chrome.sidePanel API, MV3)

**Responsibilities:**
- Render the chat interface (user messages, agent messages, system status)
- Display current procedure progress (step N of M)
- Relay screenshots from content script to backend
- Relay overlay injection commands from backend to content script
- Provide a "Done" / "Xong rồi" button for Handoff steps
- Display the Hard Handoff login screen (agent-looks-away state)
- Accept free-text input from user at ALL times, including during `awaiting_user` state

**Critical UI requirement (v1.1.0):** The text input field must remain enabled and accessible whenever `session_status` is `awaiting_user` or `executing`. Users must be able to type corrections, questions, or confirmations without clicking any special button. The "Xong rồi" button is a shortcut; it does not replace text input.

**File structure:**
```
extension/
├── manifest.json
├── src/
│   ├── panel/
│   │   ├── Panel.tsx          # Root sidebar component
│   │   ├── ChatFeed.tsx       # Scrollable message list
│   │   ├── MessageBubble.tsx  # Individual message rendering
│   │   ├── ProgressBar.tsx    # Step N of M display
│   │   ├── HandoffScreen.tsx  # Login / data handoff overlay
│   │   ├── StatusBar.tsx      # Agent status indicator
│   │   └── useWebSocket.ts    # WS connection hook
│   ├── content/
│   │   ├── content.ts         # Content script entry
│   │   └── overlay.ts         # Highlight overlay logic
│   └── background/
│       └── background.ts      # Service worker (MV3)
├── panel.html                 # HTML entry for side panel
└── vite.config.ts
```

**Message types the panel handles (from backend via WebSocket):**

| `type` | Action |
|---|---|
| `agent_token` | Append token to current agent message bubble |
| `agent_message_end` | Finalize current agent message bubble |
| `system_status` | Update status bar text |
| `step_update` | Update progress bar (current_step, total_steps, step_label) |
| `request_screenshot` | Trigger captureVisibleTab, send result back |
| `inject_overlay` | Forward to content script via chrome.tabs.sendMessage |
| `clear_overlay` | Forward clear command to content script |
| `handoff_start` | Show HandoffScreen component (blocks ONLY the input area, not chat) |
| `handoff_end` | Hide HandoffScreen, restore input area |
| `login_handoff_start` | Show login-specific HandoffScreen variant (full overlay) |
| `login_handoff_end` | Hide login HandoffScreen, resume |
| `procedure_complete` | Show completion state in panel |
| `ui_sync_check` | Panel responds with current visible step label and overlay label for consistency check |

**Message types the panel sends (to backend via WebSocket):**

| `type` | Payload |
|---|---|
| `user_message` | `{ text: string }` |
| `screenshot` | `{ data: string (base64 PNG), width: number, height: number, url: string }` |
| `user_done` | `{}` (user clicked "Xong rồi" / "Đã đăng nhập") |
| `session_init` | `{ session_id: string, current_url: string }` |
| `ui_sync_response` | `{ visible_step_label: string \| null, overlay_label: string \| null }` |

### 3.2 Chrome Extension — Content Script

**Type:** Content script injected into all pages matching `*://dichvucong.gov.vn/*`

**Responsibilities:**
- Receive overlay injection commands from sidebar panel via `chrome.runtime.onMessage`
- Inject highlight overlay div onto the portal page
- Remove overlay on command
- Report current URL to sidebar on navigation events

**Overlay injection spec:**

```typescript
// Message received from panel:
interface InjectOverlayMessage {
  type: "inject_overlay"
  // One of: CSS selector string OR bounding box coordinates
  selector?: string           // e.g. "#btn-submit", ".next-step-btn"
  bbox?: {                    // Absolute page coordinates (from vision model output)
    x: number
    y: number
    width: number
    height: number
  }
  label: string               // Vietnamese label shown above the highlight
                              // e.g. "Nhấn vào đây"
}
```

**Overlay DOM structure injected:**

```html
<div id="civic-nav-overlay-container">
  <div class="civic-nav-highlight">
    <div class="civic-nav-highlight-label">Nhấn vào đây</div>
    <!-- pulsing border applied via CSS animation -->
  </div>
</div>
```

**Overlay CSS requirements:**
- `position: fixed` on container, `z-index: 2147483647` (max)
- Highlight border: `2px solid #4ade80` (green)
- Pulsing animation: box-shadow glow cycling every 1.5s
- Label: white text on semi-transparent dark background, positioned above the target element
- Must not block click events on the underlying element (`pointer-events: none` on overlay)

**Content script must NOT:**
- Read, log, or transmit any form field values
- Intercept or modify form submissions
- Read cookies or localStorage

### 3.3 FastAPI Backend

**Entry point:** `backend/main.py`

**Endpoints:**

```
GET  /health                    → 200 OK, {"status": "ok"}
WS   /ws/{session_id}           → WebSocket connection for one user session
```

**WebSocket session lifecycle:**
1. Client connects to `/ws/{session_id}` where `session_id` is a UUID generated by the extension
2. Server creates a new `AgentSession` object in memory keyed by `session_id`
3. Server sends `{"type": "connected", "session_id": "..."}`
4. Bidirectional message exchange begins (see Section 5.1)
5. On disconnect: session state is retained for 10 minutes, then purged

**Concurrency model:** Each WebSocket connection runs its own async agent loop. Use `asyncio` throughout. The LangGraph agent runs in the same event loop via `async` nodes.

**File structure:**
```
backend/
├── main.py                    # FastAPI app, WS endpoint
├── agent/
│   ├── graph.py               # LangGraph state machine definition
│   ├── nodes.py               # Individual node implementations
│   ├── state.py               # AgentState TypedDict
│   ├── memory.py              # ConversationMemory class
│   ├── tools/
│   │   ├── search_tool.py     # Tavily search wrapper
│   │   ├── screenshot_tool.py # Screenshot capture + vision analysis
│   │   └── highlight_tool.py  # Independent LLM highlight subsystem
│   └── prompts.py             # All LLM prompt templates
├── services/
│   ├── openrouter.py          # OpenRouter API client
│   ├── tavily.py              # Tavily search client
│   └── vision.py              # Screenshot analysis helpers
├── models/
│   └── messages.py            # Pydantic models for WS messages
└── config.py                  # Environment config (API keys, model names)
```

**Environment variables required:**

```bash
OPENROUTER_API_KEY=sk-or-...
TAVILY_API_KEY=tvly-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=google/gemini-2.0-flash-001
```

### 3.4 LangGraph Agent

#### 3.4.1 Agent State Definition (`AgentState`)

```python
from typing import TypedDict, Optional, List, Literal

class ProcedureStep(TypedDict):
    step_number: int
    total_steps: int
    label_vi: str                    # Vietnamese step label
    expected_url_pattern: str        # Regex or substring to match expected URL
    action_tier: Literal["inform", "confirm", "handoff"]
    instruction_vi: str              # Full Vietnamese instruction for user
    field_name: Optional[str]        # For handoff steps: which field to fill
    is_personal_data: bool
    completed: bool

class ToolCallRecord(TypedDict):
    tool: str                        # "search" | "screenshot" | "highlight"
    turn: int                        # Which conversation turn triggered this
    result_summary: str              # Brief description of result for memory

class AgentState(TypedDict):
    # Identity
    session_id: str

    # --- MEMORY (v1.1.0) ---
    # Full conversation history passed to the LLM on every call.
    # Format: [{"role": "system", "content": "..."}, {"role": "user", ...}, ...]
    # The system message is rebuilt each turn with current procedure context.
    conversation_history: List[dict]

    # Scratchpad summaries injected into the system message to keep the LLM
    # grounded even as conversation_history grows. Updated after key events.
    memory_context: str              # e.g. "We are on step 3 of 7. Last action:
                                     # user confirmed clicking the submit button.
                                     # Current URL: /ho-chieu/gia-han"

    # Audit trail of tool calls made this session (not sent to LLM, for debugging)
    tool_call_history: List[ToolCallRecord]

    # Current conversation turn index (incremented on every user message)
    turn_index: int

    # --- PROCEDURE ---
    user_intent: Optional[str]
    procedure_name: Optional[str]
    procedure_steps: List[ProcedureStep]
    current_step_index: int
    search_results_raw: Optional[str]

    # --- SCREEN ---
    last_screenshot_b64: Optional[str]
    last_page_analysis: Optional[dict]
    current_url: Optional[str]

    # --- LOGIN ---
    login_required: bool
    login_completed: bool

    # --- FLOW CONTROL ---
    session_status: Literal[
        "idle",
        "parsing_intent",
        "searching",
        "planning",
        "awaiting_login",
        "executing",
        "awaiting_user",
        "verifying",
        "recovering",
        "complete",
        "error"
    ]
    error_message: Optional[str]
    recovery_attempts: int

    # --- UI CONSISTENCY (v1.1.0) ---
    # Set by sync_ui node; the agent may not proceed to awaiting_user until
    # this is True. Reset to False at the start of each new step.
    ui_synced: bool

    # The most recent instruction text emitted to the user (for sync verification)
    last_instruction_emitted: Optional[str]

    # The most recent overlay label requested (for sync verification)
    last_overlay_label_requested: Optional[str]
```

#### 3.4.2 Node Graph

```
receive_user_message
    │
    ▼
append_to_memory
    │
    ▼
conversation_turn          ← PRIMARY DECISION NODE
    │                        (LLM with full conversation_history)
    │
    ├─── intent: "start_procedure"
    │         ▼
    │    search_tutorials       (silent)
    │         ▼
    │    build_procedure_plan
    │         ▼
    │    check_login_required
    │         ├── YES → emit_login_handoff → await_login_completion
    │         └── NO  → execute_step
    │
    ├─── intent: "execute_step"
    │         ▼
    │    execute_step
    │         ▼
    │    [if not personal_data] screenshot_tool
    │         ▼
    │    highlight_tool         (independent — see Section 3.7)
    │         ▼
    │    emit_instruction
    │         ▼
    │    sync_ui                ← CONSISTENCY GATE (must pass before awaiting_user)
    │         ▼
    │    await_user_or_message
    │
    ├─── intent: "user_correction" | "user_question" | "user_done"
    │         ▼
    │    handle_user_input      (agent reads input with full memory context,
    │         │                  decides whether to verify, adapt, or advance)
    │         ▼
    │    [route based on resolution]
    │
    ├─── intent: "verify_and_advance"
    │         ▼
    │    verify_state
    │         ├── OK  → advance_step → execute_step (or emit_completion)
    │         └── BAD → recover → execute_step
    │
    └─── intent: "procedure_complete"
              ▼
         emit_completion
```

**Node: `receive_user_message`**

Receives `{type: "user_message", text: "..."}` from the WebSocket. Increments `turn_index`. Does not invoke any LLM.

**Node: `append_to_memory`**

Appends the user message to `conversation_history`:
```python
state["conversation_history"].append({"role": "user", "content": user_text})
```

Also updates `memory_context` with a brief summary of current session state:
```python
state["memory_context"] = build_memory_context(state)
```

```python
def build_memory_context(state: AgentState) -> str:
    lines = []
    if state["procedure_name"]:
        lines.append(f"Đang hỗ trợ thủ tục: {state['procedure_name']}")
    if state["procedure_steps"]:
        total = len(state["procedure_steps"])
        idx = state["current_step_index"]
        step = state["procedure_steps"][idx] if idx < total else None
        lines.append(f"Bước hiện tại: {idx + 1}/{total}" + (f" — {step['label_vi']}" if step else ""))
    if state["current_url"]:
        lines.append(f"URL hiện tại: {state['current_url']}")
    if state["last_instruction_emitted"]:
        lines.append(f"Hướng dẫn vừa phát: {state['last_instruction_emitted'][:120]}...")
    return "\n".join(lines)
```

**Node: `conversation_turn`**

The primary decision-making node. Calls the LLM with the full `conversation_history`, prepending a system message that embeds `memory_context` and the current procedure state.

System message template:
```
Bạn là Civic Navigator, trợ lý hướng dẫn thủ tục hành chính tại dichvucong.gov.vn.
Bạn luôn trả lời bằng tiếng Việt, thân thiện và rõ ràng.

=== TRẠNG THÁI PHIÊN HIỆN TẠI ===
{memory_context}

=== QUY TẮC ===
- Bạn là một cuộc hội thoại. Hãy nhớ tất cả những gì đã được nói và thực hiện trong phiên này.
- Khi người dùng nói "không thấy nút đó", "hướng dẫn sai", hoặc bất kỳ sự điều chỉnh nào,
  bạn PHẢI thừa nhận và điều chỉnh hành động của mình.
- Trước khi chuyển sang bước tiếp theo, hãy đảm bảo người dùng đã xác nhận bước hiện tại.
- Không bao giờ mâu thuẫn với những gì bạn đã nói trước đó trong phiên này.
- Nếu bạn cần nhìn màn hình, hãy yêu cầu chụp ảnh màn hình.
- Nếu bạn muốn làm nổi bật một phần tử, hãy gọi công cụ highlight.

=== ĐỊNH DẠNG PHẢN HỒI ===
Trả về JSON:
{
  "intent": "<start_procedure|execute_step|user_correction|user_question|user_done|verify_and_advance|procedure_complete|general_reply>",
  "reply_vi": "<Vietnamese reply to stream to user, or null if no reply>",
  "needs_screenshot": true/false,
  "needs_highlight": true/false,
  "highlight_intent_vi": "<Vietnamese description of what to highlight, or null>",
  "advance_step": true/false
}
```

The LLM response drives routing in the graph. `intent` determines which node is visited next.

**Node: `search_tutorials`**

- Runs silently. Does NOT emit any message to the user.
- Emits `{"type": "system_status", "text": "Đang tìm hiểu quy trình..."}` to sidebar
- Constructs 2 Tavily search queries:
  1. `"hướng dẫn {procedure_name_vi} dichvucong.gov.vn 2024"`
  2. `"{procedure_name_vi} cổng dịch vụ công quốc gia các bước"`
- Combines and deduplicates results
- Stores raw text in `search_results_raw`
- Appends to `conversation_history` as an **assistant tool_result** message so the LLM knows the search ran

**Node: `build_procedure_plan`**

Input: `search_results_raw`, `user_intent`
Output: `procedure_steps` (list of `ProcedureStep`)

Prompt contract:
```
SYSTEM: You are building a step-by-step procedure plan for guiding a Vietnamese
citizen through dichvucong.gov.vn. Parse the tutorial text and return a JSON array
of steps. Each step must include: step_number, total_steps, label_vi,
expected_url_pattern, action_tier ("inform"|"confirm"|"handoff"), instruction_vi,
field_name (null if N/A), is_personal_data (bool).

Rules:
- action_tier = "handoff" for ANY step that requires personal data input
- action_tier = "confirm" for form submissions, file uploads, clicking Next/Submit
- action_tier = "inform" for navigation, scrolling, reading content
- instruction_vi must be written in simple, clear, warm Vietnamese
- is_personal_data = true for: CMND/CCCD number, full name, date of birth,
  address, phone number, email, tax code, household book number

Return JSON array only, no other text.

TUTORIAL TEXT:
{search_results_raw}
```

After plan is built, a summary is appended to `conversation_history`:
```python
state["conversation_history"].append({
    "role": "assistant",
    "content": f"[Kế hoạch đã lập: {len(steps)} bước cho '{procedure_name}'. "
               f"Bước 1: {steps[0]['label_vi']}]"
})
```

**Node: `execute_step`**

Gets `current_step = procedure_steps[current_step_index]`

Emits:
```json
{
  "type": "step_update",
  "current_step": 2,
  "total_steps": 7,
  "step_label": "Điền thông tin cá nhân",
  "action_tier": "confirm"
}
```

If `is_personal_data = True` → transition to `handoff_personal_data` sub-flow (see Section 4.7). Otherwise → proceed to `screenshot_tool` if the conversation_turn decided `needs_screenshot = true`, then to `highlight_tool` if `needs_highlight = true`, then to `emit_instruction`.

**Node: `emit_instruction`**

Streams the current step's `instruction_vi` (or a freshly composed instruction if the LLM adapted it based on screenshot analysis) to the user via `agent_token` messages.

After streaming, stores the emitted text in `state["last_instruction_emitted"]`.

Resets `state["ui_synced"] = False` before calling `sync_ui`.

**Node: `sync_ui`**

**Purpose:** Ensure that the chat message, the overlay highlight, and the progress bar all describe the same step and intent before the agent waits for the user. This node is the gate that prevents the inconsistency between chat/highlights/progress that was a known bug in v1.0.0.

```
1. Emit {"type": "ui_sync_check"} to sidebar
2. Await {"type": "ui_sync_response", visible_step_label, overlay_label} from sidebar
3. Compare:
   - visible_step_label == current ProcedureStep.label_vi
   - overlay_label == last_overlay_label_requested (if a highlight was requested)
4. If mismatch:
   - Re-emit {"type": "step_update"} with correct values
   - Re-emit {"type": "inject_overlay"} with last overlay parameters
   - Wait 200ms, repeat check (max 2 retries)
5. If consistent (or no highlight was requested): set ui_synced = True
6. Only then: set session_status = "awaiting_user"
```

The agent MUST NOT proceed to `await_user_or_message` until `ui_synced = True`.

**Node: `await_user_or_message`**

Sets `session_status = "awaiting_user"`. Waits for any incoming message from the user — either `{type: "user_done"}` or `{type: "user_message", text: "..."}`.

Both are handled identically: appended to memory and routed through `conversation_turn`. The LLM with full context decides whether the user is confirming completion, asking a question, or making a correction.

**Node: `handle_user_input`**

Called when `conversation_turn` returns `intent = "user_correction"` or `"user_question"`.

The LLM is given the user's message in the context of the full conversation history. It MUST:

- Acknowledge what the user said
- If the user says they cannot see something: request a new screenshot and re-analyze
- If the user says the instruction was wrong: apologize briefly, re-examine, re-instruct
- If the user asks a question: answer it, then offer to continue

The node then re-routes: if a correction required a new highlight, it goes back through `highlight_tool` → `emit_instruction` → `sync_ui`. If the question was answered inline, it returns to `await_user_or_message`.

**Node: `verify_state`**

- Requests new screenshot via `screenshot_tool`
- Calls vision model to check if state matches expected post-step state
- If `page_matches_expected = True` AND `unexpected_elements` empty:
  - Marks `procedure_steps[current_step_index].completed = True`
  - Appends completion note to `conversation_history`
  - Advance `current_step_index`
  - If `current_step_index >= len(procedure_steps)`: → `emit_completion`
  - Else: → `execute_step`
- If mismatch: → `recover`

**Node: `recover`**

- Increments `recovery_attempts`
- If `recovery_attempts <= 2`:
  - Emits: `"Có vẻ có gì đó khác với trang. Để tôi kiểm tra lại..."`
  - Re-requests screenshot
  - Re-analyzes
  - If still mismatched and error visible: explains error to user in Vietnamese
  - → back to `execute_step`
- If `recovery_attempts > 2`:
  - Emits: `"Tôi gặp khó khăn với bước này. Bạn có thể mô tả bạn đang thấy gì trên màn hình không?"`
  - Sets `session_status = "awaiting_user"` for manual re-orientation

**Node: `emit_completion`**

Streams:
```
✓ Hoàn thành! Bạn đã hoàn tất {procedure_name_vi} thành công.

[Summary of what was submitted, any confirmation numbers visible on screen]

Bạn có thể đóng trợ lý này hoặc bắt đầu một thủ tục mới.
```

Appends completion to `conversation_history` so the agent remains helpful if the user asks follow-up questions.

### 3.5 OpenRouter LLM Integration

**Base URL:** `https://openrouter.ai/api/v1`

**Auth header:** `Authorization: Bearer {OPENROUTER_API_KEY}`

**Required additional headers:**
```
HTTP-Referer: https://civic-navigator.local
X-Title: Civic Navigator
```

**Text completion call pattern:**

```python
import httpx

async def call_llm(messages: list[dict], stream: bool = False) -> str | AsyncIterator:
    payload = {
        "model": config.OPENROUTER_MODEL,
        "messages": messages,
        "max_tokens": 2000,
        "temperature": 0.2,    # Low temperature for consistent procedure plans
        "stream": stream,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{config.OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://civic-navigator.local",
                "X-Title": "Civic Navigator",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60.0,
        )
    return response.json()["choices"][0]["message"]["content"]
```

**Vision call pattern (screenshot analysis):**

```python
async def call_vision(screenshot_b64: str, prompt: str) -> dict:
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{screenshot_b64}"
                    }
                },
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }
    ]
    result = await call_llm(messages, stream=False)
    # Strip markdown code fences if present before JSON parse
    clean = result.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(clean)
```

**Streaming pattern (for agent instructions to user):**

When `stream=True`, iterate over SSE chunks and emit each token via WebSocket:

```python
async for chunk in stream_response:
    token = chunk["choices"][0]["delta"].get("content", "")
    if token:
        await websocket.send_json({"type": "agent_token", "token": token})
await websocket.send_json({"type": "agent_message_end"})
```

**Conversation call pattern (v1.1.0):**

The `conversation_turn` node always calls the LLM with the full `conversation_history`. The history is built as:

```python
def build_messages_for_llm(state: AgentState) -> list[dict]:
    system_msg = {
        "role": "system",
        "content": CONVERSATION_SYSTEM_PROMPT.format(
            memory_context=state["memory_context"]
        )
    }
    # conversation_history already contains alternating user/assistant turns
    return [system_msg] + state["conversation_history"]
```

**History size management:** If `conversation_history` exceeds 40 turns, summarize the oldest 20 turns into a single assistant message using a summarization LLM call, replace the oldest 20 entries with the summary, and continue. This prevents context overflow without losing session memory.

### 3.6 Tavily Search Integration

**Client:** `tavily-python` package

**Search call pattern:**

```python
from tavily import TavilyClient

client = TavilyClient(api_key=config.TAVILY_API_KEY)

async def search_procedure_tutorial(procedure_name_vi: str) -> str:
    queries = [
        f"hướng dẫn {procedure_name_vi} dichvucong.gov.vn 2024",
        f"{procedure_name_vi} cổng dịch vụ công quốc gia các bước thực hiện",
    ]
    all_results = []
    for query in queries:
        result = client.search(
            query=query,
            search_depth="advanced",
            max_results=3,
            include_answer=True,
        )
        for r in result.get("results", []):
            all_results.append(f"SOURCE: {r['url']}\n{r['content']}")
    return "\n\n---\n\n".join(all_results)
```

**Search is always silent.** No search queries, URLs, or result snippets are ever shown to the user.

### 3.7 Highlight Tool (Independent LLM Subsystem)

**Purpose (v1.1.0):** The highlight tool is an independent, self-contained LLM subsystem. The main agent calls it with a natural-language intent; the tool's own LLM — looking at a fresh screenshot — decides what element to highlight and produces the overlay command. This decoupling ensures that highlight decisions are grounded in what is actually on screen, not in stale selector guesses from the plan-building phase.

**Interface:**

```python
async def highlight_tool(
    intent_vi: str,               # e.g. "Làm nổi bật nút Tiếp theo ở góc dưới bên phải"
    screenshot_b64: str,          # Most recent screenshot
    websocket: WebSocket          # To emit inject_overlay command
) -> HighlightResult:
    ...
```

**Internal behavior:**

```
1. Call vision LLM with screenshot + intent:

   SYSTEM: You are analyzing a screenshot of a Vietnamese government portal.
           Find the UI element described below and return its location.

   Prompt:
   Tìm phần tử phù hợp với yêu cầu: "{intent_vi}"

   Return JSON only:
   {
     "found": true/false,
     "element_description": "<what you found in Vietnamese>",
     "css_selector": "<best CSS selector, null if not determinable>",
     "bbox": {"x": 0, "y": 0, "width": 0, "height": 0},
     "label_vi": "<short Vietnamese label to show above highlight, max 4 words>",
     "confidence": "high" | "medium" | "low"
   }

2. If found = true AND confidence != "low":
   - Emit {"type": "inject_overlay", "selector": ..., "bbox": ..., "label": label_vi}
   - Store label_vi in state["last_overlay_label_requested"]
   - Return HighlightResult(success=True, label=label_vi)

3. If found = false OR confidence = "low":
   - Do NOT emit any overlay command
   - Return HighlightResult(success=False, reason="element_not_found")
   - Main agent receives this result and adapts its instruction accordingly
     (e.g., describes the element in text without a highlight)
```

**The highlight tool never emits a highlight it is not confident about.** A missing highlight with a clear verbal description is better than a highlight on the wrong element.

```python
@dataclass
class HighlightResult:
    success: bool
    label: Optional[str] = None
    reason: Optional[str] = None   # "element_not_found" | "low_confidence"
```

---

## 4. Agent Behavior Specification

### 4.1 Action Tier Model

Every agent action is classified into one of three tiers. This classification is embedded in `ProcedureStep.action_tier` and determines agent behavior. Note that in v1.1.0, tier classification influences behavior but does not override user input — the user can always send a message that changes what the agent does next.

```
┌─────────────────────────────────────────────────────────────────┐
│ TIER 1 — INFORM                                                 │
│ Color code: green                                               │
│                                                                 │
│ Applies to: Navigation, reading page content, scrolling,        │
│             pointing out elements                               │
│                                                                 │
│ Agent behavior:                                                 │
│   • Request screenshot if needed                                │
│   • Call highlight_tool if an element should be shown           │
│   • Stream instruction to user (what they should do/see)        │
│   • sync_ui: verify progress bar, highlight, and message match  │
│   • Auto-advance after brief pause (1.5s) OR immediately        │
│     if user acts or sends a message                             │
│   • Does NOT wait for explicit user confirmation                │
│                                                                 │
│ Example instruction:                                            │
│   "Trang đã tải thành công. Bạn đang ở trang Dịch vụ công.    │
│    Tôi đang tìm nút Hộ chiếu..."                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TIER 2 — CONFIRM                                                │
│ Color code: amber                                               │
│                                                                 │
│ Applies to: Clicking Next/Submit buttons, selecting options,    │
│             uploading non-sensitive files                       │
│                                                                 │
│ Agent behavior:                                                 │
│   • Request screenshot, call highlight_tool                     │
│   • Stream instruction ending with confirmation request         │
│   • sync_ui: verify consistency                                 │
│   • Display "Xong rồi" button in sidebar                        │
│   • WAIT for user to click "Xong rồi" OR send any message      │
│   • User message during wait is processed by conversation_turn  │
│   • Do NOT advance automatically                                │
│                                                                 │
│ Example instruction:                                            │
│   "Tôi thấy nút 'Tiếp theo' ở góc phải phía dưới. Vui lòng   │
│    nhấn vào đó để sang bước tiếp theo. Nhấn 'Xong rồi' khi   │
│    bạn đã nhấn nút."                                           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TIER 3 — HANDOFF                                                │
│ Color code: red                                                 │
│                                                                 │
│ Applies to: Any field requiring personal data, file uploads     │
│             of ID documents                                     │
│                                                                 │
│ Agent behavior:                                                 │
│   • Emit "handoff_start" to sidebar                            │
│   • HandoffScreen component renders (covers input area only,   │
│     chat remains readable)                                      │
│   • Stream instruction: what field to fill, what format        │
│   • sync_ui: verify progress bar reflects this step            │
│   • Agent does NOT take screenshots during handoff             │
│   • On "Xong rồi" OR user message: emit "handoff_end",        │
│     resume normal flow                                          │
│                                                                 │
│ Example instruction:                                            │
│   "Vui lòng điền số CCCD của bạn vào ô 'Số CMND/CCCD'.       │
│    Tôi sẽ không nhìn thấy thông tin này. Nhấn 'Xong rồi'     │
│    khi bạn đã điền xong."                                      │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Agent State Machine

```
                    ┌─────────┐
                    │  IDLE   │
                    └────┬────┘
                         │ user sends first message
                         ▼
                ┌─────────────────┐
                │ PARSING_INTENT  │
                └────────┬────────┘
                         │
                         ▼
                  ┌────────────┐
                  │ SEARCHING  │ ← silent
                  └─────┬──────┘
                         │
                         ▼
                  ┌────────────┐
                  │ PLANNING   │
                  └─────┬──────┘
                         │
              ┌──────────┴──────────┐
              │ login required?      │
             YES                    NO
              │                      │
              ▼                      │
       ┌──────────────┐              │
       │AWAITING_LOGIN│              │
       └──────┬───────┘              │
              │ user_done            │
              └──────────┬───────────┘
                         │
                         ▼
                  ┌────────────┐
                  │ EXECUTING  │◄──────────────────────────┐
                  └─────┬──────┘                           │
                         │                                 │
                         ▼                                 │
               ┌──────────────────┐                       │
               │  AWAITING_USER   │                       │
               │  (text input     │                       │
               │   always open)   │                       │
               └────────┬─────────┘                       │
                         │                                 │
            ┌────────────┴─────────────┐                  │
            │                          │                  │
     user_done /                 user sends               │
     "xong rồi"                  a message                │
            │                          │                  │
            ▼                          ▼                  │
    ┌──────────────────┐   ┌──────────────────────┐       │
    │   VERIFYING      │   │  conversation_turn   │       │
    └────────┬─────────┘   │  (LLM reads message  │       │
             │              │   with full memory)  │       │
             │              └──────────┬───────────┘       │
  ┌──────────┴───────┐                 │                   │
  │ state OK?         │        ┌───────┴──────┐            │
 YES                 NO        │  resolution  │            │
  │                  │         │              │            │
  │            ┌──────────┐  adapt/      answer/          │
  │            │RECOVERING│  re-instruct  continue        │
  │            └──────┬───┘    │              │            │
  │                   │        └───────┬───────┘            │
  └──────────────────┴────────────────┘                   │
                         │                                 │
                         └─────────────────────────────────┘
                         │ all steps done
                         ▼
                  ┌────────────┐
                  │  COMPLETE  │
                  └────────────┘
```

### 4.3 Conversation Memory Model

**Principle:** The agent is a conversational entity. Every LLM call includes the full conversation history. The agent never loses context of what it said, what the user said, what was confirmed, or what went wrong. This is the foundation that makes the system consistent.

**ConversationMemory class:**

```python
class ConversationMemory:
    """
    Wraps the conversation_history list in AgentState.
    Provides helper methods for common memory operations.
    """

    def add_user(self, text: str) -> None:
        """Append a user message."""

    def add_assistant(self, text: str) -> None:
        """Append an assistant message (streamed or composed)."""

    def add_tool_result(self, tool: str, summary: str) -> None:
        """
        Append a synthetic assistant message summarizing a tool call result.
        This keeps the LLM aware of tool calls without exposing raw data.
        Example: "[search_tool: Found 6-step tutorial for gia hạn hộ chiếu]"
        """

    def add_event(self, event: str) -> None:
        """
        Append a synthetic assistant message for important events.
        Example: "[Đã xác nhận bước 3: Tải tài liệu thành công]"
                 "[Người dùng đã đăng nhập]"
        """

    def summarize_oldest(self, n: int) -> None:
        """
        Summarize and compress the oldest n turns to manage context length.
        """

    def build_for_llm(self, system_prompt: str) -> list[dict]:
        """
        Return the full message list to pass to the LLM:
        [system_message, ...conversation_history]
        """
```

**Memory scope rules:**

- Tool call results (search output, screenshot analysis) are summarized into the memory as brief assistant events — not as raw data. Raw data stays in `AgentState` fields for processing, not for the LLM.
- Every step completion is recorded in memory.
- Every user correction is recorded in memory.
- Login completion is recorded in memory.
- The LLM always has access to what step was last instructed, so it can never contradict itself.

### 4.4 User Authority — Handling Corrections

**In v1.1.0, user messages have full authority during any state except `awaiting_login`.** The agent must respond meaningfully to all user messages, including during `awaiting_user`.

**Trigger phrases that require corrective action:**

The agent must recognize (but is not limited to) these patterns and escalate to `handle_user_input`:

| Pattern | Required agent response |
|---|---|
| "không thấy nút đó" / "không thấy [element]" | Re-request screenshot, re-analyze, re-highlight or describe differently |
| "hướng dẫn sai" / "làm sai rồi" / "không đúng" | Acknowledge, re-examine screen, provide corrected instruction |
| "bị lỗi" / "trang lỗi" / "không tải được" | Ask user to describe the error; provide recovery steps |
| "bước trước" / "quay lại" | Navigate back in `procedure_steps`, re-emit that step |
| "bỏ qua" / "skip" | Mark current step complete if safe to do so, advance |
| Any question ("...là gì?" / "tại sao...?" / "...ở đâu?") | Answer the question in context, then offer to continue |

**The agent must never:**
- Ignore a user message when `session_status = "awaiting_user"`
- Auto-advance a step without either a `user_done` signal or an affirmative user message
- Contradict a previous instruction without first acknowledging the contradiction
- Emit a highlight for an element that is not visible on the current screenshot

### 4.5 UI Consistency — The sync_ui Contract

Every time the agent finishes emitting an instruction and before setting `session_status = "awaiting_user"`, it must verify that the three UI components agree:

```
┌──────────────────────────────────────────────────────────────────┐
│  COMPONENT          SHOULD SHOW           CHECK                  │
│  ─────────────────────────────────────────────────────────────   │
│  Progress bar       Step N label          == ProcedureStep.label_vi │
│  Chat message       Last instruction      == last_instruction_emitted │
│  Overlay label      Highlight label       == last_overlay_label_requested │
│                     (if highlight active)                         │
└──────────────────────────────────────────────────────────────────┘
```

If any component is out of sync, the agent re-emits the correct value before waiting. This eliminates the inconsistency between sidebar highlights and conversation instructions that was a known defect in v1.0.0.

### 4.6 Login Handling — Hard Handoff

**Trigger conditions (any one is sufficient):**
- `procedure_steps` contains a step with `label_vi` matching `/(đăng nhập|đăng ký tài khoản)/i`
- Vision model identifies the current page as a login page
- HTTP 401 / redirect to login URL detected via content script URL monitoring

**Exact sequence:**

```
1. Agent appends to conversation_history:
   "[Phát hiện bước đăng nhập. Chuyển sang chế độ chờ đăng nhập.]"

2. Agent stops all screenshot capture immediately.

3. Agent emits to sidebar:
   {"type": "login_handoff_start"}

4. Sidebar renders HandoffScreen variant "login".

5. Sidebar's "Tôi đã đăng nhập" button is the ONLY interactive element shown.
   Chat is hidden. Screenshot capture is disabled.

6. User logs in manually on the portal tab.

7. User clicks "Tôi đã đăng nhập".

8. Sidebar sends {"type": "user_done"} to backend.

9. Agent sets login_completed = True.
   Agent appends to conversation_history:
   "[Người dùng đã xác nhận đăng nhập thành công.]"

10. Agent emits {"type": "login_handoff_end"}.

11. Sidebar restores normal chat view.

12. Agent requests fresh screenshot to verify login success.

13. Agent continues with execute_step.
```

**The agent must NOT:**
- Take any screenshot while `session_status = "awaiting_login"`
- Send any message to the content script while in this state
- Infer or log the user's credentials in any form

### 4.7 Personal Data Handling — Handoff

**Fields that always trigger Tier 3 Handoff:**

```python
PERSONAL_DATA_FIELDS = [
    "cmnd", "cccd", "passport_number",      # ID numbers
    "ho_ten", "full_name",                   # Name
    "ngay_sinh", "date_of_birth",            # Date of birth
    "dia_chi", "address",                    # Address
    "so_dien_thoai", "phone",               # Phone
    "email",                                 # Email
    "ma_so_thue", "tax_id",                 # Tax ID
    "so_ho_khau", "household_book",          # Household book
    "so_giay_khai_sinh", "birth_cert_no",   # Birth certificate
]
```

**Handoff instruction template:**

```
Bước này yêu cầu bạn điền {field_description}.

{specific_instruction_about_format_if_needed}

Tôi sẽ không xem hoặc lưu thông tin này. Nhấn "Xong rồi" khi bạn
đã điền xong ô này.
```

### 4.8 Recovery Behavior

When `verify_state` detects a mismatch:

**Recovery attempt 1 (recovery_attempts = 1):**
```
Emits: "Trang có vẻ hơi khác so với dự kiến. Để tôi kiểm tra lại..."
Action: Re-requests screenshot, re-analyzes, re-attempts instruction
Memory: Appends "[Recovery attempt 1: re-analyzing screen]" to conversation_history
```

**Recovery attempt 2 (recovery_attempts = 2):**
```
Emits: "Có lỗi nhỏ xảy ra. [Describes what agent sees]. Bạn vui lòng thử
        [specific corrective action]."
Action: Provides corrective instruction based on vision analysis
Memory: Appends "[Recovery attempt 2: gave corrective instruction]"
```

**Recovery attempt 3 (recovery_attempts = 3):**
```
Emits: "Tôi gặp khó khăn với bước này và cần bạn giúp đỡ. Bạn có thể
        mô tả ngắn gọn bạn đang thấy gì trên màn hình không?"
Action: Sets session_status = "awaiting_user", accepts free-text description,
        uses description (with full memory context) to re-orient
```

**Special case — DVCQG broken URL patterns:**

When the agent detects a navigation dead-end:

1. Instructs the user to navigate to the known direct URL
2. Emits the URL as a copyable text element in the sidebar
3. Instruction: `"Trang này cần truy cập qua đường dẫn trực tiếp. Vui lòng sao chép và dán đường dẫn sau vào thanh địa chỉ: [URL]"`

---

## 5. Message & Data Contracts

### 5.1 WebSocket Message Protocol

All messages are JSON objects with a required `type` field.

**Backend → Frontend messages:**

```typescript
// Token streaming (agent typing)
{ type: "agent_token"; token: string }

// Signal end of one agent message
{ type: "agent_message_end" }

// Status bar update (silent status, not in chat)
{ type: "system_status"; text: string }

// Procedure progress update
{
  type: "step_update"
  current_step: number      // 1-indexed
  total_steps: number
  step_label: string        // Vietnamese label
  action_tier: "inform" | "confirm" | "handoff"
}

// Request a screenshot from the tab
{ type: "request_screenshot" }

// Inject highlight overlay on portal page
{
  type: "inject_overlay"
  label: string             // Vietnamese label shown above highlight
  bbox?: { x: number; y: number; width: number; height: number }
  selector?: string
}

// Remove overlay
{ type: "clear_overlay" }

// Show login handoff screen
{ type: "login_handoff_start" }

// Hide login handoff screen
{ type: "login_handoff_end" }

// Show data handoff screen (for personal data fields)
{
  type: "handoff_start"
  field_description: string   // Vietnamese description of the field
}

// Hide data handoff screen
{ type: "handoff_end" }

// Procedure fully complete
{
  type: "procedure_complete"
  procedure_name_vi: string
  summary: string
}

// Connected confirmation
{ type: "connected"; session_id: string }

// UI consistency check request (v1.1.0)
{ type: "ui_sync_check" }
```

**Frontend → Backend messages:**

```typescript
// Initial session setup
{
  type: "session_init"
  session_id: string
  current_url: string
}

// User typed and sent a message
{ type: "user_message"; text: string }

// Screenshot captured from tab
{
  type: "screenshot"
  data: string      // base64-encoded PNG
  width: number
  height: number
  url: string       // current tab URL at time of capture
}

// User signals completion of a Confirm or Handoff step (shortcut button)
{ type: "user_done" }

// UI consistency check response (v1.1.0)
{
  type: "ui_sync_response"
  visible_step_label: string | null   // What the progress bar currently shows
  overlay_label: string | null        // What the current overlay label shows (null if no overlay)
}
```

### 5.2 Screenshot Payload

Screenshots are captured via `chrome.tabs.captureVisibleTab(null, { format: "png" })`.

```typescript
interface ScreenshotPayload {
  type: "screenshot"
  data: string      // base64 PNG, WITHOUT the data:image/png;base64, prefix
  width: number     // viewport width in CSS pixels
  height: number    // viewport height in CSS pixels
  url: string       // window.location.href at moment of capture
  timestamp: number // Date.now()
}
```

**Size constraint:** Screenshots should be captured at the default device pixel ratio. Do not upscale. If the base64 string exceeds 3MB, resize to max 1280px width before encoding.

### 5.3 Session State Schema

```python
# In-memory session store: Dict[session_id: str, AgentSession]

@dataclass
class AgentSession:
    session_id: str
    websocket: WebSocket
    state: AgentState
    memory: ConversationMemory     # v1.1.0: explicit memory object
    created_at: float              # time.time()
    last_activity: float           # updated on every message

# Cleanup: sessions inactive for > 600 seconds are purged
SESSION_TTL_SECONDS = 600
```

---

## 6. UI/UX Requirements

### 6.1 Sidebar Panel Layout

```
┌─────────────────────────────────────┐
│ 🇻🇳 Civic Navigator        [●] live │  ← Header bar (fixed)
├─────────────────────────────────────┤
│ Bước 3 / 7                          │  ← Progress bar (shows only during procedure)
│ ████████████░░░░░░░░░░░░            │    step label: "Điền thông tin cá nhân"
│ Điền thông tin cá nhân              │
├─────────────────────────────────────┤
│                                     │
│  [user bubble]                      │  ← Chat feed (scrollable, always visible)
│  Tôi muốn gia hạn hộ chiếu         │
│                                     │
│         [agent bubble]              │
│         Được rồi! Tôi sẽ hướng dẫn │
│         bạn qua 7 bước gia hạn...  │
│                                     │
│         [system bubble]             │
│         ⟳ Đang tìm hiểu quy trình  │
│                                     │
├─────────────────────────────────────┤
│ ┌─────────────────────────────────┐ │  ← Input area (fixed bottom)
│ │ Nhập tin nhắn...                │ │    ALWAYS ENABLED during awaiting_user
│ └─────────────────────────────────┘ │    and executing states
│       [✓ Xong rồi]     [Gửi →]     │  ← "Xong rồi" appears for confirm/handoff steps
└─────────────────────────────────────┘
```

**v1.1.0 change:** The text input field is ALWAYS enabled and available when `session_status` is `awaiting_user` or `executing`. The "Xong rồi" button appears alongside the input (not instead of it) during confirm and handoff steps. Users can always type to communicate with the agent.

**When Handoff is active (replaces only the "Xong rồi" button area, NOT the chat):**

```
├─────────────────────────────────────┤
│  ⚠ Bước bảo mật                    │  ← HandoffScreen component (above input)
│                                     │
│  Vui lòng điền:                     │
│  Số CMND / CCCD của bạn             │
│                                     │
│  Tôi sẽ không xem thông tin này.    │
│                                     │
├─────────────────────────────────────┤
│ ┌─────────────────────────────────┐ │  ← Input still accessible
│ │ Nhập tin nhắn...                │ │
│ └─────────────────────────────────┘ │
│       [✓ Xong rồi]     [Gửi →]     │
└─────────────────────────────────────┘
```

**When Login Handoff is active (full overlay — only exception where chat is hidden):**

```
┌─────────────────────────────────────┐
│         🔒                          │
│                                     │
│  Đăng nhập vào                      │
│  Cổng Dịch vụ công Quốc Gia        │
│                                     │
│  Vui lòng đăng nhập trên trang web. │
│  Tôi sẽ đợi ở đây.                 │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  ✓ Tôi đã đăng nhập         │   │
│  └─────────────────────────────┘   │
│                                     │
│  Tôi không lưu thông tin đăng nhập. │
└─────────────────────────────────────┘
```

### 6.2 Overlay Highlight Specification

```css
/* Injected by content script into portal page */

#civic-nav-overlay-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;   /* CRITICAL: must not block portal interactions */
  z-index: 2147483647;    /* max z-index */
}

.civic-nav-highlight {
  position: absolute;
  border: 2px solid #4ade80;
  border-radius: 4px;
  pointer-events: none;
  animation: civic-nav-pulse 1.5s ease-in-out infinite;
}

.civic-nav-highlight-label {
  position: absolute;
  top: -32px;
  left: 0;
  background: rgba(0, 0, 0, 0.75);
  color: #4ade80;
  font-size: 13px;
  font-family: system-ui, sans-serif;
  padding: 4px 10px;
  border-radius: 4px;
  white-space: nowrap;
  pointer-events: none;
}

@keyframes civic-nav-pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(74, 222, 128, 0.4);
  }
  50% {
    box-shadow: 0 0 0 6px rgba(74, 222, 128, 0);
  }
}
```

**Overlay positioning logic (content script):**

```typescript
function injectOverlay(msg: InjectOverlayMessage): void {
  clearOverlay()

  let rect: DOMRect | null = null

  if (msg.selector) {
    const el = document.querySelector(msg.selector)
    if (el) rect = el.getBoundingClientRect()
  }

  if (!rect && msg.bbox) {
    // bbox is in page coordinates from vision model
    // convert to viewport coordinates
    rect = {
      x: msg.bbox.x - window.scrollX,
      y: msg.bbox.y - window.scrollY,
      width: msg.bbox.width,
      height: msg.bbox.height,
    } as DOMRect
  }

  if (!rect) return  // Cannot locate element — highlight tool decided not to emit

  const container = document.createElement("div")
  container.id = "civic-nav-overlay-container"

  const highlight = document.createElement("div")
  highlight.className = "civic-nav-highlight"
  highlight.style.left = `${rect.x}px`
  highlight.style.top = `${rect.y}px`
  highlight.style.width = `${rect.width}px`
  highlight.style.height = `${rect.height}px`

  const label = document.createElement("div")
  label.className = "civic-nav-highlight-label"
  label.textContent = msg.label

  highlight.appendChild(label)
  container.appendChild(highlight)
  document.body.appendChild(container)
}

function clearOverlay(): void {
  document.getElementById("civic-nav-overlay-container")?.remove()
}
```

### 6.3 Vietnamese Copy — Standard Phrases

These are the fixed Vietnamese strings used across agent messages. Use these exactly — do not let the LLM improvise on system-critical messages.

**Status bar messages (short, shown in status bar only):**

| Key | Vietnamese |
|---|---|
| `status.searching` | Đang tìm hiểu quy trình... |
| `status.planning` | Đang lập kế hoạch hướng dẫn... |
| `status.analyzing` | Đang xem màn hình... |
| `status.verifying` | Đang kiểm tra kết quả... |
| `status.recovering` | Đang điều chỉnh... |
| `status.ready` | Sẵn sàng hỗ trợ |
| `status.highlighting` | Đang tìm phần tử... |

**Login handoff screen (exact copy):**

```
Title    : Đăng nhập vào Cổng Dịch vụ công Quốc Gia
Body     : Vui lòng đăng nhập bằng tài khoản của bạn trên trang web.
           Tôi sẽ tiếp tục hướng dẫn ngay khi bạn đã đăng nhập xong.
Button   : Tôi đã đăng nhập ✓
Footnote : Tôi không thu thập hoặc lưu trữ thông tin đăng nhập của bạn.
```

**Data handoff screen (templated):**

```
Title    : Bước bảo mật
Body     : Vui lòng điền: {field_description}
           Tôi sẽ không xem hoặc lưu thông tin này.
Button   : Xong rồi ✓
```

**Agent greeting:**

```
Xin chào! Tôi là Civic Navigator, trợ lý giúp bạn thực hiện
các thủ tục hành chính trên Cổng Dịch vụ công Quốc Gia.

Bạn muốn làm thủ tục gì hôm nay?
```

**Procedure start:**

```
Tôi sẽ hướng dẫn bạn thực hiện {procedure_name_vi}.
Quy trình gồm {total_steps} bước. Hãy bắt đầu thôi!
```

**Correction acknowledgment (v1.1.0):**

```
Để tôi kiểm tra lại. {corrective_action}
```

**Highlight not found (v1.1.0):**

```
Tôi không thấy phần tử đó rõ ràng trên màn hình. {verbal_description_of_where_to_look}
```

**Completion message:**

```
✓ Hoàn thành! Bạn đã nộp hồ sơ {procedure_name_vi} thành công.

{completion_details}

Nếu bạn cần làm thêm thủ tục khác, hãy cho tôi biết nhé.
```

---

## 7. Non-Functional Requirements

### 7.1 Performance

| Metric | Target |
|---|---|
| Agent first token latency | < 2 seconds after user message |
| Screenshot capture → analysis → first instruction | < 5 seconds |
| WebSocket connection establishment | < 500ms |
| Overlay injection after backend command | < 100ms |
| highlight_tool LLM call latency | < 3 seconds |
| sync_ui round-trip (check + verify) | < 500ms |
| conversation_turn LLM call (full history) | < 3 seconds |

### 7.2 Reliability

- WebSocket must auto-reconnect if connection drops. Session state and conversation memory are retained for 10 minutes on backend.
- If OpenRouter API returns an error (5xx, rate limit), retry up to 2 times with exponential backoff (1s, 3s), then surface Vietnamese error: `"Có sự cố kết nối. Vui lòng thử lại sau ít phút."`
- If Tavily search fails, agent should attempt to proceed with a generic procedure plan based on LLM knowledge alone, and note: `"Tôi không tìm được hướng dẫn cụ thể — tôi sẽ cố gắng dựa trên kiến thức sẵn có."`
- If `highlight_tool` returns `success=False`, the agent must continue and describe the element verbally. It must NOT stall waiting for a highlight.
- If `sync_ui` fails after 2 retries, the agent logs the inconsistency and proceeds — it does not block indefinitely.

### 7.3 Hackathon Scope Constraints

The following are explicitly OUT OF SCOPE for the hackathon build:

- User authentication / accounts for the Civic Navigator app itself
- Persistence of session history across browser restarts
- Support for mobile browsers
- Support for any portal other than dichvucong.gov.vn
- Multi-language support (Vietnamese only)
- Accessibility features (screen reader support, etc.)
- Production deployment / hosting

---

## 8. Privacy & Security Constraints

These are hard constraints. They are not negotiable and must be respected in all implementations.

```
CONSTRAINT P1: The content script MUST NOT read, log, capture in screenshots,
or transmit any value from a form field that is classified as personal data
(see Section 4.7 for field list).

CONSTRAINT P2: Screenshot capture is DISABLED while session_status = "awaiting_login".
The chrome.tabs.captureVisibleTab call must not be invoked in this state.

CONSTRAINT P3: The backend MUST NOT store screenshots to disk or any persistent
storage. Screenshots exist only in memory during active agent processing and are
discarded immediately after the vision model returns its analysis.

CONSTRAINT P4: No user conversation history, screenshots, or session state
is transmitted to any third party other than:
  - OpenRouter API (LLM inference only, for the current turn's messages)
  - Tavily API (search queries only, no user content)

CONSTRAINT P5: OpenRouter API calls for screenshot analysis (highlight_tool and
screenshot_tool) must send ONLY the screenshot image and the analysis prompt.
They must NOT include conversation history containing any user-entered data.

CONSTRAINT P6: The Civic Navigator application does not persist any data
beyond the active browser session. All state is in-memory and lost on
extension reload or backend restart.

CONSTRAINT P7 (v1.1.0): conversation_history stored in AgentState is never
written to disk, never logged by FastAPI, and never transmitted to Tavily.
It is passed to OpenRouter only in the context of the current LLM call.
```

---

## 9. Scope Boundaries

### 9.1 In Scope

- [x] Chrome Extension (Manifest V3) with sidebar panel (chrome.sidePanel)
- [x] React sidebar UI with chat, progress bar, handoff screens
- [x] Always-enabled text input during awaiting_user state
- [x] Content script for overlay injection on dichvucong.gov.vn
- [x] FastAPI backend with WebSocket endpoint
- [x] Conversation-first LangGraph agent with full memory (Section 3.4, 4.3)
- [x] ConversationMemory class with scoped history per session
- [x] OpenRouter integration for LLM text + vision
- [x] Tavily integration for silent procedure search
- [x] Three-tier action model (Inform / Confirm / Handoff)
- [x] Hard Handoff login flow
- [x] Personal data Handoff flow
- [x] Recovery behavior (up to 3 attempts)
- [x] User authority / correction handling (Section 4.4)
- [x] UI consistency sync_ui contract (Section 4.5)
- [x] Independent highlight_tool LLM subsystem (Section 3.7)
- [x] Procedure: gia hạn hộ chiếu (passport renewal) — primary demo scenario
- [x] Procedure: cấp CCCD gắn chip — secondary scenario if time allows
- [x] Vietnamese-only UI

### 9.2 Out of Scope

- [ ] Autonomous clicking / form filling on behalf of user
- [ ] Any portal other than dichvucong.gov.vn
- [ ] English language support
- [ ] User accounts or persistent history
- [ ] Mobile browser support
- [ ] Production deployment
- [ ] Billing / usage tracking
- [ ] Analytics or telemetry

---

## 10. Glossary

| Term | Definition |
|---|---|
| **DVCQG** | Cổng Dịch vụ công Quốc gia — Vietnam's National Public Service Portal at dichvucong.gov.vn |
| **BCA** | Cổng Dịch vụ công Bộ Công an — Ministry of Public Security portal (out of scope for this build) |
| **CCCD** | Căn cước công dân — Vietnamese national identity card |
| **Content script** | JavaScript injected by Chrome Extension into the portal tab's DOM context |
| **Sidebar panel** | The extension's UI rendered in Chrome's native side panel (chrome.sidePanel API) |
| **Action tier** | Classification of each agent action: Inform (auto), Confirm (wait for user), Handoff (user acts alone) |
| **Hard Handoff** | The login flow where the agent completely stops all observation and waits for user to signal completion |
| **OpenRouter** | API gateway at openrouter.ai providing unified access to multiple LLM providers |
| **LangGraph** | Python library for building stateful, graph-structured AI agents |
| **Tavily** | Search API optimized for AI agent use — returns clean, structured web results |
| **Vision model** | The LLM called with a screenshot image to analyze the current state of the portal page |
| **bbox** | Bounding box — {x, y, width, height} coordinates identifying an element's position on screen |
| **session_id** | UUID generated by the extension identifying one user's active guidance session |
| **procedure_steps** | The structured list of ProcedureStep objects built by the agent from tutorial search results |
| **recovery_attempts** | Counter tracking how many times the agent has tried to recover from an unexpected portal state |
| **ConversationMemory** | v1.1.0 — Class managing the scoped conversation history passed to the LLM on every call |
| **memory_context** | v1.1.0 — A concise summary string embedded in the system prompt to ground the LLM on current session state |
| **conversation_turn** | v1.1.0 — The primary LangGraph node; calls the LLM with full history and routes based on intent |
| **highlight_tool** | v1.1.0 — Independent LLM subsystem that looks at a screenshot and decides what to highlight |
| **sync_ui** | v1.1.0 — LangGraph node that verifies chat, highlight, and progress bar are mutually consistent before waiting for user |
| **user authority** | v1.1.0 — The principle that any user message during awaiting_user is processed by the agent and can change agent behavior |
| **tool_call_history** | v1.1.0 — Audit trail of search/screenshot/highlight calls made during the session (debug only, not sent to LLM) |

---

```
END OF DOCUMENT
CNV-SRS-001 v1.1.0
```
