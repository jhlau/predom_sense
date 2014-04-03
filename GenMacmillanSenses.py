"""
Spdin:          N/A
Stdout:         N/A
Other Input:    N/A
Other Output:   lemma_senses.pickle, gold_instances.pickle
Author:         Jey Han Lau
Date:           Jul 13
"""

import argparse
import sys
import pickle
import re
import subprocess
from lxml import etree
from collections import defaultdict

#parser arguments
desc = "Extracts the gloss and example from macmillan's dictionary for a given list of lemmas."
parser = argparse.ArgumentParser(description=desc)

#####################
#positional argument#
#####################
parser.add_argument("lemma_list", help="list of lemmas of interest")
parser.add_argument("lemma_data_dir", help="directory that contains the definitions of the lemmas" +\
    " in xml.");

###################
#optional argument#
###################

args = parser.parse_args()

#parameters
noun_only = False
thesaurus = False
debug = False

#global variables
lemmas = [ item.strip() for item in open(args.lemma_list) ]
stopwords = set([item.strip() for item in open("predom_data/stopwords.txt")])
# { target_lemma: { word#pos#num: { word: freq } } }
sense_word_dist = {}

###########
#functions#
###########

def get_clean_text(elem):
    clean_str = re.sub("<.*?>", " ", etree.tostring(elem)).encode('ascii','ignore').replace('\n', \
        ' ').strip()
    clean_str = clean_str.replace("-", " ")
    clean_str = clean_str.replace("/", " ")
    return clean_str

######
#main#
######

#process each lemma
for l in lemmas:
    context = etree.iterparse(open(args.lemma_data_dir + "/" + l + ".xml"))
    sense_sents = defaultdict(list) #sense_id: [sentences]
    sense_id = ""
    sense_word_dist[l + ".n"] = {}
    
    if debug:
        print "================================================================="
        print "Lemma =", l

    for action, elem in context:
        if (elem.tag == "SENSE" and elem.getparent().tag != "PHRASE") or \
            (elem.tag == "SUB-SENSE" and elem.getparent().getparent().getparent() != "PHRASE"):
            if elem.tag == "SENSE":
                sense_id = elem.attrib["ID"]
                sense_content = elem.find("SENSE-CONTENT")
            else:
                sense_id = elem.getparent().getparent().attrib["ID"]
                sense_content = elem.find("SUB-SENSE-CONTENT")
            if debug:
                print "\nSense ID =", sense_id

            #get the (sub) definitions
            for d in sense_content.findall("DEFINITION"):
                sense_sents[sense_id].append(get_clean_text(d))
                if debug:
                    print "Definition =", get_clean_text(d)

            for e in sense_content.findall("EXAMPLES"):
                if debug:
                    print "\tExample =",
                #look for collocation patterns
                colloc = e.find("PATTERNS-COLLOCATIONS")
                if colloc != None:
                    sense_sents[sense_id].append(get_clean_text(colloc))
                    if debug:
                        print get_clean_text(colloc),

                #look for examples
                example = e.find("EXAMPLE")
                if example != "":
                    sense_sents[sense_id].append(get_clean_text(example))
                if debug:
                    print get_clean_text(example)

            #get the thesaurus entries
            if (thesaurus):# and (elem.tag != "SUB-SENSE"):
                if debug:
                    print "\tThesaurus entries =",
                for txref in sense_content.findall("TXREF"):
                    for entry in txref.findall("Ref"):
                        sense_sents[sense_id].append(get_clean_text(entry).strip(",").strip())
                        if debug:
                            print "'" + get_clean_text(entry).strip(",").strip() + "'",
                if debug:
                    print

    #lemmatise the sentences
    if debug:
        print "\nLemmatising the glosses..."
    for sense_num, sense_id in enumerate(sense_sents.keys()):
        word_dist = defaultdict(int)
        if debug:
            print "\nSENSE ID =", sense_id
        model_dir = "lemmatiser_tools/opennlp-tools-1.5.0/models/"
        morpha_dir = "lemmatiser_tools/morpha/"
        command = "echo \"" + "\n".join(sense_sents[sense_id]).replace("\"", "\\\"") + "\" " + \
                    "| opennlp TokenizerME " + model_dir + "/en-token.bin 2>/dev/null " + \
                    "| opennlp POSTagger " + model_dir + "/en-pos-maxent.bin 2>/dev/null " + \
                    "| " + morpha_dir + "morpha -tf " + morpha_dir + "verbstem.list " + \
                    "| " + morpha_dir + "morph-post-correct.prl "
                    #"| python " + morpha_dir + "CleanMorpha.py " + \
        p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True, executable='/bin/bash')
        results = p.stdout.readlines()
        if len(results) == 0:
            print "Error lemmatising", sense_id, "for", l
            raise SystemExit
        for line in results:
            if debug:
                print line.strip()
            for word_pos in line.strip().split():
                break_id = word_pos.rfind("_")
                word = word_pos[:break_id].lower()
                wpos = word_pos[(break_id+1):]
                word = word.strip("\"").strip("'").strip(")").strip("(")
                if (word == l) or \
                    (len(word) < 3) or \
                    (word in stopwords) or \
                    (wpos == "CD") or \
                    ((noun_only) and (not wpos.startswith("NN"))):
                    continue
                else:
                    word_dist[word] += 1

        #update the word weights for the sense
        sense_word_dist[l + ".n"][l + "#n#" + str(sense_num+1)] = dict(word_dist)
        if debug:
            print "Word distribution =", sense_word_dist[l + ".n"][l + "#n#" + str(sense_num+1)]

#dump the word distribution of senses
pickle.dump(sense_word_dist, open("predom_data/dic_senses.pickle", "w"))
