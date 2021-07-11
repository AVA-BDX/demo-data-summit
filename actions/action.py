
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
import nltk
from nltk.corpus import stopwords
from nltk import word_tokenize

import pickle
from sklearn import preprocessing
import unicodedata
from fuzzywuzzy import fuzz

import json




# class ActionStoreAllBotResponses(Action):

#     def name(self):
#         return 'action_store_all_bot_responses'

#     async def run(self, dispatcher, tracker, domain):
#         """This action will map and store all the bot's responses at the begining of the first user's question"""

#         path = r"data/qna_data_bases/reponses_bot_augmente.csv"
#         data_base = pd.read_csv(path,  sep=";", encoding="latin3")       
#         test_if_all_responses_was_stored = tracker.get_slot('strored_all_bot_responses')
#         if test_if_all_responses_was_stored == None:
#             strored_all_bot_responses = [{str(num_pivot): [data_base.reponse_pivot[idx].encode('utf8','ignore').decode('utf8').replace('\x92',"'").replace('\x9c','oe').replace('\x80','€').replace('\xa0',' ') for idx in range(len(data_base.id_question_pivot)) if data_base.id_question_pivot[idx] == num_pivot]} for num_pivot in set(data_base.id_question_pivot)]
#             return [SlotSet("strored_all_bot_responses", strored_all_bot_responses)]
#         else:
#             return [] 

# class ActionStoreAllBotQuesstions(Action):

#     def name(self):
#         return 'action_store_all_bot_questions'

#     async def run(self, dispatcher, tracker, domain):
#         """This action will map and store all the bot's responses at the begining of the first user's question"""

#         path = r"data/qna_data_bases/questions_bot_augmente.csv"
#         data_base = pd.read_csv(path,  sep=";", encoding="latin3")       
#         test_if_all_questions_was_stored = tracker.get_slot('strored_all_bot_questions')
#         if test_if_all_questions_was_stored == None:
#             strored_all_bot_questions = [{str(num_pivot): [data_base.reponse_prop[idx].encode('utf8','ignore').decode('utf8').replace('\x92',"'").replace('\x9c','oe').replace('\x80','€').replace('\xa0',' ') for idx in range(len(data_base.id_question_pivot)) if data_base.id_question_pivot[idx] == num_pivot]} for num_pivot in set(data_base.id_question_pivot)]
#             return [SlotSet("strored_all_bot_questions", strored_all_bot_questions)]
#         else:
#             return [] 

class user_inputs(Action):

    def name(self):
        return 'action_user_last_message'

    async def run(self, dispatcher, tracker, domain):
        """This action will store the last user faq question"""

        user_ongoin_message = tracker.latest_message['text']
        time_user_question = str(datetime.now())
        return [SlotSet("user_ongoin_message", user_ongoin_message),SlotSet("time_user_question", time_user_question)] 

