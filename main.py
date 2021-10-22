import discord
import json
import logging
from datetime import datetime

import firestore_client
import config

DISCORD_CLIENT = discord.Client()
LOGGER = logging.getLogger()

CHANNEL_LIST = list()
ADMIN_CHANNEL = None
DB_CLIENT = firestore_client.DigestBotFirestoreClient(gcp_credentials_env_var='GOOGLE_APPLICATION_CREDENTIALS')

def _get_server_channels():
    all_channels_generator = DISCORD_CLIENT.get_all_channels()
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
    
@DISCORD_CLIENT.event
async def on_ready():
    logging.info(f'We have logged in as {DISCORD_CLIENT.user}')

    current_channels = _get_server_channels()

    for channel in current_channels['raw_channels']:
        if channel.name not in config.excluded_channels and channel.type.name == 'text':
            CHANNEL_LIST.append(channel)
            if channel.name == config.bot_admin_channel:
                ADMIN_CHANNEL = channel

    local_server_emoji_metadata = list()
    for emoji in DB_CLIENT.monitored_emoji['emoji_list']:
        # This bot is currently hard-coded to only connect to one Discord Server, hence the [0]:
        for server_emojii in DISCORD_CLIENT.guilds[0].emojis:
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
    for channel in DB_CLIENT.monitored_channels['channels']:
        channel_string = channel_string + " \n • #" + channel

    emoji_string = f'{new_line}{new_line}**Emoji Being Monitored:**'
    for emoji in local_server_emoji_metadata:
        if emoji['id'] != '': emoji_string = emoji_string + ' \n • <:' + emoji['name'] + ':' + emoji['id'] + '> (Category: ' + emoji['category'] + ')' 
        if emoji['id'] == '': emoji_string = emoji_string + " \n • " + emoji['name'] + ' (Category: ' + emoji['category'] + ')' 

    await ADMIN_CHANNEL.send(f'Techpod Discord Digest bot is ready as of '\
        f'{datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC ' \
        f'{new_line}{new_line} {channel_string}'\
        f'{emoji_string}'
    )

    print('Bot Ready.')

@DISCORD_CLIENT.event
async def on_message(message):    
    if message.author == DISCORD_CLIENT.user:
        return

    # Ignore messages in channels not being monitored
    if message.channel.id not in [i.id for i in CHANNEL_LIST]:
        return

    if message.content.startswith('$'):
        # TODO? Might be good to turn this into a helper function
        for admin_role in config.bot_admin_role_names:
            # Ignore any messsage that looks like a bot command if the user does not have a bot admin role:
            if admin_role not in [i.name for i in message.author.roles]:
                return       
        
        if message.content.startswith('$add_channels'):
            # Remove command and hashes from list of channels in command:
            cmd_channels = [i.replace('#','').strip() for i in message.content.split(' ') if i != '$add_channels']
            current_channels = _get_server_channels()
            DB_CLIENT._refresh_configured_channels()
            
            # If a channel that's already being tracked was in the request, remove it:
            new_channels_to_verify = [i for i in cmd_channels if i not in DB_CLIENT.monitored_channels['channels']]
            new_channels_to_monitor = [i for i in new_channels_to_verify if i in current_channels['text_channels']]

            invalid_channels = False
            invalid_channel_list = []
            if len(new_channels_to_verify) != len(new_channels_to_monitor):
                invalid_channels = True
                for channel in cmd_channels:
                    if channel not in current_channels['text_channels']:
                        invalid_channel_list.append(channel)
                logging.warning(f'Add channel command by user {message.author.display_name} contained channels that do not exist. Invalid channels: ```{invalid_channel_list}``` / Added to config DB: ```{new_channels_to_monitor}```')

            try:
                DB_CLIENT.set_channels_to_monitor(new_channels_to_monitor)
                DB_CLIENT._refresh_configured_channels()
                response_message_text = str()
                if invalid_channels:
                    await message.channel.send(f'**Warning:** There were invalid channel entries in your request. You may want to double check and try again. \n _Invalid Channels:_ ```{invalid_channel_list}```')
                if len(new_channels_to_monitor) != 0:
                    response_message_text = f'{message.author.display_name} added these channels to be monitored by the Discord Digest Bot: ```{new_channels_to_monitor}``` \n'
                else: 
                    response_message_text = f'**INFO:** There were no new channels to monitor in your request. \n '
                response_message_text = response_message_text + f'**All channels currently being monitored:** ```{DB_CLIENT.monitored_channels["channels"]}```'
                await message.channel.send(response_message_text)
            except Exception as e:
                logging.error(f'Could not set channels to monitor in backend. Exception: {e}')
                await message.channel.send(f'There was a problem adding your channels to the backend DB. Error logged.')
                await ADMIN_CHANNEL.send(f'There was a problem adding your channels to the backend DB: ```{e}```')

    if message.content.startswith('!test'):
        logging.info('debugging!')
        logging.info('no really I would like to debug')

@DISCORD_CLIENT.event
async def on_raw_reaction_add(payload):
    logging.debug(f"saw a reaction added: {payload}")
    if payload.channel_id in [c.id for c in CHANNEL_LIST]:
        logging.info(f"Reaction {payload.emoji.name} was used on message {payload.message_id} in channel {payload.channel_id} by member {payload.member.name}.")

if __name__ == "__main__":
    logging.basicConfig(level=config.log_level)
    DISCORD_CLIENT.run(config.discord_token)