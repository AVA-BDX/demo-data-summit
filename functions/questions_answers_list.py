import pandas as pd
import json


path_responses = r"data/qna_data_bases/reponses_bot_augmente.csv"
data_base = pd.read_csv(path_responses,  sep=";", encoding="latin3")       
strored_all_bot_responses = [{str(num_pivot): [data_base.reponse_pivot[idx].encode('utf8','ignore').decode('utf8').replace('\x92',"'").replace('\x9c','oe').replace('\x80','€').replace('\xa0',' ') for idx in range(len(data_base.id_question_pivot)) if data_base.id_question_pivot[idx] == num_pivot]} for num_pivot in set(data_base.id_question_pivot)]
with open('data/qna_data_bases/strored_all_bot_responses.txt', 'w') as outfile:
    json.dump(strored_all_bot_responses, outfile)
    
    
path_question = r"data/qna_data_bases/questions_bot_augmente.csv"
data_base = pd.read_csv(path_question,  sep=";", encoding="latin3")    
strored_all_bot_questions = [{str(num_pivot): [data_base.reponse_prop[idx].encode('utf8','ignore').decode('utf8').replace('\x92',"'").replace('\x9c','oe').replace('\x80','€').replace('\xa0',' ') for idx in range(len(data_base.id_question_pivot)) if data_base.id_question_pivot[idx] == num_pivot]} for num_pivot in set(data_base.id_question_pivot)]
with open('data/qna_data_bases/strored_all_bot_questions.txt', 'w') as outfile:
    json.dump(strored_all_bot_questions, outfile)