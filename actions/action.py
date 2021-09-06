
import logging
from typing import Any, Dict, List, Text, Optional
from rasa_sdk import Action,  Tracker
from rasa_sdk.types import DomainDict
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import AllSlotsReset, SlotSet, EventType, SessionStarted, ActionExecuted, Form, UserUtteranceReverted
from rasa_sdk.forms import FormAction, FormValidationAction, REQUESTED_SLOT
import psycopg2
from psycopg2 import Error
from datetime import datetime
import random
import pandas as pd
import numpy as np

import spacy
from collections import Counter
import math
nlp = spacy.load("fr_core_news_sm")

import pickle
from sklearn import preprocessing
import unicodedata
from fuzzywuzzy import fuzz

import json



class ActionSessionStart(Action):
    def name(self) :
        return "action_session_start"

    @staticmethod
    def fetch_slots(tracker: Tracker):
        """Collect slots that contain the user's name and phone number."""

        slots = []
        for key in ("name", "phone_number"):
            value = tracker.get_slot(key)
            if value is not None:
                slots.append(SlotSet(key=key, value=value))
        return slots

    async def run(
      self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        # the session should begin with a `session_started` event
        events = [SessionStarted()]

        dispatcher.utter_message(text="Message d'accueil pour voir comment cela fonctionne sur rasa X")

        # # an `action_listen` should be added at the end as a user message follows
        # events.append(ActionExecuted("action_listen"))

        return [UserUtteranceReverted(),Form("note_and_pseudo_asking_form")]



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
    def name(self) :
        return "action_utter_reformulate"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]

    ) -> List[EventType]:
        """This action will reformulate bot answers when the user ask to reformulate and will adapt those answers to the user profile"""
        #get the user profile
        user_profile = tracker.get_slot('profile')

        # #get intent to make sure at least one faq question was asked before user ask reformulate
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
                return [SlotSet("bot_reformulation", Bot_chosed_utterance ),]
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
    def name(self) :
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
        #get the user faq intent id
        user_current_intent_id = tracker.get_slot('user_current_intent_id')
        #get bot last_faq_message to check if at least one faq_message has been asked by the user
        bot_last_faq_message = tracker.get_slot('bot_last_faq_message')
        #get bot last_faq_message to check if at least one faq_message has been asked by the user
        user_ongoin_message = tracker.get_slot('user_ongoin_message')
        #get already given answers
        already_uttered_responses = tracker.get_slot('bot_utterances_list_slot')

        if bot_last_faq_message == None and user_ongoin_message == None:
            dispatcher.utter_message(text = "Je vous écoute pour votre question")
            return []

        elif user_current_intent_id == None:
            dispatcher.utter_message(response = "utter_give_more_details") # If the user doesn't choose anything among confusion'propositions (make sense when adaptive anwser comes after confusion)
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



class ActionNoFortherReformulation(Action):
    def name(self) :
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

        return [Form("note_and_pseudo_asking_form")]
    
class ActionAskAnotherQuestion(Action):
    def name(self) :
        return "action_ask_another_question"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[EventType]:
        """ This function will ask the user to ask another question"""
        
        dispatcher.utter_message(response ="utter_ask_another_question")

        return [Form("note_and_pseudo_asking_form")]



