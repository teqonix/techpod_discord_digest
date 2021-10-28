import discord
import emoji
import logging
import config

from datetime import datetime

class TechPodBotClient():
    def __init__(self, DB_CLIENT) -> None:
        super().__init__()
        self.DB_CLIENT = DB_CLIENT
        self.ADMIN_CHANNEL = None
        self.CHANNEL_LIST = list()
        self.DISCORD_CLIENT = discord.Client()

    def _get_server_channels(self):
        all_channels_generator = self.DISCORD_CLIENT.get_all_channels()
        raw_all_channels = list()
        voice_channel_names = list()
        text_channel_names = list()    

        for c in all_channels_generator:
            raw_all_channels.append(c)
            if type(c) == discord.channel.VoiceChannel:
                voice_channel_names.append(c.name)
            elif type(c) == discord.channel.TextChannel:
                text_channel_names.append(c.name)

        return {
            'raw_channels': raw_all_channels,
            'text_channels': text_channel_names,
            'voice_channels': voice_channel_names
        }
    
    def _get_server_emoji(self):
        logging.info('DEBUG')
        server_custom_emoji = self.DISCORD_CLIENT.emojis
        return

    def _validate_command_channels(self, message, action):
        """For add/remove channel commands this will check for invalid channels in the request."""
        cmd_channels = [i.replace('#','').strip() for i in message.content.split(' ') if i not in ['$add_channels','$remove_channels']]
        current_channels = self._get_server_channels()
        self.DB_CLIENT._refresh_configured_channels()
        
        verified_cmd_channels = [i for i in cmd_channels if i in current_channels['text_channels']]
        invalid_channel_list = []
        if len(verified_cmd_channels) != len(cmd_channels):
            for channel in cmd_channels:
                if channel not in current_channels['text_channels']:
                    invalid_channel_list.append(channel)
            logging.warning(f'Channel command by user {message.author.display_name} contained channels that do not exist. Invalid channels: ```{invalid_channel_list}``` / Valid channels: ```{verified_cmd_channels}```')
        
        if action == "add":
        # If a channel that's already being tracked was in the request, remove it:
            valid_cmd_channels = [i for i in cmd_channels if i not in self.DB_CLIENT.monitored_channels['channels']]

        if action == 'remove':
            valid_cmd_channels = [i for i in cmd_channels if i in self.DB_CLIENT.monitored_channels['channels']]

        return {
            'valid_channels': valid_cmd_channels,
            'invalid_channels': invalid_channel_list
        }

    def _validate_command_emoji(self, message, action):
        cmd_emoji = [i.replace('#','').strip() for i in message.content.split(' ') if i not in ['$add_reactions','$remove_reactions']]
        server_emoji = self._get_server_emoji()
        invalid_characters = list()
        for (i,character) in enumerate(cmd_emoji):
            try:
                if not emoji.UNICODE_EMOJI_ALIAS_ENGLISH[character]:
                    invalid_characters.append(character)
            except KeyError:
                if character.startswith('<') and character.endswith('>'):
                    pass
                else:
                    invalid_characters.append(character)

        for entry in invalid_characters:
            [cmd_emoji.remove(entry) for x in cmd_emoji if x == character]    
        
        new_reactions = list()
        # TODO: Check DB_CLIENT to see if the sanitized list of reactions from the command are being tracked in the backend DB:
        # for reaction in cmd_emoji:
        #     try:
        #         if emoji.UNICODE_EMOJI_ALIAS_ENGLISH[reaction]:

        #     except KeyError:
        #         pass    

        logging.info(f'Characters found in command after validating UNICODE EMOJI: {cmd_emoji}')


    async def initialize_bot(self):
        current_channels = self._get_server_channels()

        for channel in current_channels['raw_channels']:
            if channel.name not in config.excluded_channels and channel.type.name == 'text':
                self.CHANNEL_LIST.append(channel)
                if channel.name == config.bot_admin_channel:
                    self.ADMIN_CHANNEL = channel

        local_server_emoji_metadata = list()
        for emoji in self.DB_CLIENT.monitored_emoji['emoji_list']:
            # This bot is currently hard-coded to only connect to one Discord Server, hence the [0]:
            for server_emojii in self.DISCORD_CLIENT.guilds[0].emojis:
                if emoji['name'] == server_emojii.name:
                    already_added = 1
                    local_server_emoji_metadata.append({'name': emoji['name'], 'id': str(server_emojii.id), 'category': emoji['category']})
            # Unicode emoji will not exist in the DISCORD_CLIENT listing of emojis, so if we didn't add the emoji being processed then add it now: 
            if already_added == 1:
                already_added = 0
                continue
            else:
                already_added = 0
                local_server_emoji_metadata.append({'name': emoji['name'], 'id': '', 'category': emoji['category']})              
        
        new_line = "\n"
        channel_string = '**Channels Being Monitored:**'
        for channel in self.DB_CLIENT.monitored_channels['channels']:
            channel_string = channel_string + " \n • #" + channel

        emoji_string = f'{new_line}{new_line}**Emoji Being Monitored:**'
        for emoji in local_server_emoji_metadata:
            if emoji['id'] != '': emoji_string = emoji_string + ' \n • <:' + emoji['name'] + ':' + emoji['id'] + '> (Category: ' + emoji['category'] + ')' 
            if emoji['id'] == '': emoji_string = emoji_string + " \n • " + emoji['name'] + ' (Category: ' + emoji['category'] + ')' 

        await self.ADMIN_CHANNEL.send(f'Techpod Discord Digest bot is ready as of '\
            f'{datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC ' \
            f'{new_line}{new_line} {channel_string}'\
            f'{emoji_string}'
        )

    async def add_channels(self, message):
        try:
            channels = self._validate_command_channels(message=message,action='add')
            self.DB_CLIENT.add_channels_to_monitor(channels['valid_channels'])
            self.DB_CLIENT._refresh_configured_channels()
            response_message_text = str()
            if channels['invalid_channels']:
                await message.channel.send(f'**Warning:** There were invalid channel entries in your request. You may want to double check and try again. \n _Invalid Channels:_ ```{channels["invalid_channels"]}```')
            if len(channels['valid_channels']) != 0:
                response_message_text = f'{message.author.display_name} added these channels to be monitored by the Discord Digest Bot: ```{channels["valid_channels"]}``` \n'
            else:
                response_message_text = f'**INFO:** There were no new channels to monitor in your request. \n '
            response_message_text = response_message_text + f'**All channels currently being monitored:** ```{self.DB_CLIENT.monitored_channels["channels"]}```'
            await message.channel.send(response_message_text)

        except Exception as e:
            logging.error(f'Could not set channels to monitor in backend. Exception: {e}')
            await message.channel.send(f'There was a problem adding your channels to the backend DB. Error logged.')
            await self.ADMIN_CHANNEL.send(f'There was a problem adding your channels to the backend DB: ```{e}```.  Please contact your friendly bot admin for help.')

    async def remove_channels(self, message):
        try:
            channels = self._validate_command_channels(message=message,action='remove')
            self.DB_CLIENT.remove_monitored_channels(channels['valid_channels'])
            self.DB_CLIENT._refresh_configured_channels()
            response_message_text = str()
            if channels['invalid_channels']:
                await message.channel.send(f'**Warning:** There were invalid channel entries in your request. You may want to double check and try again. \n _Invalid Channels:_ ```{channels["invalid_channels"]}```')
            if len(channels['valid_channels']) != 0:
                response_message_text = f'{message.author.display_name} removed these channels and will **no longer** be monitored by the Discord Digest Bot: ```{channels["valid_channels"]}``` \n'
            else:
                response_message_text = f'**INFO:** There were no new channels to monitor in your request. \n '
            response_message_text = response_message_text + f'**All channels currently being monitored:** ```{self.DB_CLIENT.monitored_channels["channels"]}```'
            await message.channel.send(response_message_text)
        except Exception as e:
            raise e
    
    async def add_emojis(self, message):
        try:
            emoji = self._validate_command_emoji(message=message,action='add')
        except Exception as e:
            logging.error(f'Exception occurred when trying to add reaction(s) to the list of monitored emoji')
            await self.ADMIN_CHANNEL.send(f'There was a problem adding your channels to the backend DB: ```{e}```.  Please contact your friendly bot admin for help.')