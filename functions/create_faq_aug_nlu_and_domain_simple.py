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



# #pas utile

# #merge des deux nlu
# #combiner les deux fichiers faq-domain.yml et od-domain.yml en commun de manière automatique
# #ouverture des deux fichiers yml
# #importation de faq-domain.yml
# with open("data/nlu/faq-nlu.yml", 'rb') as stream:
#         faq_domain = yaml.load(stream)
# #importation de od-domain.yml
# with open("data/nlu/faq-aug-nlu.yml", 'rb') as stream:
#         od_domain = yaml.load(stream) 
# for num_pivot in range(0,len(set(data_base["id_question_pivot"]))):
#     od_domain['nlu'][num_pivot]['examples'] = od_domain['nlu'][num_pivot]['examples'] + faq_domain['nlu'][num_pivot]['examples'][:-1] 
#     od_domain['nlu'][num_pivot]['examples'] = od_domain['nlu'][num_pivot]['examples'].replace("-","").split("\n")
# with open("stand-and-aug-bot-nlu-merged.yml", 'w') as stream:
#     ruamel.yaml.round_trip_dump(od_domain, stream, indent=2, block_seq_indent=0)   

