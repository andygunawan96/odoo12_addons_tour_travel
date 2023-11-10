import os
import pickle
# Gmail API utils
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
# for encoding/decoding messages in base64
from base64 import urlsafe_b64decode, urlsafe_b64encode
# for dealing with attachement MIME types
from email import encoders
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from mimetypes import guess_type as guess_mime_type
import logging
import codecs
from datetime import datetime, timedelta
import traceback
import time
import json
import base64
from .db_connector import GatewayConnector
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)
# Request all access (permission to read/send/receive emails, manage the inbox, and more)
SCOPES = ['https://mail.google.com/']
##AUTH
def_folder = '/var/log/tour_travel/gmailcredentials'
def gmail_authenticate(creds, email_name):
    if creds:
        if creds.refresh_token and creds.expiry - datetime.now() < timedelta(minutes=10):
            if os.path.exists("%s/update_status_email_%s.txt" % (def_folder, email_name)):
                update_status_email_file = read_file_update(email_name)
            else:
                update_status_email_file = {## Block, karena pasti sdh mau expired
                    "last_update": time.time(),
                    "is_update": True
                }
                write_file_update(update_status_email_file, email_name)
                update_status_email_file.update({## open untuk worker yg bikin file
                    "is_update": False
                })

            if update_status_email_file['is_update'] and creds.expiry - datetime.now() > timedelta(minutes=5):
                ## someone is updating but the expiry time is still longer than 5 minutes, do nothing and use old creds
                pass ## do nothing
            else:
                ## 1. no one is updating
                ## 2. someone is updating but the expiry time is less than 5 minutes
                update_status_email_file.update({  ## Block
                    "last_update": time.time(),
                    "is_update": True
                })
                write_file_update(update_status_email_file, email_name)
                try:
                    creds.refresh(Request())
                    with open("%s/%s.pickle" % (def_folder, email_name), "wb") as token:
                        pickle.dump(creds, token)
                except Exception as e:
                    _logger.error('Error update credential backend')
                    _logger.error("%s, %s" % (str(e), traceback.format_exc()))
                    raise UserError('Connection Failed') ## user error disini karena kalau di test connection pakai try except hasil return akan selalu failed
                    # data = {
                    #     'code': 9903,
                    #     'title': 'ERROR EMAIL BACKEND',
                    #     'message': 'Error refresh token email backend %s' % (str(e)),
                    # }
                    # GatewayConnector().telegram_notif_api(data, {})
                update_status_email_file.update({
                    "is_update": False,
                    "last_update": time.time(),
                })
                write_file_update(update_status_email_file, email_name)
        return build('gmail', 'v1', credentials=creds, cache_discovery=False)
    else:
        _logger.error('Error please set email first')
        return False

def write_file_update(update_status_email_file, email_name):
    _file = open("%s/update_status_email_%s.txt" % (def_folder, email_name), 'w')
    _file.write(json.dumps(update_status_email_file))
    _file.close()

def read_file_update(email_name):
    file = open("%s/update_status_email_%s.txt" % (def_folder, email_name), "r")
    data = file.read()
    file.close()
    return json.loads(data)

##SEARCH EMAIL
def search_messages(service, query, limit_message=100):
    result = service.users().messages().list(userId='me',q=query).execute()
    messages = [ ]
    if 'messages' in result:
        messages.extend(result['messages'])
    if len(messages) < limit_message:
        while 'nextPageToken' in result:
            page_token = result['nextPageToken']
            result = service.users().messages().list(userId='me',q=query, pageToken=page_token).execute()
            if 'messages' in result:
                messages.extend(result['messages'])
            if len(messages) > limit_message:
                break

    return messages[0:limit_message]