class ActionGetUserCurentIntent(Action):
    """Returns the user's faq intent's number"""

    def name(self) -> Text:
        return "action_get_user_curent_intent"

    async def run(
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

        return [SlotSet("note", None),SlotSet("user_wants_details",0)]

class bot_outputs(Action):

    def name(self):
        return 'action_bot_last_message'

    async def run(self, dispatcher, tracker, domain):
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

    async def run(self, dispatcher, tracker, domain):
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

        intent_ranking = (
            tracker.latest_message.get("response_selector", {})
            .get("faq", {})
            .get("ranking", [])
        )       
        question_id = tracker.get_slot('user_current_intent_id')
        user_question = tracker.get_slot('user_ongoin_message')
        pseudo = tracker.get_slot('pseudo')
        bot_answer = tracker.get_slot('bot_ongoin_message')
        user_note = tracker.get_slot('note')
        time_user_question = datetime.strptime(tracker.get_slot('time_user_question'), "%Y-%m-%d %H:%M:%S.%f") 
        time_bot_answer = datetime.strptime(tracker.get_slot('time_bot_answer'), "%Y-%m-%d %H:%M:%S.%f")    
        bot_question_confusion =  tracker.get_slot('bot_question_confusion')
        bot_question_incomprehension =  tracker.get_slot('bot_question_incomprehension')
        user_wants_details = tracker.get_slot('user_wants_details')
        bot_confid_to_user_question = intent_ranking[0].get("confidence")
        
        try:
            # Connect to an existing database (should put these in a config file for more safe)
            connection = psycopg2.connect(user="civadev",
                                        password="civa",
                                        host="20.199.107.202",
                                        port="5432",
                                        database="postgres")
            # Create a cursor to perform database operations
            cursor = connection.cursor()
            # Executing a SQL query to insert data into  table
            insert_query = """ INSERT INTO user_bot_augmented_recordings 
            (pseudo,
            question_id,
            user_question,
            bot_answer,
            bot_confid_to_user_question, 
            user_note,
            time_user_question, 
            time_bot_answer,
            bot_question_confusion,
            bot_question_incomprehension,
            user_wants_details) VALUES 
            (%s, %s, %s, %s, %s, %s, %s, %s,%s,%s,%s);"""
            item_tuple = (pseudo,
                        question_id,
                        user_question,
                        bot_answer,
                        bot_confid_to_user_question,
                        user_note,
                        time_user_question,
                        time_bot_answer,
                        bot_question_confusion,
                        bot_question_incomprehension,
                        user_wants_details)
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

    async def required_slots(
        self,
        slots_mapped_in_domain: List[Text],
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict"
    ) -> List[Text]:
        if tracker.get_slot("pseudo2") is True:
            return ["note"]
        else:
            return ["note", "pseudo"]

    def validate_note(self, slot_value, dispatcher, tracker, domain):
        """Check if the note given by the user is within 1 and 5"""

        if str(slot_value) in ["1","2","3","4","5"]:
            return {"note": slot_value}
        else:
            dispatcher.utter_message("veuillez renseigner une valeur entre 1 et 5")
            return {"note": None}

    def validate_pseudo(self, slot_value, dispatcher, tracker, domain):
        """Check if the user pseudo already exists"""

        
        try:
            # Connect to an existing database (should put these in a config file for more safe)
            connection = psycopg2.connect(user="civadev",
                                        password="civa",
                                        host="20.199.107.202",
                                        port="5432",
                                        database="postgres")
            # Create a cursor to perform database operations
            cursor = connection.cursor()
            cursor.execute("SELECT pseudo from user_bot_augmented_recordings")
            record = cursor.fetchall()
            pseudos = list(set(list(pd.DataFrame(record)[0].values)))
        except (Exception, Error) as error:
            print("Error while connecting to PostgreSQL", error)
        finally:
            if (connection):
                cursor.close()
                connection.close()
                print("PostgreSQL connection is closed")
                
        if slot_value not in pseudos:
            return {"pseudo": slot_value, "pseudo2" : slot_value}
        else:
            dispatcher.utter_message("Ce pseudo existe déjà. Veuillez en renseigner un autre s'il vous plait.")
            return {"pseudo": None}


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
        else:   
            #bot_responses_to_user_question_json contains all bot utterances regarding the user sub-intent in a list of json
            with open('data/qna_data_bases/strored_all_bot_responses.txt') as json_file:
                bot_responses_to_user_question_json = json.load(json_file)
            #bot_responses_to_user_question_json =  tracker.get_slot('strored_all_bot_responses')
            #get the user faq intent id
            user_current_intent_id = tracker.get_slot('user_current_intent_id')

            if user_current_intent_id == None:
                dispatcher.utter_message(text = "Difficile de reformuler une réponse, à partir d'une question non comprise ^^'")

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
                if choice != "":
                    Bot_chosed_utterance = f"😕 Désolé, par rapport à vos goûts ({choice}) je n'ai plus d'autres reformulations pour cette question.\nVoulez vous quand même  que je vous propose une réponse que je vous ai déjà proposée ?"
                    dispatcher.utter_message(text = Bot_chosed_utterance)
                    return [Form(None)]
                else:
                    Bot_chosed_utterance = f"😕 Désolé, je n'ai plus d'autres reformulations pour cette question.\nVoulez vous quand même  que je vous propose une réponse que je vous ai déjà proposée ?"
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
        with open('data/qna_data_bases/strored_all_bot_responses.txt') as json_file:
            bot_responses_to_user_question_json = json.load(json_file)       
        #bot_responses_to_user_question_json =  tracker.get_slot('strored_all_bot_responses')
        #get the user faq intent id
        user_current_intent_id = tracker.get_slot('user_current_intent_id')
        #get bot last_faq_message to check if at least one faq_message has been asked by the user
        bot_last_faq_message = tracker.get_slot('bot_last_faq_message')
        #get bot last_faq_message to check if at least one faq_message has been asked by the user
        user_ongoin_message = tracker.get_slot('user_ongoin_message')

        if bot_last_faq_message == None and user_ongoin_message == None:
            dispatcher.utter_message(text = "Je vous écoute pour votre question")
            return []

        elif user_current_intent_id == None:
            dispatcher.utter_message(template="utter_dont_understand")
            return []
        else:
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
            return [SlotSet("profile", "long_utters"),SlotSet("user_wants_details",1)]
        else:
            dispatcher.utter_message(text = "Je n'ai pas encore cerné votre profil")
            return [SlotSet("profile", None)]

        return []

        


class ActionAskClarification(Action):
    """Asks for a clarification if confusion between two intentions"""

    def name(self) -> Text:
        return "action_ask_for_clarification"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict,
    ) -> List[EventType]:
        #bot_responses_to_user_question_json contains all bot utterances regarding the user sub-intent in a list of json
        with open('data/qna_data_bases/strored_all_bot_responses.txt') as json_file:
            bot_responses_to_user_question_json = json.load(json_file)
        #bot_responses_to_user_question_json =  tracker.get_slot('strored_all_bot_responses') 
        with open('data/qna_data_bases/strored_all_bot_responses.txt') as json_file:
            user_questions_to_bot_responses_json = json.load(json_file)
        #user_questions_to_bot_responses_json =  tracker.get_slot('strored_all_bot_questions')

        french_stopwords = set(stopwords.words('french'))
        filtre_stopfr =  lambda text: [token for token in text if token.lower() not in french_stopwords]
        ponctuations = [",",".","?","[","]","(",")","{","}",";","!",":","/","'","-","_","«","»"]
        
        intent_ranking = (
            tracker.latest_message.get("response_selector", {})
            .get("faq", {})
            .get("ranking", [])
        )
        if len(intent_ranking) > 1 :
            #user question not clear enough
            if intent_ranking[0].get("confidence")<0.4:
                dispatcher.utter_message(text= f"Pouvez vous apporter plus de détails s'il vous plait ? \n je n'ai compris que {round(100*intent_ranking[0].get('confidence'),2)}% de ce que vous avez dit ^^'" )
                return []
            else:
                diff_intent_confidence = intent_ranking[0].get(
                    "confidence"
                ) - intent_ranking[1].get("confidence")
                #confusion case
                if diff_intent_confidence < 0.5:
                    intent_ranking = intent_ranking[:2]
                    #get questions ids
                    id1 = intent_ranking[0].get("intent_response_key").split("/")[1]
                    id2 = intent_ranking[1].get("intent_response_key").split("/")[1]

                    #get faq_1 2 key words
                    # phrase1 = list([list_utters for list_utters in bot_responses_to_user_question_json if id1 in list_utters.keys()][0].values())[0]
                    phrase1_q = list([list_utters for list_utters in user_questions_to_bot_responses_json if id1 in list_utters.keys()][0].values())[0]
                    # phrase1 = phrase1 + phrase1_q
                    phrase1 =  phrase1_q
                    phrase1_to_one_str = ', '.join(phrase1)
                    for ponc in ponctuations:
                        phrase1_to_one_str = phrase1_to_one_str.replace(ponc," ")
                    words_phrase1 = filtre_stopfr( word_tokenize(phrase1_to_one_str, language="french") )
                    words_phrase1 = [word for word in words_phrase1 if len(word) > 3]
                    words_phrase1_copy = words_phrase1
                    count_phrase1 = [phrase1_to_one_str.count(word) for word in list(set(words_phrase1))]
                    max_count_phrase1_idx = count_phrase1.index(max(count_phrase1))
                    phrase1_key_word = list(set(words_phrase1))[max_count_phrase1_idx]

                    words_phrase1 = [word for word in  words_phrase1 if  word != phrase1_key_word] 
                    count_phrase1 = [phrase1_to_one_str.count(word) for word in list(set(words_phrase1))]
                    max_count_phrase1_idx = count_phrase1.index(max(count_phrase1))
                    phrase1_key_word2 = list(set(words_phrase1))[max_count_phrase1_idx]

                    #get faq_2 2 key words
                    # phrase2 = list([list_utters for list_utters in bot_responses_to_user_question_json if id2 in list_utters.keys()][0].values())[0]
                    phrase2_q = list([list_utters for list_utters in user_questions_to_bot_responses_json if id2 in list_utters.keys()][0].values())[0]
                    # phrase2 = phrase2 + phrase2_q
                    phrase2 = phrase2_q
                    phrase2_to_one_str = ', '.join(phrase2)
                    for ponc in ponctuations:
                        phrase2_to_one_str = phrase2_to_one_str.replace(ponc," ")                
                    words_phrase2 = filtre_stopfr( word_tokenize(phrase2_to_one_str, language="french") )
                    words_phrase2 = [word for word in words_phrase2 if len(word) > 3 and word not in words_phrase1_copy]
                    count_phrase2 = [phrase2_to_one_str.count(word) for word in list(set(words_phrase2))]
                    max_count_phrase2_idx = count_phrase2.index(max(count_phrase2))
                    phrase2_key_word = list(set(words_phrase2))[max_count_phrase2_idx]

                    words_phrase2 = [word for word in  words_phrase2 if  word != phrase2_key_word] 
                    count_phrase2 = [phrase2_to_one_str.count(word) for word in list(set(words_phrase2))]
                    max_count_phrase2_idx = count_phrase2.index(max(count_phrase2))
                    phrase2_key_word2 = list(set(words_phrase2))[max_count_phrase2_idx]

                    #create buttons titles
                    title_1 = f"{phrase1_key_word},{phrase1_key_word2}"
                    title_2 = f"{phrase2_key_word},{phrase2_key_word2}"
                   
                    message_title = (
                        "Pardon, je ne suis pas sur d'avoir bien compris 🤔 "  "me parlez-vous de..."
                    )
                    buttons = []

                    buttons.append({"title": title_1, "payload": f"/confusion_1"})                   
                    buttons.append({"title": title_2, "payload": f"/confusion_2"})  
                    buttons.append({"title": "autre", "payload": f"/non_sense"})

                    dispatcher.utter_message(text=message_title, buttons=buttons)
                    return [SlotSet("confusion_1_id", id1),SlotSet("confusion_2_id", id2), SlotSet("confusion", True)]
                #no confison case
                else:
                    #get the user profile
                    user_profile = tracker.get_slot('profile')

                    #get the user faq intent id
                    user_current_intent_id = tracker.get_slot('user_current_intent_id')
                    #get bot last_faq_message to check if at least one faq_message has been asked by the user
                    bot_last_faq_message = tracker.get_slot('bot_last_faq_message')
                    #get bot last_faq_message to check if at least one faq_message has been asked by the user
                    user_ongoin_message = tracker.get_slot('user_ongoin_message')                  

                    if bot_last_faq_message == None and user_ongoin_message == None:
                        dispatcher.utter_message(text="Je vous écoute pour votre question")
                        return []
                    elif user_current_intent_id == None:
                        dispatcher.utter_message(template="utter_dont_understand")
                        return []
                    else:
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

