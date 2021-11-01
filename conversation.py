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
        self.conversation_message_list = list()
    
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
                conversation_complete_text = conversation_complete_text + f"* Reaction: {reaction['discord_output_str']} Category: {reaction['category']}"
            conversation_complete_text = conversation_complete_text + f'\n I\'m currently monitoring these reactions on messages: {[i["discord_output_str"] for i in self.DB_CLIENT.monitored_emoji["emoji_list"]]}'
            await message.channel.send(conversation_complete_text)

    async def remove_reaction_handler(self, message):
        if self.conversation_stage == '':
            self.conversation_data['reactions'] = list()
            self.conversation_stage = 'remove_emoji'
        
        if self.conversation_stage == 'remove_emoji':
            self.conversation_data['emoji_validation_results'] = self.BOT_ADMIN._validate_command_emoji(message)
            if len(self.conversation_data['emoji_validation_results']['tracked_emoji']) > 0:
                current_emoji = self.conversation_data['emoji_validation_results']['tracked_emoji']
                self.DB_CLIENT.remove_emoji_to_monitor(emoji_list=current_emoji)
                await message.channel.send(f'You got it.  I\'m still watching for these reactions: {[i["discord_output_str"] for i in self.DB_CLIENT.monitored_emoji["emoji_list"]]}')
                self.conversation_stage='complete'
            else:
                await message.channel.send(f'Hmm. Your command did not include an emoji already being monitored on this server (which are { [i["discord_output_str"] for i in self.DB_CLIENT.monitored_emoji["emoji_list"]] }). Try re-submitting an emoji to remove (or cancel with a `$cancel` command.)')

    async def add_channel_handler(self, message):
        if self.conversation_stage == '':
            self.conversation_data['channels'] = list()
            self.conversation_stage = 'add_channels'
        
        if self.conversation_stage == 'add_channels':
            self.conversation_data['channel_validation_results'] = self.BOT_ADMIN._validate_command_channels(message,action='add')
            if len(self.conversation_data['channel_validation_results']['valid_cmd_channels']) > 0:
                self.DB_CLIENT.add_channels_to_monitor(channel_list=self.conversation_data['channel_validation_results']['valid_cmd_channels'])
                await message.channel.send(f'Done. I\'m now monitoring these channels: {self.DB_CLIENT.monitored_channels["channels"]}')
                self.conversation_stage = 'complete'
                return
            elif len(self.conversation_data['channel_validation_results']['invalid_channels']) > 0:
                await message.channel.send(f'Sorry, there are channel(s) that seem to be invalid in your command: {self.conversation_data["channel_validation_results"]["invalid_channels"]}.  Try this command again.')
                logging.error(f'User attempted to add an invalid channel - conversation will terminate.')
                self.conversation_stage = 'complete'
            elif len(self.conversation_data['channel_validation_results']['valid_cmd_channels']) == 0:
                await message.channel.send(f'Hmm. There were no new channels to monitor in your request. These channels are now being monitored: {self.DB_CLIENT.monitored_channels["channels"]}')
                self.conversation_stage = 'complete'
            else:
                logging.error(f'Something went wrong when trying to add channels to what the bot monitors.. message that caused the issue: {message}')

    async def remove_channel_handler(self, message):
        if self.conversation_stage == '':
            self.conversation_data['channels'] = list()
            self.conversation_stage = 'remove_channel'
        
        if self.conversation_stage == 'remove_channel':
            self.conversation_data['channel_validation_results'] = self.BOT_ADMIN._validate_command_channels(message,action='remove')
            if len(self.conversation_data['channel_validation_results']['valid_cmd_channels']) > 0:
                self.DB_CLIENT.remove_monitored_channels(channel_list=self.conversation_data['channel_validation_results']['valid_cmd_channels'])
                await message.channel.send(f'You got it.  Channels still being monitored: {[i for i in self.DB_CLIENT.monitored_channels["channels"]]}')
                self.conversation_stage='complete'
            else:
                await message.channel.send(f'Hmm. Your command did not include an channels already being monitored on this server (which are { [i for i in self.DB_CLIENT.monitored_channels["channels"]] }). Try re-submitting an channel to remove (or cancel with a `$cancel` command.)')