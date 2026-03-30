from datetime import datetime
from uuid import uuid4


def create_thread_id() -> str:
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{timestamp}_{str(uuid4())[:8]}"
