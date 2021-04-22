
import logging
from typing import Any, Dict, List, Text, Optional
from rasa_sdk import Action,  Tracker
from rasa_sdk.types import DomainDict
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import AllSlotsReset, SlotSet, EventType, SessionStarted, ActionExecuted
from rasa_sdk.forms import FormAction, FormValidationAction, REQUESTED_SLOT
import psycopg2
from psycopg2 import Error
from datetime import datetime
import random
import pandas as pd





class ActionStoreAllBotResponses(Action):

    def name(self):
        return 'action_store_all_bot_responses'

    def run(self, dispatcher, tracker, domain):
        path = r"data/qna_data_bases/reponses_bot_augmente.csv"
        data_base = pd.read_csv(path,  sep=";", encoding="latin3")       
        test_if_all_responses_was_stored = tracker.get_slot('strored_all_bot_responses')
        if test_if_all_responses_was_stored == None:
            strored_all_bot_responses = [{str(num_pivot): [data_base.reponse_pivot[idx].encode('utf8','ignore').decode('utf8').replace('\x92',"'").replace('\x9c','oe').replace('\x80','€').replace('\xa0',' ') for idx in range(len(data_base.id_question_pivot)) if data_base.id_question_pivot[idx] == num_pivot]} for num_pivot in set(data_base.id_question_pivot)]
            return [SlotSet("strored_all_bot_responses", strored_all_bot_responses)]
        else:
            return [] 

class user_inputs(Action):

    def name(self):
        return 'action_user_last_message'

    def run(self, dispatcher, tracker, domain):
        user_ongoin_message = tracker.latest_message['text']
        time_user_question = str(datetime.now())
        return [SlotSet("user_ongoin_message", user_ongoin_message),SlotSet("time_user_question", time_user_question)] 

class ActionGetUserCurentIntent(Action):
    """Returns the chitchat utterance dependent on the intent"""

    def name(self) -> Text:
        return "action_get_user_curent_intent"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict,
    ) -> List[EventType]:
        full_intent = (
            tracker.latest_message.get("response_selector", {})
            .get("faq", {})
            .get("response", {})
            .get("intent_response_key")
        )
        # response_selector_content = str((
        #     tracker.latest_message.get("response_selector", {})
        # ))
        if full_intent:
            user_current_intent_id = full_intent.split("/")[1]
        else:
            user_current_intent_id = None
        # return [SlotSet("user_current_intent", user_current_intent),SlotSet("response_selector_content", response_selector_content)]
        return [SlotSet("user_current_intent_id", user_current_intent_id)]

class reset_note(Action):

    def name(self):
        return 'user_note_to_none'

    def run(self, dispatcher, tracker, domain):
        return [SlotSet("note", None)]

class bot_outputs(Action):

    def name(self):
        return 'action_bot_last_message'

    def run(self, dispatcher, tracker, domain):
        bot_last_event = next(e for e in reversed(tracker.events) if e["event"] == "bot")
        bot_ongoin_message = bot_last_event['text']       
        time_bot_answer = str(datetime.now())
        return [SlotSet("bot_ongoin_message", bot_ongoin_message),SlotSet("time_bot_answer", time_bot_answer)]

class ActionBotUterranceList(Action):

    def name(self):
        return 'action_bot_utterances_list'

    def run(self, dispatcher, tracker, domain):
        actual_list_responses = tracker.get_slot('bot_utterances_list_slot')
        bot_ongoin_message = tracker.get_slot('bot_ongoin_message')
        bot_reformulation = tracker.get_slot('bot_reformulation')

        bot_utterances_list_slot = []
        if actual_list_responses == None:
            if bot_reformulation == None:
                bot_utterances_list_slot = [bot_ongoin_message.replace("\xa0"," ")]
            else:
                bot_utterances_list_slot = [bot_ongoin_message.replace("\xa0"," ")] + [bot_reformulation.replace("\xa0"," ")]
        else:
            bot_utterances_list_slot = tracker.get_slot('bot_utterances_list_slot')
            if bot_reformulation == None:
                bot_utterances_list_slot = bot_utterances_list_slot + [bot_ongoin_message.replace("\xa0"," ")] 
            else:
                bot_utterances_list_slot = bot_utterances_list_slot + [bot_ongoin_message.replace("\xa0"," ")] + [bot_reformulation.replace("\xa0"," ")]

        return [SlotSet("bot_utterances_list_slot", list(set(bot_utterances_list_slot)) )]
    

