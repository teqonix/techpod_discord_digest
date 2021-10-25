import bot_actions
import discord
import json
import logging
import firestore_client
from datetime import datetime

import config

# TODO List:
# - Need to add mocking and unit testing
# - Code review from a real programmer (I have a feeling my classes are a disaster)
# - Add emojii monitoring logic (add/remove)
# - Add query capability & output message + formatting

DB_CLIENT = firestore_client.DigestBotFirestoreClient(gcp_credentials_env_var='GOOGLE_APPLICATION_CREDENTIALS')
BOT_ADMIN = bot_actions.TechPodBotClient(DB_CLIENT)
DISCORD_CLIENT = BOT_ADMIN.DISCORD_CLIENT
LOGGER = logging.getLogger()

@DISCORD_CLIENT.event
async def on_ready():
    logging.info(f'We have logged in as {DISCORD_CLIENT.user}')
    await BOT_ADMIN.initialize_bot()
    print('Bot Ready.')

@DISCORD_CLIENT.event
async def on_message(message):    
    if message.author == DISCORD_CLIENT.user:
        return

    # Ignore messages in channels not being monitored
    if message.channel.id not in [i.id for i in BOT_ADMIN.CHANNEL_LIST]:
        return

    if message.content.startswith('$'):
        # TODO? Might be good to turn this into a helper function
        for admin_role in config.bot_admin_role_names:
            # Ignore any messsage that looks like a bot command if the user does not have a bot admin role:
            if admin_role not in [i.name for i in message.author.roles]:
                return       
        
        if message.content.startswith('$add_channels'):
            await BOT_ADMIN.add_channels(message)

        if message.content.startswith('$remove_channels'):
            await BOT_ADMIN.remove_channels(message)
            
    if message.content.startswith('!test'):
        logging.info('debugging!')
        logging.info('no really I would like to debug')

@DISCORD_CLIENT.event
async def on_raw_reaction_add(payload):
    logging.debug(f"saw a reaction added: {payload}")
    if payload.channel_id in [c.id for c in BOT_ADMIN.CHANNEL_LIST]:
        logging.info(f"Reaction {payload.emoji.name} was used on message {payload.message_id} in channel {payload.channel_id} by member {payload.member.name}.")

if __name__ == "__main__":
    logging.basicConfig(level=config.log_level)
    DISCORD_CLIENT.run(config.discord_token)