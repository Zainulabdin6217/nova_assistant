from typing import TypedDict, Optional


class NovaState(TypedDict):
    raw_input: str           # what the user typed or said
    intent: str               # classified intent name
    args: Optional[str]       # extracted argument (search query, file name, note content...)
    is_chat: bool             # True when the LLM decided this is conversation, not a command
    needs_confirm: bool       # does this action need a Yes/No dialog?
    confirmed: Optional[bool] # None = not asked yet, True = user said yes, False = user said no
    skip_classify: bool       # True on the second pass after a confirmation dialog (avoids re-calling the LLM)
    response: str              # the final text response to show + speak
    success: bool              # did the action succeed?
