
import logging
from typing import Any, Dict, List, Text, Optional
from rasa_sdk import Action,  Tracker
from rasa_sdk.types import DomainDict
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import AllSlotsReset, SlotSet, EventType, SessionStarted, ActionExecuted, Form
from rasa_sdk.forms import FormAction, FormValidationAction, REQUESTED_SLOT
import psycopg2
from psycopg2 import Error
from datetime import datetime
import random
import pandas as pd
import numpy as np





class ActionStoreAllBotResponses(Action):

    def name(self):
        return 'action_store_all_bot_responses'

    async def run(self, dispatcher, tracker, domain):
        """This action will map and store all the bot's responses at the begining of the first user's question"""

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
        """This action will store the last user faq question"""

        user_ongoin_message = tracker.latest_message['text']
        time_user_question = str(datetime.now())
        return [SlotSet("user_ongoin_message", user_ongoin_message),SlotSet("time_user_question", time_user_question)] 

class ActionGetUserCurentIntent(Action):
    """Returns the user's faq intent's number"""

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
        """ Reset the user's note to None"""

        return [SlotSet("note", None)]

class bot_outputs(Action):

    def name(self):
        return 'action_bot_last_message'

    def run(self, dispatcher, tracker, domain):
        """Get the bot last response"""

        user_intent = tracker.latest_message['intent'].get('name')
        
        bot_last_event = next(e for e in reversed(tracker.events) if e["event"] == "bot")
        bot_ongoin_message = bot_last_event['text']       
        time_bot_answer = str(datetime.now())
        if user_intent == "faq":
            return [SlotSet("bot_ongoin_message",bot_ongoin_message),SlotSet("bot_last_faq_message", bot_ongoin_message),SlotSet("time_bot_answer", time_bot_answer)]
        else:
            return [SlotSet("bot_ongoin_message", bot_ongoin_message),SlotSet("time_bot_answer", time_bot_answer)]

