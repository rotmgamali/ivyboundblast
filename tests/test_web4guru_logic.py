import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock environment variables BEFORE importing modules that use them
os.environ["MAILREEF_API_KEY"] = "mock_key"

from reply_watcher import ReplyWatcher
import mailreef_automation.automation_config as automation_config

class TestReplyWatcherWeb4Guru(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_mailreef = MagicMock()
        self.mock_sheets = MagicMock()
        self.mock_telegram = MagicMock()
        self.mock_generator = MagicMock()
        
        # Initialize Watcher with new profile
        with patch('reply_watcher.MailreefClient', return_value=self.mock_mailreef), \
             patch('reply_watcher.GoogleSheetsClient', return_value=self.mock_sheets), \
             patch('reply_watcher.TelegramNotifier', return_value=self.mock_telegram), \
             patch('reply_watcher.EmailGenerator', return_value=self.mock_generator), \
             patch('reply_watcher.lock_util.ensure_singleton'), \
             patch('reply_watcher.get_logger'):
            
            self.watcher = ReplyWatcher(profile_name="WEB4GURU_ACCOUNTANTS")
            
    def test_positive_reply_triggers_auto_reply(self):
        # Mock GPT response to be 'positive'
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "positive"
        self.watcher.generator.client.chat.completions.create.return_value = mock_completion
        
        # Mock Mailreef inbox status
        self.watcher.mailreef.get_inbox_status.return_value = {"sender_name": "Web4Guru Team"}
        self.watcher.mailreef.send_email.return_value = {"success": True}
        
        # Mock a reply
        reply_data = {
            "from_email": "lead@cpafirm.com",
            "body": "Yes, we are taking new clients right now.",
            "subject": "Re: Inquiry",
            "inbox_email": "andrew@aspireteam.help", # One of the errorskin inboxes
            "thread_id": "thread_123",
            "date": "2026-02-13T10:00:00"
        }
        
        # Mock get_inbox_replies to return this reply
        self.watcher.get_inbox_replies = MagicMock(return_value=[reply_data])
        
        # Run processing
        with patch.object(self.watcher, 'load_state', return_value={}), \
             patch.object(self.watcher, 'save_state'):
            self.watcher.process_replies()
            
        # Verify GPT was called with custom prompt
        # We can't easy verify the prompt content without inspecting args, but we can verify call
        self.watcher.generator.client.chat.completions.create.assert_called()
        
        # Verify Auto-Reply was sent
        self.watcher.mailreef.send_email.assert_called()
        args, _ = self.watcher.mailreef.send_email.call_args
        
        inbox_id, to_email, subject, body = args
        self.assertEqual(inbox_id, "andrew@aspireteam.help")
        self.assertEqual(to_email, "lead@cpafirm.com")
        self.assertEqual(subject, "Re: Inquiry")
        
        # Verify body content has the pitch (from email_2.txt)
        # We expect "lead generation service" (full text) to be in there
        self.assertIn("lead generation service", body)
        self.assertIn("Web4Guru", body)
        
        print("\n✅ Test Passed: Positive reply triggered correct auto-reply.")

if __name__ == '__main__':
    unittest.main()