class ActionSetFaqConfusionId(Action):
    def name(self) -> Text:
        return "action_set_faq_confusion_id"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[EventType]:
        """ this function will indicate what to do after a clarification has been choosen"""

        #get confusion ids
        confusion_intent = tracker.latest_message['intent'].get('name')
        #on determine le 1er quartile et le 3e quartile des nombres de caractere des reponses
        if ((confusion_intent == "confusion_1") or (tracker.get_slot('gauche'))):
            return [SlotSet("user_current_intent_id", tracker.get_slot('confusion_1_id'))]
        elif ((confusion_intent == "confusion_2") or (tracker.get_slot('milieu'))):
            dispatcher.utter_message(text = "J'enregistre que ça vous est égal")
            return [SlotSet("user_current_intent_id", tracker.get_slot('confusion_2_id'))]
        elif ((confusion_intent == "non_sense") or (tracker.get_slot('droit'))):
            return [SlotSet("user_current_intent_id", None)]
        else:
            return [SlotSet("user_current_intent_id", None)]
        return []

class ActionIncrementIncomprehensionConfusion(Action):
    def name(self) -> Text:
        return "action_increment_confusion_incomprehension"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict):
        intent_ranking = (
        tracker.latest_message.get("response_selector", {})
        .get("faq", {})
        .get("ranking", [])
        )
        var_bot_question_incomprehension = 0
        var_bot_question_confusion = 0
        if len(intent_ranking) > 1 :
            if intent_ranking[0].get("confidence") < 0.4:
                var_bot_question_incomprehension = 1
            elif 0.4 <= intent_ranking[0].get("confidence") <= 0.6:
                var_bot_question_confusion = 1
        return [SlotSet("bot_question_incomprehension", var_bot_question_incomprehension),SlotSet("bot_question_confusion", var_bot_question_confusion) ]



