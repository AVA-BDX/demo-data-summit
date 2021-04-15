#!/usr/bin/env python
#-*- coding: UTF-8 -*-

import ruamel.yaml
import yaml
#combiner les deux fichiers faq-domain.yml et od-domain.yml en commun de manière automatique
#ouverture des deux fichiers yml
#importation de faq-domain.yml
with open("data/all_domains/faq-domain.yml", 'rb') as stream:
        faq_domain = yaml.load(stream)
#importation de od-domain.yml
with open("data/all_domains/od-domain.yml", 'rb') as stream:
        od_domain = yaml.load(stream) 
#generating the new domain.yml file
domain_yaml = {'version': '2.0'}
domain_yaml['intents'] = faq_domain['intents'] + od_domain['intents']
domain_yaml['entities'] = faq_domain['entities'] 
domain_yaml['responses'] = {**od_domain['responses'] , **faq_domain['responses']}
domain_yaml['session_config'] = {'session_expiration_time': 60, 'carry_over_slots_to_new_session': False}
with open("domain.yml", 'w') as stream:
    ruamel.yaml.round_trip_dump(domain_yaml, stream, indent=4, block_seq_indent=2)


