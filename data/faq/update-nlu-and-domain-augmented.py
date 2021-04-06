#!/usr/bin/env python
#-*- coding: UTF-8 -*-

import pandas as pd
#import unicodedata
path = r"data/data-base-source/QNA_for_bots_entites.csv"
data_base = pd.read_csv(path,  sep=";", encoding="latin3")
with open("data/nlu/faq-nlu.yml", "wt", encoding="utf-8") as f:
    f.write('version: "2.0" \n')
    f.write('\n')
    f.write("nlu:\n")
    for num_pivot in range(1,len(data_base)+1):
        data_base_pivot = data_base.loc[data_base["id_question_pivot"]==num_pivot,]
        f.write("- intent: faq/" + str(num_pivot) + "\n")
        f.write("  examples: |\n")
        for row in range(len(data_base_pivot)):
            text = str(data_base_pivot.iloc[row,1])
            key_word = str(data_base_pivot.iloc[row,3]) 
            entity_name = str(data_base_pivot.iloc[row,4]) 
            text = text.encode('utf8','ignore').decode('utf8').replace('\x92',"'").replace('\x9c','oe').replace('\x80','€')
            if (key_word in text) == True:
                entity_detected =f"[{key_word}]"+'('+ f"{entity_name}" +")"
                text = text.replace(key_word, entity_detected)
            f.write(f"   - {text}\n")
        f.write("\n")
        

   
with open("data/faq/faq-domain.yml", "wt", encoding="utf-8") as f:
    f.write('version: "2.0" \n')
    f.write('\n')
    f.write("intents:\n")
    f.write("  - faq\n")
    f.write('\n')
    f.write("entities:\n")
    for indiv_entity in  sorted(list(set(data_base.iloc[:,4]))):
        f.write(f"  - {indiv_entity}\n")
    f.write("\n")
    f.write('responses:\n')
    for num_pivot in range(1,len(data_base)+1):
        data_base_pivot = data_base.loc[data_base["id_question_pivot"]==num_pivot,]
        f.write("  utter_faq/" + str(num_pivot) +":" "\n")
        for row in range(len(data_base_pivot)):
            text = '"'+ str(data_base_pivot.iloc[row,2]) + '"'
            text = text.encode('utf8', 'ignore').decode().replace('\x92',"'").replace('\x9c','oe').replace('\x80','€')
            f.write(f"    - text: {text}\n")
        f.write("\n")

import ruamel.yaml
import yaml
#combiner les deux fichiers faq-domain.yml et od-domain.yml en commun de manière automatique
#ouverture des deux fichiers yml
#importation de faq-domain.yml
with open("data/domain/faq-domain.yml", 'rb') as stream:
        faq_domain = yaml.load(stream)
#importation de od-domain.yml
with open("data/domain/od-domain.yml", 'rb') as stream:
        od_domain = yaml.load(stream) 
#generating the new domain.yml file
domain_yaml = {'version': '2.0'}
domain_yaml['intents'] = faq_domain['intents'] + od_domain['intents']
domain_yaml['entities'] = faq_domain['entities'] 
domain_yaml['responses'] = {**od_domain['responses'] , **faq_domain['responses']}
domain_yaml['session_config'] = {'session_expiration_time': 60, 'carry_over_slots_to_new_session': False}
with open("domain.yml", 'w') as stream:
    ruamel.yaml.round_trip_dump(domain_yaml, stream, indent=4, block_seq_indent=2)