# class TriggerNoteForm(Action):
#     def name(self) -> Text:
#         return "action_trigger_note_form"

#     async def run(
#         self,
#         dispatcher: CollectingDispatcher,
#         tracker: Tracker,
#         domain: Dict[Text, Any],

#     ) -> List[EventType]:
#         """This action will trigger the note_asking_form """
      
#         return [Form("note_asking_form")] 
       
            

class SetConfusionSlotToNone(Action):
    def name(self) -> Text:
        return "action_set_confusion_slot_to_none"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],

    ) -> List[EventType]:
        """This action will set the slot named confusion to None"""
   
        return [SlotSet("confusion", None), SlotSet("user_wants_details", 0)]


# class ActionRecommendationAlgo(Action):

#     def __init__(self) -> None:
#         self.roles = ['administrateur', 'developpeur', 'manager']
#         self.materilasList = ['adminAccess',
#         'calendarAccess',
#         'clavier',
#         'devTools',
#         'ordinateur',
#         'smartphone',
#         'souris',
#         'vsCode']


#     def name(self) -> Text:
#         return "action_recommendation_algo"

    
#     def distance_phrases(self,phrase1, phrase2):
#         """
#             cette fonction calcule la distance de Levenshtein 
#             tres amélioree entre deux phrases
#         """
#         """
#             lev.ratio
#             fuzz.ratio
#             fuzz.partial_ratio
#             fuzz.token_sort_ratio
#             fuzz.token_set_ratio
        
