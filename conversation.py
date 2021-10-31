import uuid
import logging
from datetime import datetime

class Conversation():
    def __init__(self, owner, command, db_client, bot_admin) -> None:
        super().__init__()
        self.conversation_id = uuid.uuid4()
        self.conversation_begin_timestamp = datetime.now()
        self.conversation_active = True
        self.owner = owner
        self.conversation_stage = str()
        self.command = command
        self.conversation_data = dict()
        self.DB_CLIENT = db_client
        self.BOT_ADMIN = bot_admin
    
    async def add_reaction_handler(self, message):
        if self.conversation_stage == '':
            self.conversation_data['reactions'] = list()
            self.conversation_stage = 'add_emoji'
        
        if self.conversation_stage == 'add_emoji':
            self.conversation_data['emoji_validation_results'] = self.BOT_ADMIN._validate_command_emoji(message)
            if len(self.conversation_data['emoji_validation_results']['tracked_emoji']) > 0:
                current_emoji = [i['discord_output_str'] for i in self.DB_CLIENT.monitored_emoji['emoji_list']]
                await message.channel.send(f'It looks like one of those reactions is already being tracked along with these others: {current_emoji}. Please re-submit your request without emoji already being monitored. 🙂')
                return
            elif len(self.conversation_data['emoji_validation_results']['invalid_cmd_arguments']) > 0:
                await message.channel.send(f'Sorry, your reaction seems to be invalid.  Did you use a Discord server emoji or Unicode emoji character?  Try this command again.')
                logging.error(f'User attempted to add a non-emoji reaction - conversation will terminate.')
                self.conversation_stage = 'complete'
            elif len(self.conversation_data['emoji_validation_results']['new_emoji']) > 0:
                # DB_CLIENT.add_emoji_to_monitor(convo.conversation_data['emoji_validation_results']['new_emoji'])
                for reaction in self.conversation_data['emoji_validation_results']['new_emoji']:
                    await message.channel.send(f"Got it! What category do you want to assign to {reaction}?")
                    self.conversation_data['reactions'].append(reaction)
                    self.conversation_stage = 'add_categories'
            else:
                logging.error(f'Something went wrong when trying to add reactions to what the bot monitors..')

        elif self.conversation_stage == 'add_categories':
            reactions_to_add_to_db = list()
            categories = message.content.strip().split(' ')
            self.conversation_data['categories'] = categories
            
            if len(self.conversation_data['reactions']) != len(categories):
                await message.channel.send(f'Looks like you had a mismatch between number of reactions and categories. Can you give me {len(self.conversation_data["reactions"])} instead?  (Reactions: {self.conversation_data["reactions"]} / Categories: {categories})')
                return

            for (i,reaction) in enumerate(self.conversation_data['reactions']):
                if self.BOT_ADMIN.determine_if_custom_emoji(reaction=reaction) == 'normal':
                    reactions_to_add_to_db.append({'name': reaction, 'category': categories[i], 'id': '', 'discord_output_str': reaction})
                elif self.BOT_ADMIN.determine_if_custom_emoji(reaction=reaction) == 'custom':
                    custom_reaction = reaction.strip('<>').split(':')
                    reactions_to_add_to_db.append({'name': custom_reaction[1], 'category': categories[i], 'id': custom_reaction[2], 'discord_output_str': reaction})
            self.DB_CLIENT.add_emoji_to_monitor(reactions_to_add_to_db)
            self.conversation_stage = 'complete'

            conversation_complete_text = f'Awesome.  Added the following reactions and categories to monitor: \n'
            for reaction in reactions_to_add_to_db:
                conversation_complete_text = conversation_complete_text + f"* Reaction: {reaction['name']} Category: {reaction['category']}"
            await message.channel.send(conversation_complete_text)
            logging.info("DEBUG ADD CATEGORIES CONVO FLOW LOGIC")
