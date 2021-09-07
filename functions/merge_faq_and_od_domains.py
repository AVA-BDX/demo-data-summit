#!/usr/bin/env python
#-*- coding: UTF-8 -*-

import ruamel.yaml
import yaml
#combiner les deux fichiers faq-domain.yml et od-domain.yml en commun de manière automatique
#ouverture des deux fichiers yml
#importation de faq-domain.yml
with open("other_data/all_domains/faq-domain.yml", 'rb') as stream:
        faq_domain = yaml.load(stream)
#importation de od-domain.yml
with open("other_data/all_domains/od-domain.yml", 'rb') as stream:
        od_domain = yaml.load(stream)
#importation de faq-aug-domain.yml
with open("other_data/all_domains/faq-aug-domain.yml", 'rb') as stream:
        faq_aug_domain = yaml.load(stream) 
#importation de additional-entities.yml
with open("other_data/all_domains/additional-entities.yml", 'rb') as stream:
        additional_enties = yaml.load(stream) 
#importation de slots.yml
with open("other_data/all_domains/slots.yml", 'rb') as stream:
        slots = yaml.load(stream) 
#importation de actions.yml
with open("other_data/all_domains/actions.yml", 'rb') as stream:
        actions = yaml.load(stream) 
#importation de forms.yml
with open("other_data/all_domains/forms.yml", 'rb') as stream:
        forms = yaml.load(stream) 
#generating the new domain.yml file
domain_yaml = {'version': '2.0'}
domain_yaml['intents'] = faq_domain['intents'] + od_domain['intents']
domain_yaml['entities'] = faq_domain['entities'] + additional_enties['entities']
domain_yaml['slots'] = slots['slots']
domain_yaml['responses'] = {**{**od_domain['responses'] , **faq_domain['responses']},**faq_aug_domain['responses']}
domain_yaml['actions'] = actions['actions']
domain_yaml['forms'] = forms['forms']
domain_yaml['session_config'] = {'session_expiration_time': 60, 'carry_over_slots_to_new_session': True}
with open("domain.yml", 'w', encoding="utf-8") as stream:
    ruamel.yaml.round_trip_dump(domain_yaml, stream, indent=4, block_seq_indent=2)