class ActionBotUterranceList(Action):

    def name(self):
        return 'action_bot_utterances_list'

    def run(self, dispatcher, tracker, domain):
        """Store every bot's faq responses during conversation in a non duplicated list"""

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
        """Records the user's question, the bot answer, 
        the times of the latest and the user's note in a database"""

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
            insert_query = """ INSERT INTO user_bot_augmented_recordings 
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
            cursor.execute("SELECT * from user_bot_augmented_recordings")
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
        """Check if the note given by the user is within 1 and 5"""

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
        """This action will reformulate bot answers when the user ask to reformulate and will adapt those answers to the user profile"""
        #get the user profile
        user_profile = tracker.get_slot('profile')

        # #get intent to make sure at least one faq question was asked befor user ask reformulate
        # intent = tracker.latest_message['intent'].get('name')

        #get bot faq response  to make sure that user has asked at least one faq queston
        bot_last_faq_response = tracker.get_slot('bot_last_faq_message')

        #recall conversation memory
        already_uttered_responses = tracker.get_slot('bot_utterances_list_slot')

        #if the user ask to reformulate before asking any faq question notify he didn't ask any question
        if bot_last_faq_response == None:
            dispatcher.utter_message(text = "Mais vous n'avez encore posé aucune question ^^' !")
            return [] 
            
        #bot_responses_to_user_question_json contains all bot utterances regarding the user sub-intent in a list of json
        bot_responses_to_user_question_json =  tracker.get_slot('strored_all_bot_responses')
        #get the user faq intent id
        user_current_intent_id = tracker.get_slot('user_current_intent_id')

        #get all responses for that id
        bot_responses_to_user_question = list([list_utters for list_utters in bot_responses_to_user_question_json if user_current_intent_id in list_utters.keys()][0].values())[0]
        #measure quantile to adapt responses to the user profile
        bot_responses_lengths = [len(utter) for utter in bot_responses_to_user_question]
        first_quantile = int(np.quantile(bot_responses_lengths, .25))
        third_quentile = int(np.quantile(bot_responses_lengths, .75))

        if user_profile == "short_utters":
            responses_idx = [idx for idx in range(len(bot_responses_lengths)) if bot_responses_lengths[idx] <= first_quantile]
            bot_responses_to_user_question = [bot_responses_to_user_question[idx] for idx in responses_idx]
            choice = "réponses courtes"
        elif user_profile == "long_utters":
            responses_idx = [idx for idx in range(len(bot_responses_lengths)) if bot_responses_lengths[idx] >= third_quentile]
            bot_responses_to_user_question = [bot_responses_to_user_question[idx] for idx in responses_idx]
            choice = "réponses longues"
        else:
            bot_responses_to_user_question = bot_responses_to_user_question
            choice = ""
        bot_allowed_utterances = [bot_utterance for bot_utterance in bot_responses_to_user_question if bot_utterance not in already_uttered_responses]
        if len(bot_allowed_utterances) > 0:
            Bot_chosed_utterance = bot_allowed_utterances[random.randint(0, len(bot_allowed_utterances) - 1)]
            dispatcher.utter_message(text = Bot_chosed_utterance)
            return [SlotSet("bot_reformulation", Bot_chosed_utterance )]
        else:
            Bot_chosed_utterance = f"😕 Désolé, par rapport à vos goûts ({choice}) Je n'ai plus d'autres reformulations pour cette question.\nVoulez vous quand même  que je vous propose une réponse que je vous ai déjà proposée ?"
            dispatcher.utter_message(text = Bot_chosed_utterance)
            return [Form(None)]

        return []



class ActionBotAdaptiveAnswer(Action):
    def name(self) -> Text:
        return "action_bot_adaptive_answer"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],

    ) -> List[EventType]:
        """This action will answers the user question adaptively to his profile"""
        #get the user profile
        user_profile = tracker.get_slot('profile')

        #bot_responses_to_user_question_json contains all bot utterances regarding the user sub-intent in a list of json
        bot_responses_to_user_question_json =  tracker.get_slot('strored_all_bot_responses')
        #get the user faq intent id
        user_current_intent_id = tracker.get_slot('user_current_intent_id')

        #get all responses for that id
        bot_responses_to_user_question = list([list_utters for list_utters in bot_responses_to_user_question_json if user_current_intent_id in list_utters.keys()][0].values())[0]
        #measure quantile to adapt responses to the user profile
        bot_responses_lengths = [len(utter) for utter in bot_responses_to_user_question]
        first_quantile = int(np.quantile(bot_responses_lengths, .25))
        third_quentile = int(np.quantile(bot_responses_lengths, .75))

        if user_profile == "short_utters":
            responses_idx = [idx for idx in range(len(bot_responses_lengths)) if bot_responses_lengths[idx] <= first_quantile]
            bot_responses_to_user_question = [bot_responses_to_user_question[idx] for idx in responses_idx]
        elif user_profile == "long_utters":
            responses_idx = [idx for idx in range(len(bot_responses_lengths)) if bot_responses_lengths[idx] >= third_quentile]
            bot_responses_to_user_question = [bot_responses_to_user_question[idx] for idx in responses_idx]
        else:
            bot_responses_to_user_question = bot_responses_to_user_question

        Bot_chosed_utterance = bot_responses_to_user_question[random.randint(0, len(bot_responses_to_user_question) - 1)]
        dispatcher.utter_message(text = Bot_chosed_utterance)

        return []




class ActionNoFortherReformulation(Action):
    def name(self) -> Text:
        return "action_no_further_reformulation"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[EventType]:
        """ This function will give an answer to the user among those the bot has already given 
        when there is no other/further reformulation and will adapt those answers based on the user's profile"""
        # #bot_responses_to_user_question_json contains all bot utterances regarding the user sub-intent in a list of json
        # # bot_responses_to_user_question_json =  tracker.get_slot('strored_all_bot_responses')
        # # user_current_intent_id = tracker.get_slot('user_current_intent_id')
        # # bot_responses_to_user_question = list([list_utters for list_utters in bot_responses_to_user_question_json if user_current_intent_id in list_utters.keys()][0].values())[0]
        # bot_responses_to_user_question  = tracker.get_slot('bot_utterances_list_slot')
        # Bot_chosed_utterance = bot_responses_to_user_question[random.randint(0, len(bot_responses_to_user_question) - 1)]
        Bot_chosed_utterance = tracker.get_slot('bot_reformulation')
        dispatcher.utter_message(text = Bot_chosed_utterance)

        return []



class ActionSetAndAcknowledgeProfile(Action):
    def name(self) -> Text:
        return "action_set_and_acknowledge_profile"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[EventType]:
        user_profile = tracker.latest_message['intent'].get('name')
        """ this function will set the user profile each time the user will inform on his profile"""

        #on determine le 1er quartile et le 3e quartile des nombres de caractere des reponses
        if user_profile == "short_utters":
            dispatcher.utter_message(text = "J'enregistre que vous aimez les réponses courtes")
            return [SlotSet("profile", "short_utters")]
        elif user_profile == "dont_care":
            dispatcher.utter_message(text = "J'enregistre que ça vous est égal")
            return [SlotSet("profile", "dont_care")]
        elif user_profile == "long_utters":
            dispatcher.utter_message(text = "J'enregistre que vous aimez les réponses détaillées")
            return [SlotSet("profile", "long_utters")]
        else:
            dispatcher.utter_message(text = "Je n'ai pas encore cerné votre profil")
            return [SlotSet("profile", None)]

        return []

