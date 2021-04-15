# from typing import Any, Text, Dict, List
# from rasa_sdk import Action, Tracker
# from rasa_sdk.events import SessionStarted, ActionExecuted




# class ActionSessionStart(Action):
#     def name(self) -> Text:
#         return "action_session_start"

#     async def run(
#       self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
#     ) -> List[Dict[Text, Any]]:
#         events = [SessionStarted()]

#         dispatcher.utter_message("c'est quoi votre email ?")


#         events.append(ActionExecuted("action_listen"))

#         # the session should begin with a `session_started` event and an `action_listen`
#         # as a user message follows
#         return events