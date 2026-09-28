"""
Unit tests for Confirmation Manager (PRD Section 14 & 15).
"""

import time
import unittest
from core.confirmation import confirmation_manager
from mikrotik.base import OperationResult


class TestConfirmationManager(unittest.TestCase):
    def setUp(self):
        self.user_id = 99999
        self.device = "Kantor Utama"

    def test_create_and_execute_confirmation(self):
        executed = []

        def dummy_action():
            executed.append(True)
            return OperationResult(success=True, message="Dummy action executed successfully")

        # 1. Create pending action
        action = confirmation_manager.create_pending_action(
            user_id=self.user_id,
            device_name=self.device,
            action_name="test_action",
            arguments={"param1": "val1"},
            description="Test execution",
            callback=dummy_action,
        )
        self.assertIsNotNone(action)
        self.assertFalse(action.is_expired)

        # 2. Get pending for user
        user_pending = confirmation_manager.get_pending_for_user(self.user_id)
        self.assertEqual(user_pending.token, action.token)

        # 3. Execute action
        result = confirmation_manager.execute_action(action.token)
        self.assertTrue(result.success)
        self.assertTrue(executed[0])

        # 4. Pending should now be cleared
        cleared = confirmation_manager.get_pending_for_user(self.user_id)
        self.assertIsNone(cleared)

    def test_cancel_confirmation(self):
        action = confirmation_manager.create_pending_action(
            user_id=self.user_id,
            device_name=self.device,
            action_name="test_action",
            arguments={},
            description="Test cancellation",
        )
        cancelled = confirmation_manager.cancel_action(action.token)
        self.assertTrue(cancelled)

        self.assertIsNone(confirmation_manager.get_pending_for_user(self.user_id))


if __name__ == "__main__":
    unittest.main()
