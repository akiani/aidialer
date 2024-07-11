from typing import List, Optional


class CallContext:
    """Store context for the current call."""
    def __init__(self):
        self.stream_sid: Optional[str] = None
        self.call_sid: Optional[str] = None
        self.call_ended: bool = False
        self.user_context: List = []
        self.system_message: str = ""
        self.initial_message: str = ""
        self.start_time: Optional[str] = None
        self.end_time: Optional[str] = None
        self.final_status: Optional[str] = None
        
