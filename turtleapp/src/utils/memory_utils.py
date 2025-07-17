from datetime import datetime
from uuid import UUID, uuid4


def create_thread_id() -> UUID:
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{timestamp}_{str(uuid4())[:8]}"