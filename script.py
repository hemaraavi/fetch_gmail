# Import libraries
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from sqlalchemy import create_engine,text
from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from models import Email
import dateutil.parser
import pickle
import requests
import json
import os

# Define scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly','https://www.googleapis.com/auth/gmail.modify']
ACCESS_TOKEN = ''
fields = {'From':'sender', 'Subject':'subject', 'To':'recepient', 
        'Date':'received_date','Received Date':'received_date'}

def main():
    try:
        fetch_emails()
        modify_emails()
    except Exception as e:
        print(f"An error occurred: {e}")

def fetch_emails():
    '''
    Fetches emails from the user's mailbox and inserts them into the database
    '''
    service = gmail_authenticate()
    # Get the list of messages in the user's mailbox
    results = service.users().messages().list(userId='me', labelIds=['INBOX']).execute()
    messages = results.get('messages', [])
    # Create a database session
    session = create_db_session()
    for msg in messages:
        # Get the full email message
        txt = service.users().messages().get(userId='me', id=msg['id'], format='metadata').execute()
        email_dict = {'message_id': msg['id'], 'label': 'INBOX'}
        try:
            headers = txt['payload']['headers']
            for each in headers:
                for field_key,field_value in fields.items():
                    if each['name'] == field_key:
                        if field_key == 'Date':
                            received_date = dateutil.parser.parse(each['value'])
                            email_dict[field_value] = received_date
                        else:
                            email_dict[field_value] = each['value']
            # Insert the email into the database
            email = Email(**email_dict)
            session.add(email)
        except Exception as e:
            print(f"An error occurred: {e}")
    session.commit()
    session.close()

def gmail_authenticate():
    ''' 
    Authenticates the user and creates a Gmail service object
    Returns:
            service: Gmail service object
    '''
    global ACCESS_TOKEN
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if Path('token.pickle').is_file():
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
    # If there are no (valid) credentials available, letting the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Saving the credentials for the next run
        with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
    ACCESS_TOKEN = creds.token
    # Building the Gmail service object
    service = build('gmail', 'v1', credentials=creds)
    return service



def create_db_session():
    ''' 
    Creates a session to interact with the database
    Returns:
        session: Database session object
    '''
    engine = create_engine('sqlite:///emails.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    return session



def load_rules():
    '''
    Loads the rules from the rules.json file
    Returns:
        rules: List of rules
    '''
    with open('rules.json', 'r') as file:
        return json.load(file)["rules"]


def modify_emails():
    '''
    Modifies the emails based on the rules defined in rules.json
    '''
    as_read_ids,unread_ids,move_ids = build_query_based_on_rules()
    # Modify the emails based on the rules
    modify_api_call(as_read_ids,unread_ids,move_ids)

    
def build_conditions(where_conditions,params,condition):
    '''
    Builds the conditions for the SQL query based on the rule conditions
    Args:
        where_conditions: List of conditions
        params: Dictionary of parameters
        condition: Condition from the rule
    Returns:
        where_conditions: List of conditions
        params: Dictionary of parameters
    '''
    if 'field' not in condition or 'predicate' not in condition or 'value' not in condition:
        return where_conditions,params
    field = fields.get(condition["field"],'')
    predicate = condition["predicate"].lower()
    value = condition["value"]
    # Check if the field is valid
    if predicate == "contains":
        where_conditions.append(f"{field} LIKE :{field}_like")
        params[f"{field}_like"] = f"%{value}%"

    elif predicate == "does not contain":
        where_conditions.append(f"{field} NOT LIKE :{field}_not_like")
        params[f"{field}_not_like"] = f"%{value}%"

    elif predicate == "does not equal":
        conditions.append(f"{field} <> :{field}_not_equal")
        params[f"{field}_not_equal"] = value

    elif predicate == "equals":
        conditions.append(f"{field} = :{field}_eq")
        params[f"{field}_eq"] = value

    elif field == "received_date":
        # Calculate the datetime value for 'less than' condition
        date_threshold = datetime.now() - timedelta(days=int(value))
        if predicate == "less than": 
            where_conditions.append(f"{field} < :{field}_lt")
            params[f"{field}_lt"] = date_threshold.strftime('%Y-%m-%d %H:%M:%S')
        else:
            where_conditions.append(f"{field} > :{field}_gt")
            params[f"{field}_gt"] = date_threshold.strftime('%Y-%m-%d %H:%M:%S')

    return where_conditions,params


def build_query_based_on_rules():
    rules = load_rules()
    where_conditions = []
    params = {}
    session = create_db_session()
    as_read_ids,unread_ids,move_ids = [],[],[]
    for rule in rules:
        message_ids = []
        for condition in rule["conditions"]:
            try:
                where_conditions,params = build_conditions(where_conditions,params,condition)
            except Exception as e:
                print(f"An error occurred: {e}")
                continue
        # Join the conditions with 'AND' as per the "predicate": "All"
        if rule["predicate"] == "All":
            where_clause = " AND ".join(where_conditions)
        else:
            # Join the conditions with 'OR' as per the "predicate": "Any"
            where_clause = " OR ".join(where_conditions)

        # Construct the final SQL query
        sql = text(f"SELECT message_id FROM email WHERE {where_clause}")
        # Execute the query with parameters
        result = session.execute(sql, params)

        for row in result:
            message_ids.append(row[0])

        for action in rule["actions"]:
            if action == "Mark as Read":
                as_read_ids.extend(message_ids)
            elif action == "Move Message":
                move_ids.extend(message_ids)
            elif action == "Mark as Unread":
                unread_ids.extend(message_ids)
    session.close()
    return as_read_ids,unread_ids,move_ids

def modify_api_call(as_read_ids,unread_ids,move_ids):
    '''
    Modifies the emails based on the rules
    Args:
        as_read_ids: List of message IDs to be marked as read
        unread_ids: List of message IDs to be marked as unread
        move_ids: List of message IDs to be moved to the inbox
    '''
    url = f'https://gmail.googleapis.com/gmail/v1/users/me/messages/batchModify'
    headers = {'Authorization': f'Bearer {ACCESS_TOKEN}', 'Content-Type': 'application/json'}
    if as_read_ids:
        data = {'ids':as_read_ids,'removeLabelIds': ['UNREAD']}
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200 or response.status_code == 204:
            print(f"Messages marked as read.")
        else:
            print(f"Failed to mark messages as read. Status code: {response.status_code}")
    if unread_ids:
        data = {'ids':unread_ids,'addLabelIds': ['UNREAD']}
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200 or response.status_code == 204:
            print(f"Messages marked as unread.")
        else:
            print(f"Failed to mark messages as unread. Status code: {response.status_code}")
    if move_ids:
        data = {'ids':move_ids,'addLabelIds': ['INBOX']}
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200 or response.status_code == 204:
            print(f"Messages moved ")
        else:
            print(f"Failed to move  {response.status_code}")
    if not as_read_ids and not unread_ids and not move_ids:
        print(f"No rules matched.")

if __name__ == "__main__":
    main()
