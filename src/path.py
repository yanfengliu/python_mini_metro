import uuid


class Path:
    def __init__(self):
        self.id = f"P-{uuid.uuid4()}"

    def __repr__(self) -> str:
        return self.id
