from discord.file import File
from google.cloud import firestore
from discord import message
from discord import emoji
from discord import PartialEmoji
from datetime import datetime
from datetime import timedelta
import os
import logging
import config

class DigestBotFirestoreClient():
    def __init__(self, gcp_credentials_env_var) -> None:
        super().__init__()
        credentials = os.getenv(gcp_credentials_env_var)
        if credentials is None or credentials.strip() == "":
            logging.error(f"Could not find env var with GCP credentals - cannot log into Firestore.")
            raise Exception
        self.get_digest_firestore_db()

    def _get_doc_data(self, collection_ref, firestore_doc_name):
        """
        This is a helper function to try and fetch a single doc and throw an error if it does not actually exist.
        If the doc does exist, then return a Python dict() with the data stored in the doc.         
        """
        test_doc_ref = collection_ref.document(firestore_doc_name).get()
        if test_doc_ref.exists:
            doc_data = test_doc_ref.to_dict()
            return doc_data
        else:
            logging.error(f'Could not find firestore doc `{firestore_doc_name}` in collection {collection_ref.id}')
            raise FileNotFoundError # I'm using this Base Exception class because I'm too lazy to define custom ones right now

    def _validate_reaction_schema(self,reaction_to_validate):
        try:
            one = reaction_to_validate['category']
            two = reaction_to_validate['name']
            three = reaction_to_validate['id']
            four = reaction_to_validate['discord_output_str']
        except KeyError:
            logging.error(f'Unable to validate {reaction_to_validate} as a reaction to add to the backend DB!')
            raise Exception
        return

    def _refresh_configured_channels(self):
        try:
            self.monitored_channels = self._get_doc_data(
                collection_ref=self.admin_collection,
                firestore_doc_name=config.monitored_channels_doc_name
            )        
        except FileNotFoundError:
            logging.warning(f'It looks like the document that tracks which channels the bot monitors is missing!  Creating an empty one..' )
            self.admin_collection.document(config.monitored_channels_doc_name).set({'channels': []})
            self.monitored_channels = self._get_doc_data(
                collection_ref=self.admin_collection,
                firestore_doc_name=config.monitored_channels_doc_name
            )
            pass

    def _refresh_configured_emoji(self):
        try:
            self.monitored_emoji = self._get_doc_data(
                collection_ref=self.admin_collection,
                firestore_doc_name=config.monitored_emoji_doc_name
            )
        except FileNotFoundError:
            logging.warning(f'It looks like the document that tracks which emoji the bot monitors is missing!  Creating an empty one..' )
            self.admin_collection.document(config.monitored_emoji_doc_name).set({'emoji_list': []})
            self.monitored_emoji = self._get_doc_data(
                collection_ref=self.admin_collection,
                firestore_doc_name=config.monitored_emoji_doc_name
            )
            pass
            

    # The discord library returns a custom Class if a custom emoji is used.  If not, it just returns a string.
    def _handle_custom_emoji(self, emoji_to_parse):
        return_dict = dict()
        if type(emoji_to_parse) == emoji.Emoji: 
            return_dict = {
                'custom_emoji': True,
                'emoji_id': str(emoji_to_parse.id),
                'emoji_name': emoji_to_parse.name,
                'emoji_bot_text': str(emoji_to_parse),
                'external_server_emoji': False
            }
            return return_dict
        elif type(emoji_to_parse) == PartialEmoji and emoji_to_parse.id is not None:
            return_dict = {
                'custom_emoji': True,
                'emoji_id': str(emoji_to_parse.id),
                'emoji_name': emoji_to_parse.name,
                'emoji_bot_text': str(emoji_to_parse),
                'external_server_emoji': True
            }
            return return_dict            
        elif type(emoji_to_parse) == str:
            return_dict = {
                'emoji_name': emoji_to_parse,
                'emoji_bot_text': str(emoji_to_parse)
            }
            return return_dict
        else:
            logging.error(f'Attempted to handle an emoji for storing in the backend with an unknown type.  Type was: {type(emoji_to_parse)} with value {str(emoji_to_parse)}')
            raise Exception

    def get_digest_firestore_db(self):
        self.db = firestore.Client(project=config.gcp_project_id)
        self.admin_collection = self.db.collection(config.firestore_admin_collection)
        self.storage_collection = self.db.collection(config.firestore_storage_collection)
        self.message_collection = self.db.collection(f'{config.firestore_storage_collection}/{config.message_store_doc_name}/{config.message_store_reaction_collection_name}')

        try:
            self._refresh_configured_emoji()
            # Init the emoji tracking db entry if it doesn't exist:
            if self.monitored_emoji == {}:
                self.admin_collection.document(config.monitored_emoji_doc_name).set({'emoji_list': []}, merge=True)
                self._refresh_configured_emoji()
            self._refresh_configured_channels()
            # Init the channel tracking db entry if it doesn't exist:
            if self.monitored_channels == {}:
                self.admin_collection.document(config.monitored_channels_doc_name).set({'channels': []}, merge=True)
                self._refresh_configured_channels()
        except Exception as e:
            logging.critical(f'Could not find bot config Firestore docs.')
            raise e

    def add_channels_to_monitor(self, channel_list):
        all_channels_to_monitor = list()
        for channel in self.monitored_channels['channels']:
            all_channels_to_monitor.append(channel)
        for new_channel in channel_list:
            all_channels_to_monitor.append(new_channel)
        self.admin_collection.document(config.monitored_channels_doc_name).set({'channels': all_channels_to_monitor}, merge=True)
        self._refresh_configured_channels()

    def remove_monitored_channels(self, channel_list):
        all_channels_to_monitor = list()
        for channel in self.monitored_channels['channels']:
            all_channels_to_monitor.append(channel)
        for channel_to_remove in channel_list:
            all_channels_to_monitor.remove(channel_to_remove)
        self.admin_collection.document(config.monitored_channels_doc_name).set({'channels': all_channels_to_monitor}, merge=True)
        self._refresh_configured_channels()

    def add_emoji_to_monitor(self, emoji_list):
        all_emoji_to_monitor = list()
        for emoji in self.monitored_emoji['emoji_list']:
            all_emoji_to_monitor.append(emoji)
        for emoji_to_add in emoji_list:
            self._validate_reaction_schema(emoji_to_add)
            all_emoji_to_monitor.append(emoji_to_add)
        self.admin_collection.document(config.monitored_emoji_doc_name).set({'emoji_list': all_emoji_to_monitor}, merge=True)
        self._refresh_configured_emoji()
 
    def remove_emoji_to_monitor(self, emoji_list):
        all_emoji_to_monitor = list()
        emoji_to_remove = list()
        for emoji in self.monitored_emoji['emoji_list']:
            all_emoji_to_monitor.append(emoji)
        for emoji in emoji_list:
            for (i,current_emoji) in enumerate(all_emoji_to_monitor):
                if emoji['discord_output_str'] == current_emoji['discord_output_str']:
                    emoji_to_remove.append(emoji)
                    all_emoji_to_monitor.pop(i)

        self.admin_collection.document(config.monitored_emoji_doc_name).set({'emoji_list': all_emoji_to_monitor}, merge=True)
        self._refresh_configured_emoji()
    
    def store_raw_message(self, fetched_message):
        if type(fetched_message) != message.Message:
            logging.exception(f'The message you submitted to be stored in the backend DB needs to be a discord.message.Message class. Yours was a {type(fetched_message)}.') 
            raise Exception
        else:
            db_document_id = str(fetched_message.guild.id) + '.' + str(fetched_message.channel.id) + '.' + str(fetched_message.id)
            
            message_data = {
                'clean_content': fetched_message.clean_content,
                'content': fetched_message.content,
                'created_at_str': fetched_message.created_at.isoformat(),
                'created_at_datetime': fetched_message.created_at,
                'message_id': str(fetched_message.id),
                'channel_id': str(fetched_message.channel.id),
                'channel_name': fetched_message.channel.name,
                'channel_guild_id': str(fetched_message.channel.guild.id),
                'reactions': [
                    {
                        'count': i.count,
                        'emoji': self._handle_custom_emoji(emoji_to_parse=i.emoji)
                     } for i in fetched_message.reactions
                ],
                'message_url': fetched_message.jump_url,
                'author': {
                    'author_id': str(fetched_message.author.id),
                    'display_name': fetched_message.author.display_name,
                    'name': fetched_message.author.name
                }
            }
            self.message_collection.document(db_document_id).set(message_data, merge=True)
        
    def get_reacted_messages_for_timespan(self, query_begin=(datetime.today() - timedelta(days=config.default_query_days)), query_end=(datetime.today() + timedelta(days=1))):
        filtered_messages_query = self.message_collection.where(config.message_created_at_field, u'>=', query_begin).where(config.message_created_at_field, u'<=', query_end)
        filtered_messages_generator = filtered_messages_query.stream()
        filtered_messages = [i.get('') for i in filtered_messages_generator]
        logging.info(f'Ran a digest query for dates starting {query_begin} and {query_end}.')
        return filtered_messages