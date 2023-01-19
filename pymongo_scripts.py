from pymongo import MongoClient
from typing import Union, List
import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_database():
    """Establish a connection with client and retrieve database"""
    db_username = 'diaa_malek'
    db_password = 'this_is_a_password'
    # Provide the mongodb atlas url to connect python to mongodb using pymongo
    CONNECTION_STRING = f"mongodb+srv://{db_username}:{db_password}@task-afaqy.fbqkr4w.mongodb.net/?retryWrites=true&w=majority"
    # Create a connection using MongoClient. You can import MongoClient or use pymongo.MongoClient
    client = MongoClient(CONNECTION_STRING)
    # Create the database for our example (we will use the same database throughout the tutorial
    return client['password_manager']


def get_userlist()->list:
    "Return a list of unique telegram IDs of users registered in the database"
    collection = get_database()['users_data']
    users_cursor = collection.find()
    # logger.info("get_userlist() called",)
    return users_cursor.distinct('_id')

def user_exists(_id : str) ->bool:
    "Returns True if a user id exists in the database"
    if _id in get_userlist():
        return True
    else:
        return False

def get_user_data(_id : str, datafield : str = None)-> Union[str, dict]:
    """Retrieve user data as a dictionary if no datafield is 'all', otherwise return the datafield"""
    collection = get_database()['users_data']
    user_data = collection.find_one({'_id':_id})

    # logger.info(f"Querying user data for user {_id}")
    if datafield is None:
        raise('Datafield was not specified')
    elif datafield == 'all':
        return user_data
    else:
        return user_data[datafield]


def set_user_data(_id : str, user_data: dict)->None:
    """Add user data to database"""
    logger.info(f"Adding data of user {_id} to database")
    collection = get_database()['users_data']
    collection.insert_one(user_data)


def get_credential_list(_id : str, services_only : bool=False) ->Union[List[dict], List[str]]:
    """Retrieve a user's credentials as a list of dictionaries (service, username, password)
    Returns a list of strings (service names) if services_only=True"""
    # logger.info(f"Querying credentials of user {_id}")
    collection = get_database()['passwords']
    credentials = collection.find_one({'_id':_id})
    if credentials:
        if services_only:
            return [i['service'] for i in credentials['credentials']]
        else:
            return credentials['credentials']

def get_credential(_id : str, service: str) ->Union[dict, None]:
    """Returns the dictionary of a specific credential, or None if not found"""
    all_creds = get_credential_list(_id)
    if not all_creds:
        return None
    for credential in all_creds:
        if credential['service'].lower() == service.lower():
            return credential

def delete_credential(_id : str, service: str)->bool:
    """Removes a credential from the database. Returns True if found and deleted"""
    collection = get_database()['passwords']

    credential = get_credential(_id, service)
    logger.info(f"Deleting '{service}' credential for user {_id}")

    if not credential or credential is None:
        return False
    else:
        collection.find_one_and_update({'_id': _id}, {'$pull': {'credentials' : {'service':service}}})
        return True

def add_credential(_id : str, credential: dict) ->bool:
    """Adds a new credential to the database. Returns True if successfully added, False if a duplicate was found"""
    logger.info(f"Adding {credential['service']} credential for user {_id}")
    collection = get_database()['passwords']

    user_credentials = collection.find_one({'_id':_id})
    if not user_credentials:
        collection.insert_one({'_id':_id, 'credentials': [credential]})
        return True
    elif credential['service'].lower() in [i['service'].lower() for i in user_credentials['credentials']]:
        return False
    else:
        collection.find_one_and_update({'_id':_id}, {'$push':{'credentials':credential}})
        return True

if __name__ == "__main__":

    dbname = get_database()
