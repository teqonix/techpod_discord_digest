import uuid

class Conversation():
    def __init__(self, owner, command) -> None:
        super().__init__()
        conversation_id = uuid(4)
        owner = owner
        command = command