class Record_user_note(Action):

    def name(self):
        return 'action_record_the_user_note'      

    def run(self, dispatcher, tracker, domain):

        user_question = tracker.get_slot('user_ongoin_message')
        bot_answer = tracker.get_slot('bot_ongoin_message')
        user_note = tracker.get_slot('note')
        time_user_question = datetime.strptime(tracker.get_slot('time_user_question'), "%Y-%m-%d %H:%M:%S.%f") 
        time_bot_answer = datetime.strptime(tracker.get_slot('time_bot_answer'), "%Y-%m-%d %H:%M:%S.%f")    
        try:
            # Connect to an existing database
            connection = psycopg2.connect(user="civadev",
                                        password="civa",
                                        host="35.192.219.219",
                                        port="5432",
                                        database="civadatabases")
            # Create a cursor to perform database operations
            cursor = connection.cursor()
            # Executing a SQL query to insert data into  table
            insert_query = """ INSERT INTO user_bot_recordings_lao 
            (user_question,
            bot_answer, 
            user_note,
            time_user_question, 
            time_bot_answer) VALUES 
            (%s, %s, %s, %s, %s);"""
            item_tuple = (user_question,
                        bot_answer,
                        user_note,
                        time_user_question,
                        time_bot_answer)
            cursor.execute(insert_query, item_tuple)
            connection.commit()
            print("1 Record inserted successfully")
            # Fetch result
            cursor.execute("SELECT * from user_bot_recordings_lao")
            record = cursor.fetchall()
            print("Result ", record)
        except (Exception, Error) as error:
            print("Error while connecting to PostgreSQL", error)
        finally:
            if (connection):
                cursor.close()
                connection.close()
                print("PostgreSQL connection is closed") 

        dispatcher.utter_message(f"vous avez donné la note de {user_note} à la question.") 

        return [] 

class validatenoteForm(FormValidationAction):

    def name(self):
        return 'validate_note_asking_form'

    def validate_note(self, slot_value, dispatcher, tracker, domain):

        if str(slot_value) in ["1","2","3","4","5"]:
            return {"note": slot_value}
        else:
            dispatcher.utter_message("veuillez renseigner une valeur entre 1 et 5")
            return {"note": None}

class bot_reformulate(Action):
    def name(self) -> Text:
        return "action_utter_reformulate"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[EventType]:
    
        already_uttered_responses = tracker.get_slot('bot_utterances_list_slot')

        #bot_responses_to_user_question_json contains all bot utterances regarding the user sub-intent in a list of json
        bot_responses_to_user_question_json =  tracker.get_slot('strored_all_bot_responses')
        user_current_intent_id = tracker.get_slot('user_current_intent_id')

        bot_responses_to_user_question = list([list_utters for list_utters in bot_responses_to_user_question_json if user_current_intent_id in list_utters.keys()][0].values())[0]

        bot_allowed_utterances = [bot_utterance for bot_utterance in bot_responses_to_user_question if bot_utterance not in already_uttered_responses]

        
        if len(bot_allowed_utterances) > 0:
            Bot_chosed_utterance = bot_allowed_utterances[random.randint(0, len(bot_allowed_utterances) - 1)]
            dispatcher.utter_message(text = Bot_chosed_utterance)
            return [SlotSet("bot_reformulation", Bot_chosed_utterance )]
        else:
            Bot_chosed_utterance = "Désolé, Je n'ai plus d'autre reformulations de votre question"
            dispatcher.utter_message(text = Bot_chosed_utterance)
        return []