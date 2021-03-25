#!/usr/bin/env python
#-*- coding: UTF-8 -*-

import pandas as pd
path = r"data/data-base-source/QNA_for_bots.csv"
data_base = pd.read_csv(path,  sep=";", encoding="latin3")
with open("data/faq/faq-nlu.yml", "wt", encoding="latin3") as f:
    f.write('version: "2.0" \n')
    f.write('\n')
    f.write("nlu:\n")
    for num_pivot in range(1,len(data_base)):
        data_base_pivot = data_base.loc[data_base["id_question_pivot"]==num_pivot,]
        f.write("- intent: faq/" + str(num_pivot) + "\n")
        f.write("  examples: |\n")
        for row in range(len(data_base_pivot)):
            text = str(data_base_pivot.iloc[row,1])
            f.write(f"   - {text}\n")
        f.write("\n")

with open("data/faq/faq-domain.yml", "wt", encoding="latin3") as f:
    f.write('version: "2.0" \n')
    f.write('\n')
    f.write("intents:\n") 
    f.write("  - faq\n")
    f.write('\n')
    f.write('responses:\n')
    for num_pivot in range(1,len(data_base)):
        data_base_pivot = data_base.loc[data_base["id_question_pivot"]==num_pivot,]
        f.write("  utter_faq/" + str(num_pivot) +":" "\n")
        for row in range(len(data_base_pivot)):
            text = '"'+ str(data_base_pivot.iloc[row,2]) + '"'
            f.write(f"    - text: {text}\n")
        f.write("\n")