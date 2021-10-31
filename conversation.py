import uuid
import logging
from datetime import datetime

class Conversation():
    def __init__(self, owner, command) -> None:
        super().__init__()
        self.conversation_id = uuid.uuid4()
        self.conversation_begin_timestamp = datetime.now()
        self.conversation_active = True
        self.owner = owner
        self.conversation_stage = str()
        self.command = command
        self.conversation_data = dict()
    
    def add_reaction_handler(self, bot_admin, message):
        if self.conversation_stage == '':
            self.conversation_data['emoji_validation_results'] = bot_admin._validate_command_emoji(message)
            self.conversation_stage = 'add_categories'
        if self.conversation_stage == 'add_categories':
            
            logging.info("DEBUG ADD CATEGORIES CONVO FLOW LOGIC")
