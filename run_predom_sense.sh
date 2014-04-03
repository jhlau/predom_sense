#!/bin/bash

#NOTE: please run HDP to induce the senses before running this script. For more information please
#read the README file.

#parameters
#dictionary (currently supports "wordnet" and "macmillan" only)
dic="wordnet"
#directory that contains macmillan word definitions in xml format
#note: this option is only applicable if macmallin dictionary is used
macmillan_def_dir="predom_data/macmillan"
#hdp output directory that contains tm_wsi, topic_wordprob
hdp_output="hdp_output"
#text file that contains target lemmas to learn predominant sense
lemma_input="predom_data/example_wordnet_lemmas.txt"

#generate the dictionary senses (either by invoking wordnet or parsing macmillan xml files)
echo "Generating word distribution of dictionary senses..."
if [ $dic == "wordnet" ]
then
    python GenWordnetSenses.py < $lemma_input
elif [ $dic == "macmillan" ]
then
    python GenMacmillanSenses.py $lemma_input $macmillan_def_dir
else
    echo "Dictionary $dic not supported."
    exit 0
fi

#compute the sense distribution and predominant sense
echo "Computing dictionary sense distribution and predominant sense..."
python ComputeSenseRanking.py $hdp_output predom_data/dic_senses.pickle