def get_size_format(b, factor=1024, suffix="B"):
    """
    Scale bytes to its proper byte format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if b < factor:
            return f"{b:.2f}{unit}{suffix}"
        b /= factor
    return f"{b:.2f}Y{suffix}"

def clean(text):
    # clean text for creating a folder
    return "".join(c if c.isalnum() else "_" for c in text)

def parse_parts(service, parts, folder_name, message, email):
    """
    Utility function that parses the content of an email partition
    """
    if parts:
        for part in parts:
            filename = part.get("filename")
            mimeType = part.get("mimeType")
            body = part.get("body")
            data = body.get("data")
            file_size = body.get("size")
            part_headers = part.get("headers")
            if part.get("parts"):
                # recursively call this function when we see that a part
                # has parts inside
                email = parse_parts(service, part.get("parts"), folder_name, message, email)
            if mimeType == "text/plain":
                # if the email part is text plain
                if data:
                    text = urlsafe_b64decode(data).decode()
                    email['body'] += "%s\n" % text
            elif mimeType == "text/html":
                # if the email part is an HTML content
                # save the HTML file and optionally open it in the browser
                if not filename:
                    filename = "index.html"
                filepath = os.path.join(folder_name, filename)
                email['body'] += "%s\n" % urlsafe_b64decode(data).decode()
                # with open(filepath, "wb") as f:
                #     f.write(urlsafe_b64decode(data))
            else:
                # attachment other than a plain text or HTML
                for part_header in part_headers:
                    part_header_name = part_header.get("name")
                    part_header_value = part_header.get("value")
                    if part_header_name == "Content-Disposition":
                        if "attachment" in part_header_value:
                            # we get the attachment ID
                            # and make another request to get the attachment itself
                            attachment_id = body.get("attachmentId")
                            attachment = service.users().messages().attachments().get(id=attachment_id, userId='me', messageId=message['id']).execute()
                            data = attachment.get("data")
                            filepath = os.path.join(folder_name, filename)
                            email['attachment'].append(data.replace('-','+').replace('_','/')) ## kalau tidak di replace waktu base64 ada error a multiple of 4 wktu upload
                            # if data:
                                # with open(filepath, "wb") as f:
                                #     f.write(urlsafe_b64decode(data))
    return email

def read_message(service, message):
    """
    This function takes Gmail API `service` and the given `message_id` and does the following:
        - Downloads the content of the email
        - Prints email basic information (To, From, Subject & Date) and plain/text parts
        - Creates a folder for each email based on the subject
        - Downloads text/html content (if available) and saves it under the folder created as index.html
        - Downloads any file that is attached to the email and saves it in the folder created
    """
    msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
    # parts can be the message body, or attachments
    payload = msg['payload']
    headers = payload.get("headers")
    parts = payload.get("parts")
    folder_name = "email"
    has_subject = False
    email = {
        "header": {
            "from": "",
            "to": "",
            "subject": "",
            "date": ""
        },
        "body": "",
        "attachment": []
    }
    if headers:
        # this section prints email basic info & creates a folder for the email
        for header in headers:
            name = header.get("name")
            value = header.get("value")
            if name.lower() == 'from':
                # we print the From address
                email['header']['from'] += "%s" % value
            if name.lower() == "to":
                # we print the To address
                email['header']['to'] += "%s" % value
            if name.lower() == "subject":
                # make our boolean True, the email has "subject"
                has_subject = True
                # make a directory with the name of the subject
                folder_name = clean(value)
                # we will also handle emails with the same subject name
                folder_counter = 0
                while os.path.isdir(folder_name):
                    folder_counter += 1
                    # we have the same folder name, add a number next to it
                    if folder_name[-1].isdigit() and folder_name[-2] == "_":
                        folder_name = f"{folder_name[:-2]}_{folder_counter}"
                    elif folder_name[-2:].isdigit() and folder_name[-3] == "_":
                        folder_name = f"{folder_name[:-3]}_{folder_counter}"
                    else:
                        folder_name = f"{folder_name}_{folder_counter}"
                # os.mkdir(folder_name)
                email['header']['subject'] += "%s" % value
            if name.lower() == "date":
                # we print the date when the message was sent
                email['header']['date'] += "%s" % value
    if not has_subject:
        # if the email does not have a subject, then make a folder with "email" name
        # since folders are created based on subjects
        # if not os.path.isdir(folder_name):
        #     os.mkdir(folder_name)
        pass
    parse_parts(service, parts, folder_name, message,email)
    return email

##SEND EMAIL
# Adds the attachment with the given filename to the given message
# def add_attachment(message, filename):
#     content_type, encoding = guess_mime_type(filename)
#     if content_type is None or encoding is not None:
#         content_type = 'application/octet-stream'
#     main_type, sub_type = content_type.split('/', 1)
#     if main_type == 'text':
#         fp = open(filename, 'rb')
#         msg = MIMEText(fp.read().decode(), _subtype=sub_type)
#         fp.close()
#     elif main_type == 'image':
#         fp = open(filename, 'rb')
#         msg = MIMEImage(fp.read(), _subtype=sub_type)
#         fp.close()
#     elif main_type == 'audio':
#         fp = open(filename, 'rb')
#         msg = MIMEAudio(fp.read(), _subtype=sub_type)
#         fp.close()
#     else:
#         fp = open(filename, 'rb')
#         msg = MIMEBase(main_type, sub_type)
#         msg.set_payload(fp.read())
#         fp.close()
#     filename = os.path.basename(filename)
#     msg.add_header('Content-Disposition', 'attachment', filename=filename)
#     encoders.encode_base64(msg)
#     message.attach(msg)

def add_attachment(message, attachment):
    main_type, sub_type = attachment.mimetype.split('/', 1)
    if attachment.datas: #pastikan attachment ada isi nya
        if main_type == 'text':
            msg = MIMEText(base64.b64decode(attachment.datas.decode()), _subtype=sub_type)
        elif main_type == 'image':
            msg = MIMEImage(base64.b64decode(attachment.datas), _subtype=sub_type)
        elif main_type == 'audio':
            msg = MIMEAudio(base64.b64decode(attachment.datas), _subtype=sub_type)
        else:
            msg = MIMEBase(main_type, sub_type)
            msg.set_payload(base64.b64decode(attachment.datas))


        msg.add_header('Content-Disposition', 'attachment', filename=attachment.datas_fname)
        encoders.encode_base64(msg)
        message.attach(msg)

# def build_message(destination, obj, body, attachments=[],email_account='', type='plain'):
#     if not attachments:  # no attachments given
#         message = MIMEText(body, type)
#         message['to'] = destination['to']
#         if destination['cc']:
#             message['cc'] = destination['cc']
#         if destination['bcc']:
#             message['bcc'] = destination['bcc']
#         message['from'] = email_account
#         message['subject'] = obj
#     else:
#         message = MIMEMultipart()
#         message['to'] = destination['to']
#         if destination['cc']:
#             message['cc'] = destination['cc']
#         if destination['bcc']:
#             message['bcc'] = destination['bcc']
#         message['from'] = email_account
#         message['subject'] = obj
#         message.attach(MIMEText(body, type))
#         for filename in attachments:
#             add_attachment(message, filename)
#     return {'raw': urlsafe_b64encode(message.as_bytes()).decode()}

def build_message(destination, obj, body, attachments=[],email_account='', type='plain'):
    if not attachments:  # no attachments given
        message = MIMEText(body, type)
    else:
        message = MIMEMultipart()
    message['to'] = destination['to']
    if destination['cc']:
        message['cc'] = destination['cc']
    if destination['bcc']:
        message['bcc'] = destination['bcc']
    message['from'] = email_account
    message['subject'] = obj
    if attachments:
        message.attach(MIMEText(body, type))
        for attachment in attachments:
            add_attachment(message, attachment)
    return {'raw': urlsafe_b64encode(message.as_bytes()).decode()}

def send_message(service, destination, obj, body, attachments=[], type='plain', email_account=''):
    return service.users().messages().send(
      userId="me",
      body=build_message(destination, obj, body, attachments, type=type, email_account=email_account)
    ).execute()


def connect_gmail(creds, email_name):
    gmail_auth = gmail_authenticate(creds, email_name)
    return gmail_auth

def search_email(gmail_auth, keyword, limit_messages=100):
    message_objs = search_messages(gmail_auth, keyword, limit_messages)
    return message_objs

def read_email(gmail_auth, message_id):
    message = read_message(gmail_auth, message_id)
    return message


###EXAMPLE
# get the Gmail API service
# service = gmail_authenticate()
##search email
# results = search_messages(service, 'a')
# for msg in results:
#     read_message(service, msg)

##send message
# send_message(service, "destination@domain.com", "This is a subject",
#             "This is the body of the email", ["test.txt", "anyfile.png"])