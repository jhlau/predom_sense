"""
Generates the word distribution (from wordnet glosses, examples) for each sense of a target word.
Note: Change environment variable WNHOME to use a different version of WordNet dictionary

Usage:          GenWordnetSenses.py < lemmas.txt
Stdin:          lemmas.txt
Stdout:         N/A
Other Input:    stopwords.txt
Other Output:   lemma-senses.pickle
Author:         Jey Han Lau
Date:           Apr 13
"""

import sys
import os
import subprocess
import pickle
from collections import defaultdict

#parameters
noun_only = False
debug = False 

#global variables
stopwords = set([item.strip() for item in open("predom_data/stopwords.txt")])
# { target_lemma: { word#pos#num: { word: freq } } }
sense_word_dist = {}
lemma_pos_list = []

#static
pos_map = { "n": "noun", "v": "verb"}

###########
#functions#
###########

def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


######
#main#
######
for line in sys.stdin:
    data = line.strip().split(".")
    lemma_pos_list.append((data[0], data[1]))

for (lemma, pos) in lemma_pos_list:
    if debug:
        print "\nProcessing: Lemma =", lemma, "; pos =", pos

    #get the senses from wordnet
    command = "wn " + lemma + " -over > tmp_sense.1"
    p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True, executable='/bin/bash')
    p.stdout.readlines()

    #lemmatise the documents
    model_dir = "lemmatiser_tools/opennlp-tools-1.5.0/models/"
    morpha_dir = "lemmatiser_tools/morpha/"
    command = "opennlp TokenizerME " + model_dir + "/en-token.bin < tmp_sense.1 2>/dev/null" + \
                "| opennlp POSTagger " + model_dir + "/en-pos-maxent.bin 2>/dev/null " + \
                "| " + morpha_dir + "morpha -tf " + morpha_dir + "verbstem.list " + \
                "| " + morpha_dir + "morph-post-correct.prl " + \
                " > tmp_sense.2"
                #"| python " + morpha_dir + "CleanMorpha.py " + \
    p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True, executable='/bin/bash')
    p.stdout.readlines()

    #process tmp_sense.2
    start_pattern = "the " + pos_map[pos] + " " + lemma + " have"
    total_num_senses = 0
    start_parsing = False

    sense_word_dist[lemma + "." + pos] = {}

    for line in open("tmp_sense.2"):
        data = [ item.split("_")[0] for item in line.strip().split() ]
        if " ".join(data[:4]) == start_pattern:
            start_parsing = True
            total_num_senses = int(line.strip().split()[4].split("_")[0])
            if debug:
                print "\t", total_num_senses, "senses found."

        elif start_parsing:
            if line.strip() != "":
                sense_id = 0
                word_dist = defaultdict(int)
                for i, word_pos in enumerate(line.strip().split()):
                    break_id = word_pos.rfind("_")
                    word = word_pos[:break_id].lower()
                    wpos = word_pos[(break_id+1):]
                    if i == 0:
                        sense_id = int(word.strip("."))
                        if sense_id == total_num_senses:
                            start_parsing = False
                    else:
                        word = word.strip("\"").strip("'").strip(")").strip("(")
                        if (word == lemma) or \
                            (len(word) < 3) or \
                            (word in stopwords) or \
                            (i < 4 and is_int(word)) or \
                            ((noun_only) and (not wpos.startswith("NN"))):
                            continue
                        else:
                            word_dist[word] += 1

                sense_name = lemma + "#" + pos + "#" + str(sense_id)
                sense_word_dist[lemma + "." + pos][sense_name] = dict(word_dist)

                if debug:
                    print "\n\tSense ID =", sense_id
                    print "\tLine ", line.strip()
                    print "\tWord Dist =", \
                        sorted(sense_word_dist[lemma + "." + pos][sense_name].items())

    #remove the temporary files
    os.remove("tmp_sense.1")
    os.remove("tmp_sense.2")

if debug:
    print "\nLemma and its sense-word dist:"
    for lemma, lemma_senses in sorted(sense_word_dist.items()):
        print "\nLemma =", lemma
        for sense_name, word_dist in sorted(lemma_senses.items()):
            print "\t", sense_name, "=", sorted(word_dist.items())

pickle.dump(sense_word_dist, open("predom_data/dic_senses.pickle", "w"))