class ActionSetAndAcknowledgeProfile(Action):
    def name(self) :
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

    def name(self) :
        return "action_ask_for_clarification"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict,
    ) :
        #bot_responses_to_user_question_json contains all bot utterances regarding the user sub-intent in a list of json
        with open('data/qna_data_bases/strored_all_bot_responses.txt') as json_file:
            bot_responses_to_user_question_json = json.load(json_file)
        with open('data/qna_data_bases/strored_all_bot_questions.txt') as json_file:
            user_questions_to_bot_responses_json = json.load(json_file)

        intent_ranking = (
            tracker.latest_message.get("response_selector", {})
            .get("faq", {})
            .get("ranking", [])
        )
        if len(intent_ranking) > 1 :
            #user question not clear enough
            var_confidence = intent_ranking[0].get("confidence")
            if var_confidence < 0.7:
                dispatcher.utter_message(
                    response ="utter_dont_understand",
                    name= f"{round(100*var_confidence,2)} %"
                )              
            else:
                diff_intent_confidence = intent_ranking[0].get(
                    "confidence"
                ) - intent_ranking[1].get("confidence")
                #confusion case
                if diff_intent_confidence < 0.2:
                    intent_ranking = intent_ranking[:2]
                    #get questions ids
                    id1 = intent_ranking[0].get("intent_response_key").split("/")[1]
                    id2 = intent_ranking[1].get("intent_response_key").split("/")[1]

                    #get faq_1 2 key words
                    # phrase1 = list([list_utters for list_utters in bot_responses_to_user_question_json if id1 in list_utters.keys()][0].values())[0]
                    phrase1_q = list([list_utters for list_utters in user_questions_to_bot_responses_json if id1 in list_utters.keys()][0].values())[0]
                    # phrase1 = phrase1 + phrase1_q
                    s_id1 =  phrase1_q
                    N_id1 = len(s_id1)
                   
                    #get faq_2 2 key words
                    # phrase2 = list([list_utters for list_utters in bot_responses_to_user_question_json if id2 in list_utters.keys()][0].values())[0]
                    phrase2_q = list([list_utters for list_utters in user_questions_to_bot_responses_json if id2 in list_utters.keys()][0].values())[0]
                    # phrase2 = phrase2 + phrase2_q
                    s_id2 = phrase2_q
                    N_id2 = len(s_id2)

                    #transform quesitons list into spacy's set of docs
                    docs_1 = list(nlp.pipe(s_id1))
                    docs_2 = list(nlp.pipe(s_id2))
                    #get rid of useless strings in the sentences
                    id1_pur = [',  '.join([w.lemma_.lower() for w in doc if (not w.is_stop and not w.is_punct and not w.like_num and (w.pos_ not in ["VERB","ADJ","ADV","SPACE", "AUX","PRON", "ADP"]))]) for doc in docs_1]
                    id2_pur =  [',  '.join([w.lemma_.lower() for w in doc if (not w.is_stop and not w.is_punct and not w.like_num and (w.pos_ not in ["VERB","ADJ","ADV","SPACE", "AUX","PRON", "ADP"]))]) for doc in docs_2]

                    #get unique unique words in each set of questions for id1 and id2
                    #transform the list of sentences into single character
                    fulltext_id1 = ', '.join(id1_pur)
                    fulltext_id2 = ', '.join(id2_pur)

                    unique_word_id1 = list(set(fulltext_id1.split(",")))
                    unique_word_id1 = list(set([word.strip() for word in unique_word_id1]))

                    unique_word_id2 = list(set(fulltext_id2.split(",")))
                    unique_word_id2 = list(set([word.strip() for word in unique_word_id2]))

                    words_importance_id1 = []
                    words_importance_id2 = []

                    #Extract key word for id1 questions
                    for word in unique_word_id1:
                        nb_occur_word_id1 = len([list_w for list_w in id1_pur if word in list_w ])
                        nb_occur_word_id2 = len([list_w for list_w in id2_pur if word in list_w ])
                        words_importance_id1.append((nb_occur_word_id1/N_id1)*math.log(N_id2/(nb_occur_word_id2 + 1)))
                    Id1_key_word_idx = words_importance_id1.index(max(words_importance_id1))
                    Id1_key_word = unique_word_id1[Id1_key_word_idx]
                    
                    #Extract key word for id2 questions
                    for word in unique_word_id2:
                        nb_occur_word_id2 = len([list_w for list_w in id2_pur if word in list_w ])
                        nb_occur_word_id1 = len([list_w for list_w in id1_pur if word in list_w ])
                        words_importance_id2.append((nb_occur_word_id2/N_id2)*math.log(N_id1/(nb_occur_word_id1 + 1)))
                    Id2_key_word_idx = words_importance_id2.index(max(words_importance_id2))
                    Id2_key_word = unique_word_id2[Id2_key_word_idx]
                    
                    
                    #create buttons titles
                    title_1 = f"{Id1_key_word}"
                    title_2 = f"{Id2_key_word}"
                   
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
                    # elif user_current_intent_id == None:
                    #     dispatcher.utter_message(response ="utter_give_more_details")
                    #     return []
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
    def name(self):
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
            return [SlotSet("user_current_intent_id", tracker.get_slot('confusion_2_id'))]
        elif ((confusion_intent == "non_sense") or (tracker.get_slot('droit'))):
            return [SlotSet("user_current_intent_id", None)]
        else:
            return [SlotSet("user_current_intent_id", None)]
        return []

class ActionIncrementIncomprehensionConfusion(Action):
    def name(self) :
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
            if intent_ranking[0].get("confidence") < 0.7:
                var_bot_question_incomprehension = 1
            else:
                diff_intent_confidence = intent_ranking[0].get(
                    "confidence"
                ) - intent_ranking[1].get("confidence")                          
                if diff_intent_confidence < 0.2:
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
    def name(self) :
        return "action_set_confusion_slot_to_none"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],

    ) -> List[EventType]:
        """This action will set the slot named confusion to None"""
   
        return [SlotSet("confusion", None)]


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