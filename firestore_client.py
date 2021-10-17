from google.cloud import firestore
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
            raise Exception

    def get_digest_firestore_db(self):
        self.db = firestore.Client(project=config.gcp_project_id)
        self.admin_collection = self.db.collection(config.firestore_admin_collection)
        self.storage_collection = self.db.collection(config.firestore_storage_collection)

        try:
            self.monitored_emoji = self._get_doc_data(
                collection_ref=self.admin_collection,
                firestore_doc_name=config.monitored_emoji_doc_name
            )
            self.monitored_channels = self._get_doc_data(
                collection_ref=self.admin_collection,
                firestore_doc_name=config.monitored_channels_doc_name
            )
        except Exception as e:
            logging.critical(f'Could not find bot config Firestore docs.')
            raise e