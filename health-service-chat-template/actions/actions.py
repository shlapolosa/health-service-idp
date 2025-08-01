# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

from typing import Any, Text, Dict, List
import os
import requests
from datetime import datetime

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormAction


class ActionCheckStatus(Action):
    """Action to check system status"""

    def name(self) -> Text:
        return "action_check_status"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Get environment info
        environment = os.getenv("ENVIRONMENT", "development")
        bot_name = os.getenv("BOT_NAME", "Rasa Assistant")
        rasa_url = os.getenv("RASA_URL", "http://localhost:5005")
        
        # Get current time
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create status message
        status_message = f"""
🤖 **{bot_name} Status Report**
📅 Time: {current_time}
🌍 Environment: {environment}
🔗 Rasa URL: {rasa_url}
✅ Status: Online and operational
🚀 Ready to assist you!
        """
        
        dispatcher.utter_message(text=status_message.strip())
        
        return []


class ActionProvideHelp(Action):
    """Action to provide help information"""

    def name(self) -> Text:
        return "action_provide_help"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        bot_name = os.getenv("BOT_NAME", "Rasa Assistant")
        
        help_message = f"""
🤖 **{bot_name} - How I Can Help You**

💬 **Available Commands:**
• Say "hello" or "hi" to start a conversation
• Ask about my "status" to check if I'm running properly
• Say "help" anytime to see this message
• Tell me how you're feeling - I can cheer you up!
• Say "goodbye" when you're done chatting

🛠️ **Technical Info:**
• I'm powered by Rasa and running on Kubernetes
• I use OAM (Open Application Model) for deployment
• I can scale automatically based on demand

❓ **Questions?**
Just ask me anything! I'm here to help.
        """
        
        dispatcher.utter_message(text=help_message.strip())
        
        return []


class ValidateUserInputForm(FormAction):
    """Form to collect user input"""

    def name(self) -> Text:
        return "validate_user_input_form"

    @staticmethod
    def required_slots(tracker: Tracker) -> List[Text]:
        return ["user_name"]

    def slot_mappings(self) -> Dict[Text, Any]:
        return {
            "user_name": [
                self.from_entity(entity="user_name"),
                self.from_text(intent="greet")
            ]
        }

    def validate_user_name(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Validate user_name value."""
        
        if slot_value and len(slot_value) > 0:
            # Capitalize the name
            formatted_name = slot_value.strip().title()
            dispatcher.utter_message(text=f"Nice to meet you, {formatted_name}!")
            return {"user_name": formatted_name}
        else:
            dispatcher.utter_message(text="I didn't catch your name. Could you tell me again?")
            return {"user_name": None}

    def submit(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        """Define what the form has to do after all required slots are filled"""
        
        user_name = tracker.get_slot("user_name")
        if user_name:
            dispatcher.utter_message(
                text=f"Hello {user_name}! I'm ready to help you. What can I do for you today?"
            )
        
        return []


class ActionHealthCheck(Action):
    """Health check action for Kubernetes probes"""

    def name(self) -> Text:
        return "action_health_check"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # This can be called by Kubernetes health checks
        # Return simple status without utterance
        return []