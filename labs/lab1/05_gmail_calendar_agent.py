"""
Lab 5 (Bonus) — Gmail + Google Calendar agent (Manual Tool Calling)
=============================================
Same manual agent loop as 03_interactive_agent.py, but the tools now
call real Google APIs instead of toy functions: the model can read
your Gmail inbox and read/create Google Calendar events.

Available tools: list_todays_emails, list_todays_events,
create_calendar_event, get_current_datetime
This reuses the same ideas as Lab 3:
  - Conditional execution (we don't blindly execute everything)
  - Custom business logic (reject invalid time/date input)
  - Tool filtering (ignore calls to unknown tools)
  - Custom error handling (Google API errors are caught and reported,
    not left to crash the loop)

Setup required before running this file — see GOOGLE_SETUP.md.

Interactive usage:
    python 05_gmail_calendar_agent.py
"""

import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from pydantic import BaseModel, ValidationError, field_validator

load_dotenv()

# USE_HUGGINGFACE=1 in .env switches from local Ollama to the
# HuggingFace Inference API — useful if your machine is underpowered
# for running a local model.
USE_HUGGINGFACE = os.getenv("USE_HUGGINGFACE", "0") == "1"

# Local Ollama model name (change this if you pulled a different one)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


def get_llm():
    """Builds and returns the LLM object for the selected path."""
    if USE_HUGGINGFACE:
        from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

        # HuggingFaceEndpoint calls the Inference API over the network —
        # requires a valid HUGGINGFACEHUB_API_TOKEN in .env
        endpoint = HuggingFaceEndpoint(
            repo_id="Qwen/Qwen2.5-7B-Instruct",
            task="text-generation",
            max_new_tokens=256,
            temperature=0,
        )
        return ChatHuggingFace(llm=endpoint)

    # Default path: a local model via Ollama — no internet required
    # after the model is pulled, and no API cost.
    from langchain_ollama import ChatOllama

    return ChatOllama(model=OLLAMA_MODEL, temperature=0)


SYSTEM_PROMPT = (
    "You are a helpful assistant with access to tools: list_todays_emails, "
    "list_todays_events, create_calendar_event, and get_current_datetime. "
    "Use a tool whenever the question needs real Gmail/Calendar data or "
    "the current date/time. Otherwise answer directly."
)


# =============================================================
# Google authentication
# =============================================================
# Gmail is read-only (this lab only summarizes emails, never sends or
# deletes them). Calendar is read/write (needed to create events).
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")

_gmail_service_cache = None
_calendar_service_cache = None


