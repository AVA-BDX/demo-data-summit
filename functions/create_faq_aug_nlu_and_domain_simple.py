#!/usr/bin/env python
#-*- coding: UTF-8 -*-

import pandas as pd
import ruamel.yaml
import yaml
path = r"data/qna_data_bases/questions_bot_augmente.csv"
data_base = pd.read_csv(path,  sep=";", encoding="latin3")
with open("data/nlu/faq-aug-nlu.yml", "wt", encoding="utf-8") as f:
    f.write('version: "2.0" \n')
    f.write('\n')
    f.write("nlu:\n")
    for num_pivot in range(1,len(set(data_base["id_question_pivot"]))+1):
        data_base_pivot = data_base.loc[data_base["id_question_pivot"]==num_pivot,]
        f.write("- intent: faq/" + str(num_pivot) + "\n")
        f.write("  examples: |\n")
        for row in range(len(data_base_pivot)):
            text = str(data_base_pivot.iloc[row,1])
            text = text.encode('utf8','ignore').decode('utf8').replace('\x92',"'").replace('\x9c','oe').replace('\x80','€').replace('\xa0',' ')
            f.write(f"    - {text}\n")
        f.write("\n")

path2 = r"data/qna_data_bases/reponses_bot_augmente.csv"
data_base = pd.read_csv(path2,  sep=";", encoding="latin3")
with open("data/all_domains/faq-aug-domain.yml", "wt", encoding="utf-8") as f:
    f.write('version: "2.0" \n')
    f.write('\n')
    f.write("intents:\n") 
    f.write("  - faq\n")
    f.write('\n')
    f.write('responses:\n')
    for num_pivot in range(1,len(set(data_base["id_question_pivot"]))+1):
        data_base_pivot = data_base.loc[data_base["id_question_pivot"]==num_pivot,]
        f.write("  utter_faq/" + str(num_pivot) +":" "\n")
        for row in range(len(data_base_pivot)):
            text = '"'+ str(data_base_pivot.iloc[row,1]) + '"'
            text = text.encode('utf8', 'ignore').decode().replace('\x92',"'").replace('\x9c','oe').replace('\x80','€').replace('\xa0',' ')
            f.write(f"    - text: {text}\n")
        f.write("\n")



# # #pas utile en local

# #merge des deux nlu
# #combiner les deux fichiers faq-domain.yml et od-domain.yml en commun de manière automatique
# #ouverture des deux fichiers yml
# #importation de faq-nlu.yml
# with open("data/nlu/faq-nlu.yml", 'rb') as stream:
#         faq_nlu_yml = yaml.load(stream)
# #importation de faq-aug-nlu.yml
# with open("data/nlu/faq-aug-nlu.yml", 'rb') as stream:
#         faq_aug_nlu_yml = yaml.load(stream) 
# #importation de nlu.yml
# with open("data/nlu/nlu.yml", 'rb') as stream:
#         nlu_yml = yaml.load(stream) 
# for num_pivot in range(0,len(set(data_base["id_question_pivot"]))):
#     faq_aug_nlu_yml['nlu'][num_pivot]['examples'] = faq_aug_nlu_yml['nlu'][num_pivot]['examples'] + faq_nlu_yml['nlu'][num_pivot]['examples'][:-1] 
#     faq_aug_nlu_yml['nlu'][num_pivot]['examples'] = faq_aug_nlu_yml['nlu'][num_pivot]['examples'].replace("-","").split("\n")
# faq_aug_nlu_yml['nlu'].extend(nlu_yml['nlu']) 
# for intent in range(len(set(data_base["id_question_pivot"])),len(nlu_yml['nlu']) + len(set(data_base["id_question_pivot"]))):
#     faq_aug_nlu_yml['nlu'][intent]['examples'] =   faq_aug_nlu_yml['nlu'][intent]['examples'][:-1].replace("-","").encode('utf8', 'ignore').decode().replace('\x92',"'").replace('\x9c','oe').replace('\x80','€').replace('\xa0',' ').split("\n")
# with open("data/nlu.yml", 'w', encoding = "utf-8") as stream:
#     ruamel.yaml.round_trip_dump(faq_aug_nlu_yml, stream, indent=2, block_seq_indent=0)   


