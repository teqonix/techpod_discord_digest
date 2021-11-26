import discord
import emoji
import logging

from google.cloud.firestore_v1.types import query
import config
import json

from datetime import datetime

class TechPodBotClient():
    def __init__(self, DB_CLIENT) -> None:
        super().__init__()
        self.DB_CLIENT = DB_CLIENT
        self.ADMIN_CHANNEL = None
        self.CHANNEL_LIST = list()

        enabled_intents = discord.Intents.default()
        enabled_intents.members = True
        self.DISCORD_CLIENT = discord.Client(intents=enabled_intents)

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
        cmd_channels = [i.replace('#','').strip() for i in message.content.split(' ') if i not in ['$add_channels','$remove_channels',""]]
        current_channels = self._get_server_channels()
        self.DB_CLIENT._refresh_configured_channels()
        
        cmd_channels_to_remove = list()
        for (i,channel) in enumerate(cmd_channels):
            if channel.find('<') > -1 or channel.find('>') > -1:
                for server_channel in current_channels['raw_channels']:
                    if str(server_channel.id) == channel.strip('<>'):
                        cmd_channels_to_remove.append(i)
                        cmd_channels.append(server_channel.name)

        verified_cmd_channels = [i for (n,i) in enumerate(cmd_channels) if i in current_channels['text_channels'] and n not in cmd_channels_to_remove]

        invalid_channel_list = []
        if len(verified_cmd_channels) != len(cmd_channels):
            for channel in cmd_channels:
                if channel.find('<') > -1 and channel.find('>') > -1:
                    continue
                if channel not in current_channels['text_channels']:
                    invalid_channel_list.append(channel)
            logging.warning(f'Channel command by user {message.author.display_name} contained channels that do not exist. Invalid channels: ```{invalid_channel_list}``` / Valid channels: ```{verified_cmd_channels}```')
        
        if action == "add":
        # If a channel that's already being tracked was in the request, remove it:
            valid_cmd_channels = [i for i in verified_cmd_channels if i not in self.DB_CLIENT.monitored_channels['channels']]

        if action == 'remove':
            valid_cmd_channels = [i for i in verified_cmd_channels if i in self.DB_CLIENT.monitored_channels['channels']]

        return {
            'valid_cmd_channels': valid_cmd_channels,
            'valid_channels': self.DB_CLIENT.monitored_channels['channels'],
            'invalid_channels': invalid_channel_list
        }

    def _validate_command_emoji(self, message, message_emoji_limit=1):
        raw_emoji = [i.replace('#','').strip() for i in message.content.split(' ') if i not in ['$add_reactions','$remove_reactions']]
        cmd_emoji = [i for (n,i) in enumerate(raw_emoji) if n in range(0,message_emoji_limit)]
        
        server_emoji = self._get_server_emoji()
        invalid_characters = list()

        emoji_validation_results = {
            'tracked_emoji': list(),
            'new_emoji': list(),
            'invalid_cmd_arguments': list()
        }

        for (i,character) in enumerate(cmd_emoji):
            try:
                if not emoji.UNICODE_EMOJI_ALIAS_ENGLISH[character]:
                    emoji_validation_results['invalid_cmd_arguments'].append(character)
            except KeyError:
                if character.startswith('<') and character.endswith('>'): # Discord parses custom emoji into machine-readable <:emoji_name:emoji_id> 
                    pass
                else:
                    emoji_validation_results['invalid_cmd_arguments'].append(character)

        for entry in emoji_validation_results['invalid_cmd_arguments']:
            [cmd_emoji.remove(entry) for x in cmd_emoji if x == character]    
        
        # TODO: Check DB_CLIENT to see if the sanitized list of reactions from the command are being tracked in the backend DB:
        for reaction in cmd_emoji:
            try:
                if emoji.UNICODE_EMOJI_ALIAS_ENGLISH[reaction]:
                    for tracked_emoji in self.DB_CLIENT.monitored_emoji['emoji_list']:
                        if reaction == tracked_emoji['name']:
                            emoji_validation_results['tracked_emoji'].append(tracked_emoji)
            except KeyError:
                for tracked_emoji in self.DB_CLIENT.monitored_emoji['emoji_list']:
                    custom_reaction = reaction.strip('<').strip('>').split(':')
                    if custom_reaction[1] == tracked_emoji['name']:
                        emoji_validation_results['tracked_emoji'].append(tracked_emoji)
        
        [emoji_validation_results['new_emoji'].append(i) for i in cmd_emoji if i not in emoji_validation_results['tracked_emoji'] and i not in emoji_validation_results['invalid_cmd_arguments']]
        return emoji_validation_results

    def _get_bot_status_text(self):
        local_server_emoji_metadata = list()
        for emoji in self.DB_CLIENT.monitored_emoji['emoji_list']:
            # This bot is currently hard-coded to only connect to one Discord Server, hence the [0]:
            already_added = 0
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
        return {
            'emoji_status': emoji_string,
            'channel_status': channel_string
        }

    def _get_emoji_category(self, discord_emoji_text):
        for emoji in self.DB_CLIENT.monitored_emoji['emoji_list']:
            if emoji['discord_output_str'] == discord_emoji_text:
                return {
                    'category': emoji['category'],
                    'discord_output_str': emoji['discord_output_str']
                }
            else:
                continue
        return {
                    'category': 'UNKNOWN / EXPIRED CATEGORY',
                    'discord_output_str': '❓❓❓'
            }

    def get_channel_reference(self,channel_id):
        found_channel = [i for i in self.CHANNEL_LIST if i.id == channel_id]
        if len(found_channel) == 0:
            logging.warning(f'Could not find channel with ID {channel_id} in the list of channels tracked by DISCORD_CLIENT.  Known channels: {self.CHANNEL_LIST}')
            return 'NOT_FOUND'
        else:
            return found_channel[0]

    def determine_if_custom_emoji(self, reaction):
        try:
            if emoji.UNICODE_EMOJI_ALIAS_ENGLISH[reaction]:
                return 'normal'
        except KeyError:
            if '<' in reaction and '>' in reaction and ':' in reaction:
                return 'custom'

    async def initialize_bot(self):
        current_channels = self._get_server_channels()

        for channel in current_channels['raw_channels']:
            if channel.name not in config.excluded_channels and channel.type.name == 'text':
                self.CHANNEL_LIST.append(channel)
                if channel.name == config.bot_admin_channel:
                    self.ADMIN_CHANNEL = channel

        new_line = '\n'
        current_status = self._get_bot_status_text()

        await self.ADMIN_CHANNEL.send(f'Techpod Discord Digest bot is ready as of '\
            f'{datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC ' \
            f'{new_line}{new_line} {current_status["channel_status"]}'\
            f'{current_status["emoji_status"]}'
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

    async def run_digest_query(self, message):
        # TODO:
        # - Add parsing for begin / end dates
        # - Split messages apart if too big to stuff into a single message
        # - Create a fancy HTML page and store / serve it in a GCS bucket as the report output?
        # - Data structures in this (well, basically everwhere) are a mess; likely shouldn't even need the msg_categories_dedup variable
        digest_messages = self.DB_CLIENT.get_reacted_messages_for_timespan()
        messages_by_category = dict()
        msg_categories = list() 
        await message.channel.send(f'**Community Activity Digest for the past {config.default_query_days} days:** \n --------------------------------------------------')
        for msg in digest_messages:
            [msg_categories.append(self._get_emoji_category(i['emoji']['emoji_bot_text'])) for i in msg['reactions']]

        msg_categories_dedup = list()
        for category in msg_categories:
            if category in msg_categories_dedup:
                continue
            else:
                msg_categories_dedup.append(category)

        for msg in digest_messages:
            for category in msg_categories_dedup:
                try: 
                    for reaction in msg['reactions']:
                        if reaction['emoji']['emoji_bot_text'] == category['discord_output_str']:
                            messages_by_category[(category['category'])].append(msg)
                        else:
                            continue
                except KeyError:
                    messages_by_category[(category['category'])] = list()
                    messages_by_category[(category['category'])].append(msg)
                except TypeError:
                    await message.channel.send(f'TypeError executing your query!  ..What did you do? (See logs for debug details)')
                    logging.error(f'Problem with processing search query due to a TypeError.  Dumping vars..  msg: {msg} | category: {category}')

        for category in messages_by_category:
            category_emoji = [i for i in msg_categories_dedup if i['category'] == category]
            category_text = f'\n\n **--{category_emoji[0]["discord_output_str"]}-- {category} --{category_emoji[0]["discord_output_str"]}--** \n'
            await message.channel.send(category_text)
            message_text = ''
            for msg in messages_by_category[category]:
                message_text = f'*At {msg["created_at_str"].split(".")[0]} UTC, {msg["author"]["display_name"]} wrote:*```{msg["clean_content"]}``` Context: {msg["message_url"]} \n\n'
            if len(category_text) >= 1900:
                logging.warning(f'Query response message was truncated before being sent to Discord. Full message: {category_text}')
                message_text = message_text[0:1900]
                message_text = message_text + '\n\n **Sorry, this message was too big for Discord! Category report truncated.**'
            await message.channel.send(message_text)
            await message.channel.send(category_text)
            del category_text
        return