def get_google_creds() -> Credentials:
    """Loads cached OAuth2 credentials from token.json, or runs the
    one-time browser consent flow using credentials.json. See
    GOOGLE_SETUP.md for how to obtain credentials.json."""
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(
                    "credentials.json not found in session2/labs/. Follow "
                    "GOOGLE_SETUP.md to download it from Google Cloud Console "
                    "and place it in this folder."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return creds


def _gmail_service():
    global _gmail_service_cache
    if _gmail_service_cache is None:
        _gmail_service_cache = build("gmail", "v1", credentials=get_google_creds())
    return _gmail_service_cache


def _calendar_service():
    global _calendar_service_cache
    if _calendar_service_cache is None:
        _calendar_service_cache = build("calendar", "v3", credentials=get_google_creds())
    return _calendar_service_cache


# =============================================================
# Tools
# =============================================================
@tool(parse_docstring=True)
def get_current_datetime() -> str:
    """Get the current local date and time.

    Returns:
        A string formatted as "YYYY-MM-DD HH:MM:SS (Weekday)", e.g.
        "2026-07-12 14:30:05 (Sunday)".
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)")


@tool(parse_docstring=True)
def list_todays_emails(max_results: int = 10) -> str:
    """List today's Gmail messages for the authenticated account.

    Args:
        max_results: Maximum number of emails to fetch, most recent
            first (default 10).

    Returns:
        One line per email formatted as "- From: <sender> | Subject:
        <subject> | <snippet>", newline-separated. Returns "No emails
        found for today." if the inbox has nothing today, or a string
        starting with "Gmail API error: " if the API call fails.
    """
    service = _gmail_service()
    today_str = datetime.now().strftime("%Y/%m/%d")
    try:
        resp = (
            service.users()
            .messages()
            .list(userId="me", q=f"after:{today_str}", maxResults=max_results)
            .execute()
        )
    except HttpError as e:
        return f"Gmail API error: {e}"

    message_ids = resp.get("messages", [])
    if not message_ids:
        return "No emails found for today."

    lines = []
    for m in message_ids:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=m["id"], format="metadata", metadataHeaders=["From", "Subject"])
            .execute()
        )
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        sender = headers.get("From", "(unknown sender)")
        subject = headers.get("Subject", "(no subject)")
        snippet = msg.get("snippet", "")
        lines.append(f"- From: {sender} | Subject: {subject} | {snippet}")
    return "\n".join(lines)


@tool(parse_docstring=True)
def list_todays_events() -> str:
    """List today's events on the primary Google Calendar.

    Returns:
        One line per event formatted as "- <start time>: <title>",
        newline-separated. Returns "No events scheduled for today." if
        the calendar is empty, or a string starting with "Calendar API
        error: " if the API call fails.
    """
    service = _calendar_service()
    start_of_day = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    try:
        resp = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start_of_day.isoformat(),
                timeMax=end_of_day.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
    except HttpError as e:
        return f"Calendar API error: {e}"

    events = resp.get("items", [])
    if not events:
        return "No events scheduled for today."

    lines = []
    for e in events:
        start = e["start"].get("dateTime", e["start"].get("date"))
        lines.append(f"- {start}: {e.get('summary', '(no title)')}")
    return "\n".join(lines)


@tool(parse_docstring=True)
def create_calendar_event(summary: str, date: str, time: str, duration_minutes: int = 60) -> str:
    """Create a new event on the primary Google Calendar.

    Args:
        summary: Event title, e.g. "Team sync".
        date: The event date as "YYYY-MM-DD", or the literal word "today".
        time: 24-hour start time as "HH:MM", e.g. "20:00" for 8:00 PM.
        duration_minutes: Meeting length in minutes (default 60).

    Returns:
        A confirmation string with the event title, date, time, duration,
        and a link to the created event. On failure (invalid date/time
        format or a Calendar API error) returns a string starting with
        "Error: " or "Calendar API error: ".
    """
    if date.strip().lower() == "today":
        event_date = datetime.now().date()
    else:
        try:
            event_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return "Error: date must be 'YYYY-MM-DD' or 'today'."

    try:
        hour, minute = map(int, time.split(":"))
        start_dt = datetime.combine(event_date, datetime.min.time()).replace(hour=hour, minute=minute)
    except ValueError:
        return "Error: time must be in 24-hour 'HH:MM' format, e.g. '20:00'."

    start_dt = start_dt.astimezone()
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    service = _calendar_service()
    body = {
        "summary": summary,
        "start": {"dateTime": start_dt.isoformat()},
        "end": {"dateTime": end_dt.isoformat()},
    }
    try:
        created = service.events().insert(calendarId="primary", body=body).execute()
    except HttpError as e:
        return f"Calendar API error: {e}"
    return f"Event created: '{summary}' on {event_date} at {time} ({duration_minutes} min). Link: {created.get('htmlLink')}"


TOOLS = [list_todays_emails, list_todays_events, create_calendar_event, get_current_datetime]
TOOL_REGISTRY = {t.name: t for t in TOOLS}


# =============================================================
# Manual Tool Calling: validation before execution
# =============================================================
class CreateEventArgs(BaseModel):
    summary: str
    date: str
    time: str
    duration_minutes: int = 60

    @field_validator("time")
    @classmethod
    def valid_time_format(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError("time must be 24-hour 'HH:MM', e.g. '20:00' for 8:00 PM")
        return v

    @field_validator("duration_minutes")
    @classmethod
    def positive_duration(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("duration_minutes must be a positive number")
        return v


def validate_tool_call(call: dict) -> str | None:
    """Returns an error message if the call is not acceptable, or None if it's valid."""
    name = call["name"]

    # Tool filtering: unknown tool -> reject instead of executing blindly
    if name not in TOOL_REGISTRY:
        return f"Tool '{name}' is not available. Known tools: {list(TOOL_REGISTRY)}"

    # Custom validation specific to the calendar-creation tool
    if name == "create_calendar_event":
        try:
            CreateEventArgs(**call["args"])
        except ValidationError as e:
            return f"Invalid event arguments: {e}"

    return None


def execute_tool_call(call: dict) -> str:
    """Actually executes the tool once it has passed validation."""
    selected_tool = TOOL_REGISTRY[call["name"]]
    try:
        return str(selected_tool.invoke(call["args"]))
    except Exception as e:
        # Custom error handling: don't crash the loop, return an error
        # message to the model instead.
        return f"Tool execution error: {e}"


# =============================================================
# Agent loop
# =============================================================
def run_agent(llm_with_tools, user_question: str, history: list, max_steps: int = 4) -> str:
    messages = history + [HumanMessage(content=user_question)]

    for step in range(max_steps):
        ai_message: AIMessage = llm_with_tools.invoke(messages)
        messages.append(ai_message)

        if not ai_message.tool_calls:
            # No tool request -> this is the final answer
            history.extend(messages[len(history):])
            return ai_message.content

        for call in ai_message.tool_calls:
            error = validate_tool_call(call)
            if error:
                print(f"  [rejected] {call['name']}({call['args']}) -> {error}")
                result = error
            else:
                result = execute_tool_call(call)
                print(f"  [executed] {call['name']}({call['args']}) -> {result}")
            messages.append(ToolMessage(content=result, tool_call_id=call["id"]))

    history.extend(messages[len(history):])
    return "(reached the maximum number of steps — the answer may be incomplete)"


def interactive_loop():
    try:
        get_google_creds()
    except FileNotFoundError as e:
        print(f"Setup incomplete: {e}")
        return

    llm = get_llm()
    llm_with_tools = llm.bind_tools(TOOLS)
    history = [SystemMessage(content=SYSTEM_PROMPT)]

    print("=" * 60)
    print("📬 Lab 5 — Gmail + Calendar agent")
    print("Try, for example:")
    print('  - "Give me a summary of today\'s emails"')
    print('  - "What meetings do I have today?"')
    print('  - "Create a meeting called Team Sync today at 8:00 PM"')
    print('Type "exit" or "quit" to leave.')
    print("=" * 60)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break
        if not user_input:
            continue

        answer = run_agent(llm_with_tools, user_input, history)
        print(f"Assistant: {answer}")


if __name__ == "__main__":
    interactive_loop()
