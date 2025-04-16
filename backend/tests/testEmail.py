\
import unittest
from unittest.mock import patch, MagicMock, ANY
import base64
from email.mime.text import MIMEText
import sys
import os

# Add the parent directory to the sys.path to allow importing Email module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app', 'api', 'endpoints')))

# Now import the module (assuming Email.py is in the endpoints directory)
# If Email.py is directly under backend, adjust the path accordingly
try:
    from Email import GmailService
except ImportError as e:
    print(f"Error importing GmailService: {e}")
    print(f"Current sys.path: {sys.path}")
    # If the import fails, try importing from the root backend directory as a fallback
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from Email import GmailService


# Mock gauth module before it's imported by Email.py
mock_gauth = MagicMock()
sys.modules['gauth'] = mock_gauth


class TestGmailService(unittest.TestCase):

    def _create_mock_message(self, msg_id, thread_id, subject, from_addr, to_addr, snippet, body=None, mime_type='text/plain', parts=None, headers_extra=None):
        """Helper to create a mock Gmail API message structure."""
        headers = [
            {'name': 'Subject', 'value': subject},
            {'name': 'From', 'value': from_addr},
            {'name': 'To', 'value': to_addr},
            {'name': 'Date', 'value': 'Tue, 15 Apr 2025 10:00:00 +0000'},
            {'name': 'Message-ID', 'value': f'<{msg_id}@mail.gmail.com>'}
        ]
        if headers_extra:
            headers.extend(headers_extra)

        payload = {
            'mimeType': mime_type,
            'headers': headers,
            'body': {},
            'parts': parts if parts else []
        }

        if body and mime_type == 'text/plain':
             payload['body'] = {'size': len(body), 'data': base64.urlsafe_b64encode(body.encode('utf-8')).decode('utf-8')}
        elif body and mime_type.startswith('multipart/'):
             # Simplified: Assume first part is text/plain if body is provided for multipart
             if not parts:
                 payload['parts'] = [{
                     'mimeType': 'text/plain',
                     'body': {'size': len(body), 'data': base64.urlsafe_b64encode(body.encode('utf-8')).decode('utf-8')}
                 }]


        return {
            'id': msg_id,
            'threadId': thread_id,
            'snippet': snippet,
            'payload': payload,
            'labelIds': ['INBOX', 'UNREAD'],
            'historyId': '12345',
            'internalDate': '1618486800000', # Example timestamp
            'sizeEstimate': 1024
        }

    def _create_mock_attachment_part(self, part_id, filename, mime_type, attachment_id):
        """Helper to create a mock attachment part."""
        return {
            "partId": part_id,
            "mimeType": mime_type,
            "filename": filename,
            "body": {
                "attachmentId": attachment_id,
                "size": 1000 # Dummy size
            }
        }

    @patch('Email.build') # Patch 'build' within the Email module's namespace
    def setUp(self, mock_build):
        # Reset mock_gauth calls for each test
        mock_gauth.reset_mock()

        # Mock credentials
        self.mock_credentials = MagicMock()
        mock_gauth.get_stored_credentials.return_value = self.mock_credentials

        # Mock the service returned by build
        self.mock_service = MagicMock()
        mock_build.return_value = self.mock_service

        # Instantiate the service (this will call build and get_stored_credentials)
        self.gmail_service = GmailService(user_id='test@example.com')

        # Verify mocks were called during setup
        mock_gauth.get_stored_credentials.assert_called_once_with(user_id='test@example.com')
        mock_build.assert_called_once_with('gmail', 'v1', credentials=self.mock_credentials)


    def test_init_success(self):
        # Setup already handles successful init, just assert mocks were called
        mock_gauth.get_stored_credentials.assert_called_once_with(user_id='test@example.com')
        self.assertIsNotNone(self.gmail_service.service)

    @patch('Email.build')
    def test_init_no_credentials(self, mock_build):
        mock_gauth.get_stored_credentials.return_value = None
        with self.assertRaisesRegex(RuntimeError, "No Oauth2 credentials stored"):
            GmailService(user_id='test@example.com')
        mock_gauth.get_stored_credentials.assert_called_once_with(user_id='test@example.com')
        mock_build.assert_not_called() # build should not be called if creds are missing

    def test_query_emails_success(self):
        mock_list_response = {
            'messages': [{'id': 'msg1', 'threadId': 'thr1'}, {'id': 'msg2', 'threadId': 'thr2'}],
            'resultSizeEstimate': 2
        }
        mock_msg1 = self._create_mock_message('msg1', 'thr1', 'Subject 1', 'sender1@example.com', 'test@example.com', 'Snippet 1')
        mock_msg2 = self._create_mock_message('msg2', 'thr2', 'Subject 2', 'sender2@example.com', 'test@example.com', 'Snippet 2')

        self.mock_service.users().messages().list().execute.return_value = mock_list_response
        self.mock_service.users().messages().get.side_effect = [mock_msg1, mock_msg2]

        emails = self.gmail_service.query_emails(query='is:unread', max_results=5)

        self.mock_service.users().messages().list.assert_called_once_with(userId='me', maxResults=5, q='is:unread')
        self.assertEqual(self.mock_service.users().messages().get.call_count, 2)
        self.mock_service.users().messages().get.assert_any_call(userId='me', id='msg1')
        self.mock_service.users().messages().get.assert_any_call(userId='me', id='msg2')

        self.assertEqual(len(emails), 2)
        self.assertEqual(emails[0]['id'], 'msg1')
        self.assertEqual(emails[0]['subject'], 'Subject 1')
        self.assertEqual(emails[1]['id'], 'msg2')
        self.assertEqual(emails[1]['subject'], 'Subject 2')
        self.assertNotIn('body', emails[0]) # parse_body=False by default

    def test_query_emails_no_messages(self):
        mock_list_response = {'resultSizeEstimate': 0} # No 'messages' key
        self.mock_service.users().messages().list().execute.return_value = mock_list_response

        emails = self.gmail_service.query_emails()

        self.mock_service.users().messages().list.assert_called_once_with(userId='me', maxResults=100, q='')
        self.mock_service.users().messages().get.assert_not_called()
        self.assertEqual(len(emails), 0)

    def test_query_emails_api_error(self):
        self.mock_service.users().messages().list().execute.side_effect = Exception("API Error")

        emails = self.gmail_service.query_emails()

        self.assertEqual(len(emails), 0)
        # Add logging assertion if needed

    def test_get_email_by_id_with_attachments_success(self):
        msg_id = 'msg_attach'
        thread_id = 'thr_attach'
        body_content = "This is the email body."
        attachment_part1 = self._create_mock_attachment_part("part1", "file1.txt", "text/plain", "attach1")
        attachment_part2 = self._create_mock_attachment_part("part2", "image.jpg", "image/jpeg", "attach2")
        mock_msg = self._create_mock_message(
            msg_id, thread_id, 'Email with Attachments', 'sender@example.com', 'test@example.com',
            'Snippet attach', body=body_content, mime_type='multipart/mixed',
            parts=[
                {'mimeType': 'text/plain', 'body': {'size': len(body_content), 'data': base64.urlsafe_b64encode(body_content.encode('utf-8')).decode('utf-8')}},
                attachment_part1,
                attachment_part2
            ]
        )

        self.mock_service.users().messages().get().execute.return_value = mock_msg

        email, attachments = self.gmail_service.get_email_by_id_with_attachments(msg_id)

        self.mock_service.users().messages().get.assert_called_once_with(userId='me', id=msg_id)
        self.assertIsNotNone(email)
        self.assertEqual(email['id'], msg_id)
        self.assertEqual(email['subject'], 'Email with Attachments')
        self.assertEqual(email['body'], body_content)
        self.assertEqual(email['mimeType'], 'multipart/mixed') # Top-level mimeType

        self.assertIsInstance(attachments, dict)
        self.assertEqual(len(attachments), 2)
        self.assertIn('part1', attachments)
        self.assertIn('part2', attachments)
        self.assertEqual(attachments['part1']['filename'], 'file1.txt')
        self.assertEqual(attachments['part1']['attachmentId'], 'attach1')
        self.assertEqual(attachments['part2']['filename'], 'image.jpg')
        self.assertEqual(attachments['part2']['attachmentId'], 'attach2')


    def test_get_email_by_id_no_body(self):
        msg_id = 'msg_no_body'
        mock_msg = self._create_mock_message(msg_id, 'thr_no_body', 'No Body', 'sender@example.com', 'test@example.com', 'Snippet no body', mime_type='text/html') # No text/plain part
        mock_msg['payload']['parts'] = [{'mimeType': 'text/html', 'body': {'size': 100, 'data': 'PGh0bWw+...'}}] # Only HTML part

        self.mock_service.users().messages().get().execute.return_value = mock_msg

        email, attachments = self.gmail_service.get_email_by_id_with_attachments(msg_id)

        self.assertIsNotNone(email)
        self.assertNotIn('body', email) # Should not find a plain text body
        self.assertEqual(email['mimeType'], 'text/html') # Should still get mimeType
        self.assertEqual(len(attachments), 0)


    def test_get_email_by_id_api_error(self):
        msg_id = 'msg_error'
        self.mock_service.users().messages().get().execute.side_effect = Exception("API Error")

        email, attachments = self.gmail_service.get_email_by_id_with_attachments(msg_id)

        self.assertIsNone(email)
        self.assertEqual(len(attachments), 0)
        # Add logging assertion if needed

    def test_create_draft_success(self):
        mock_draft_response = {'id': 'draft123', 'message': {'id': 'msgDraft', 'threadId': 'thrDraft'}}
        self.mock_service.users().drafts().create().execute.return_value = mock_draft_response

        to = 'recipient@example.com'
        subject = 'Test Draft'
        body = 'This is the draft body.'
        draft = self.gmail_service.create_draft(to=to, subject=subject, body=body)

        self.assertIsNotNone(draft)
        self.assertEqual(draft['id'], 'draft123')

        # Verify the call arguments
        call_args = self.mock_service.users().drafts().create.call_args
        self.assertEqual(call_args[1]['userId'], 'me') # kwargs['userId']

        # Check the raw message content
        expected_mime = MIMEText(body)
        expected_mime['to'] = to
        expected_mime['subject'] = subject
        expected_raw = base64.urlsafe_b64encode(expected_mime.as_bytes()).decode('utf-8')

        self.assertEqual(call_args[1]['body']['message']['raw'], expected_raw)


    def test_create_draft_with_cc_success(self):
        mock_draft_response = {'id': 'draft456'}
        self.mock_service.users().drafts().create().execute.return_value = mock_draft_response

        to = 'recipient@example.com'
        subject = 'Test Draft CC'
        body = 'This is the draft body with CC.'
        cc = ['cc1@example.com', 'cc2@example.com']
        draft = self.gmail_service.create_draft(to=to, subject=subject, body=body, cc=cc)

        self.assertIsNotNone(draft)
        self.assertEqual(draft['id'], 'draft456')

        call_args = self.mock_service.users().drafts().create.call_args
        expected_mime = MIMEText(body)
        expected_mime['to'] = to
        expected_mime['subject'] = subject
        expected_mime['cc'] = 'cc1@example.com,cc2@example.com'
        expected_raw = base64.urlsafe_b64encode(expected_mime.as_bytes()).decode('utf-8')

        self.assertEqual(call_args[1]['body']['message']['raw'], expected_raw)

    def test_create_draft_api_error(self):
        self.mock_service.users().drafts().create().execute.side_effect = Exception("API Error")
        draft = self.gmail_service.create_draft(to='r@e.com', subject='S', body='B')
        self.assertIsNone(draft)
        # Add logging assertion if needed

    def test_delete_draft_success(self):
        draft_id = 'draft_to_delete'
        # Delete returns empty body on success
        self.mock_service.users().drafts().delete().execute.return_value = {}

        result = self.gmail_service.delete_draft(draft_id)

        self.assertTrue(result)
        self.mock_service.users().drafts().delete.assert_called_once_with(userId='me', id=draft_id)

    def test_delete_draft_api_error(self):
        draft_id = 'draft_err'
        self.mock_service.users().drafts().delete().execute.side_effect = Exception("API Error")

        result = self.gmail_service.delete_draft(draft_id)

        self.assertFalse(result)
        # Add logging assertion if needed

    def test_create_reply_send_success(self):
        original_msg_id = 'orig_msg1'
        original_thread_id = 'orig_thr1'
        original_subject = 'Original Subject'
        original_from = 'sender@example.com'
        original_body = "Original email content."
        original_date = 'Tue, 15 Apr 2025 09:00:00 +0000'

        original_message = {
            'id': original_msg_id,
            'threadId': original_thread_id,
            'subject': original_subject,
            'from': original_from,
            'body': original_body,
            'date': original_date,
        }
        reply_body = "This is the reply."
        expected_subject = "Re: Original Subject"
        expected_full_body = (
            f"{reply_body}\n\n"
            f"On {original_date}, {original_from} wrote:\n"
            f"> {original_body.replace('\n', '\n> ')}"
        )

        mock_send_response = {'id': 'reply_msg1', 'threadId': original_thread_id, 'labelIds': ['SENT']}
        self.mock_service.users().messages().send().execute.return_value = mock_send_response

        result = self.gmail_service.create_reply(original_message, reply_body, send=True)

        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 'reply_msg1')
        self.assertEqual(result['labelIds'], ['SENT'])

        # Verify send call arguments
        call_args = self.mock_service.users().messages().send.call_args
        self.assertEqual(call_args[1]['userId'], 'me')

        sent_body = call_args[1]['body']
        self.assertEqual(sent_body['threadId'], original_thread_id)

        # Decode raw message and check headers/body
        raw_bytes = base64.urlsafe_b64decode(sent_body['raw'])
        # Note: Python's email parser might be needed for full verification,
        # but checking key parts is often sufficient for unit tests.
        raw_string = raw_bytes.decode('utf-8')
        self.assertIn(f"To: {original_from}", raw_string)
        self.assertIn(f"Subject: {expected_subject}", raw_string)
        self.assertIn(f"In-Reply-To: {original_msg_id}", raw_string)
        self.assertIn(f"References: {original_msg_id}", raw_string)
        # Check if the body content exists (might be split by headers)
        self.assertTrue(raw_string.endswith(expected_full_body) or expected_full_body in raw_string)


    def test_create_reply_draft_success(self):
        original_message = {
            'id': 'orig_msg2', 'threadId': 'orig_thr2', 'subject': 'Draft This',
            'from': 'sender2@example.com', 'body': 'Draft body.', 'date': 'Wed, 16 Apr 2025 11:00:00 +0000'
        }
        reply_body = "This is the reply draft."
        cc = ['cc@example.com']

        mock_draft_response = {'id': 'reply_draft1', 'message': {'id': 'reply_msg_draft', 'threadId': 'orig_thr2'}}
        self.mock_service.users().drafts().create().execute.return_value = mock_draft_response

        result = self.gmail_service.create_reply(original_message, reply_body, send=False, cc=cc)

        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 'reply_draft1')
        self.mock_service.users().messages().send.assert_not_called() # Ensure send wasn't called
        self.mock_service.users().drafts().create.assert_called_once()

        # Verify draft creation arguments (similar checks as send, but for draft)
        call_args = self.mock_service.users().drafts().create.call_args
        self.assertEqual(call_args[1]['userId'], 'me')
        draft_body = call_args[1]['body']['message']
        self.assertEqual(draft_body['threadId'], 'orig_thr2')

        raw_bytes = base64.urlsafe_b64decode(draft_body['raw'])
        raw_string = raw_bytes.decode('utf-8')
        self.assertIn(f"To: {original_message['from']}", raw_string)
        self.assertIn(f"Subject: Re: {original_message['subject']}", raw_string)
        self.assertIn(f"Cc: {cc[0]}", raw_string)
        self.assertIn(f"In-Reply-To: {original_message['id']}", raw_string)
        self.assertIn(f"References: {original_message['id']}", raw_string)
        self.assertTrue(reply_body in raw_string)


    def test_create_reply_no_from_error(self):
         original_message = { # Missing 'from'
            'id': 'orig_msg_no_from', 'threadId': 'orig_thr_no_from', 'subject': 'No From',
            'body': 'Body.', 'date': 'Wed, 16 Apr 2025 12:00:00 +0000'
        }
         reply_body = "Reply attempt."
         # Expecting a ValueError, but the function catches Exception and logs
         # So we check for None return and potentially log messages
         result = self.gmail_service.create_reply(original_message, reply_body, send=True)
         self.assertIsNone(result)
         # Add logging assertion if needed


    def test_create_reply_api_error(self):
        original_message = {
            'id': 'orig_msg_err', 'threadId': 'orig_thr_err', 'subject': 'API Error Test',
            'from': 'sender_err@example.com', 'body': 'Body err.', 'date': 'Wed, 16 Apr 2025 13:00:00 +0000'
        }
        reply_body = "Reply error."
        self.mock_service.users().messages().send().execute.side_effect = Exception("API Send Error")

        result = self.gmail_service.create_reply(original_message, reply_body, send=True)
        self.assertIsNone(result)
        # Add logging assertion if needed

    def test_get_attachment_success(self):
        msg_id = 'msg_with_attach'
        attach_id = 'attach_data1'
        mock_attachment_response = {
            'size': 12345,
            'data': base64.urlsafe_b64encode(b'attachment content').decode('utf-8')
        }
        self.mock_service.users().messages().attachments().get().execute.return_value = mock_attachment_response

        attachment = self.gmail_service.get_attachment(msg_id, attach_id)

        self.assertIsNotNone(attachment)
        self.assertEqual(attachment['size'], 12345)
        self.assertEqual(attachment['data'], mock_attachment_response['data'])
        self.mock_service.users().messages().attachments().get.assert_called_once_with(
            userId='me', messageId=msg_id, id=attach_id
        )

    def test_get_attachment_api_error(self):
        msg_id = 'msg_attach_err'
        attach_id = 'attach_err1'
        self.mock_service.users().messages().attachments().get().execute.side_effect = Exception("API Attach Error")

        attachment = self.gmail_service.get_attachment(msg_id, attach_id)

        self.assertIsNone(attachment)
        # Add logging assertion if needed

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