#         """
#         #creation d'une fonction lambda qui transforme en minuscule et enleve les espaces
#         minusculeSansEspace = lambda x: x.lower().strip()
#         #creation d'une fonction qui enleve les accens
#         enleveurAccent = lambda x:unicodedata.normalize('NFKD', x).encode('ASCII', 'ignore').decode("utf-8") 
#         #Application des fonctions aux mots a comparer
#         phrase1 = enleveurAccent(minusculeSansEspace(phrase1))
#         phrase2 = enleveurAccent(minusculeSansEspace(phrase2))
#         return fuzz.token_set_ratio(phrase1,phrase2)

#     def extractKeyWords(self,givenEntitiesList,searchedEntitiesList):
#         """
#         extrait les mots de searchedEntitiesList presents dans givenEntitiesList
#         des lors que leurs ration de Levenshtein est suffisament grande <=> distance petite
#         """
#         extractedWords = []
#         for wordChecked in givenEntitiesList:
#             foundOrNot = [words for words in searchedEntitiesList if self.distance_phrases(words, wordChecked) > 80]
#             if len(foundOrNot) == 0:
#                 next
#             else:
#                 extractedWords.extend(foundOrNot)
#         return list(set(extractedWords))       

#     def convertToDigit(self,givenEntitiesList,searchedEntitiesList):
#         """
#         description : 
#             fonction that takes two lists of texts as parameters
#             (givenEntitiesList and searchedEntitiesList) and send back a binary vector 
#             of length #searchedEntitesList that indicates whether (1) or not (0) 
#             searchedEntitiesList texts are contained in givenEntitiesList ones
#         Parametres : 
#             givenEntitiesList : list of texts in which to look
#             searchedEntitiesList : list of texts looked for
#         Resultat : binary (0,1) vector of length #searchedEntitesList
#         """
#         lambdachecker = lambda x,y: 1 if x in y else 0
#         checkVector = [lambdachecker(searchedEntity, givenEntitiesList) for searchedEntity in  searchedEntitiesList]
#         return checkVector       

#     def transfoInput(self,inputUser):
#         """
#         Transforme l'input de l'utilisateur (liste de mots ou texte contenant les mots)
#         en un format reconnaissable et predictible par le model
#         """
#         #definition des materiels
    
#         Xnew = pd.DataFrame(columns = self.materilasList)
#         Xnew.loc[len(Xnew)] = self.convertToDigit(inputUser, self.materilasList )
#         return Xnew


#     async def run(
#         self,
#         dispatcher: Collecting