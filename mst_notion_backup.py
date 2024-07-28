import os
from notion_client import Client
from dataclasses import dataclass
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText



mst_backup_secret_key = os.environ["MST_BACKUP_SECRET_KEY"]
backup_records_db_id = os.environ["MST_BACKUP_RECORDS_DB_ID"]
member_space_page_id = os.environ["MST_MEMBER_SPACE_PAGE_ID"]


@dataclass
class BackupRecord:
    PageID: str
    Email: str
    Date: str



def send_email(sender_email, sender_password, recipient_email, subject, body):
    try:
        # Create the MIME object
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject

        # Attach the body of the email
        msg.attach(MIMEText(body, 'plain'))

        # Connect to Gmail's SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Upgrade the connection to a secure encrypted SSL/TLS connection
        server.login(sender_email, sender_password)

        # Send the email
        server.send_message(msg)
        server.quit()
        
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email. Error: {e}")

# Usage example
backup_sender_email = os.environ["BACKUP_EMAIL_SENDER_ADDRESS"]
backup_sender_password = os.environ["BACKUP_EMAIL_SENDER_PASSWORD"]
title_prefix = "MST_Journal_"

def parse_date(date_string):
    try:
        # Try parsing the first format "24 07 11 (목)"
        parsed_date = datetime.strptime(date_string[:8], "%y %m %d")
    except ValueError:
        try:
            # Try parsing the second format "2024-07-11"
            parsed_date = datetime.strptime(date_string, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date format not recognized")

    # Formatting the parsed date
    formatted_date = parsed_date.strftime("%Y-%m-%d")
    return formatted_date


def mst_notion_backup(mst_backup_secret_key):
    client = Client(auth=mst_backup_secret_key)
    backup_records_db = client.databases.retrieve(database_id=backup_records_db_id)
    blocks = client.blocks.children.list(block_id=member_space_page_id)
    for block in blocks['results']:
        if not block['has_children']:
            continue
        block_id = block['id']
        member_blocks = client.blocks.children.list(block_id=block_id)
        email_address = None
        for member_block in member_blocks['results']:
            if member_block['type'] == 'paragraph':
                if member_block['paragraph']:
                    text = member_block['paragraph']['rich_text'][0]['text']['content']
                    text_splitted = text.split(":")
                    if text_splitted[0].lower().replace("-", "") == "email":
                        email_address = text_splitted[1].strip()
                        continue
            if email_address is None:
                continue
            if member_block['type'] == 'child_page':
                child_page_id = member_block['id']
                child_page_blocks = client.blocks.children.list(block_id=child_page_id)
                page_title = title_prefix + member_block['child_page']['title']
                text_list = []
                for child_page_block in child_page_blocks['results']:
                    if child_page_block['type'] == 'paragraph':
                        text = child_page_block['paragraph']['rich_text'][0]['text']['content']
                        if text.startswith("!status"):
                            backup = False
                            if "완료" in text:
                                backup = True
                            if "수정" in text:
                                backup = True
                            continue
                        else:
                            text_list.append(text)
                if backup:
                    text_concatenated = "\n".join(text_list)
                    send_email(backup_sender_email, backup_sender_password, email_address, page_title, text_concatenated)

    
if __name__ == "__main__":
    mst_notion_backup(mst_backup_secret_key)