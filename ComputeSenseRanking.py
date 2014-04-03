"""
Stdin:          N/A
Stdout:         system sense ranking
Other Input:    wsi_output_dir/tm_wsi
                wsi_output_dir/topicword_prob/<lemma.pos.topics.pickle>
                lemma_senses.pickle
Other Output:   N/A
Author:         Jey Han Lau
Date:           Jun 13
"""

import argparse
import sys
import pickle
import operator
import math
import numpy
import random
from scipy import stats
from collections import defaultdict

#parser arguments
desc = "Takes in the output of hdp-wsi and word distribution of dictionary senses and produce \
    the system ranking of senses"
parser = argparse.ArgumentParser(description=desc)

#####################
#positional argument#
#####################
parser.add_argument("wsi_output_dir", help="directory that contains the output of hdp-wsi")
parser.add_argument("dic_senses_pickle", help="pickle file that contains the word distribution \
    of dictionary senses")

##################
#optional argument#
###################
args = parser.parse_args()

#parameters
debug = False

#global variables
dic_sense_dist = pickle.load(open(args.dic_senses_pickle))
#{ bank: {1:0.5, 2:0.3, ...} }
lemma_topic_dist = defaultdict(lambda:defaultdict(float))


###########
#functions#
###########
#computation of kullback-liebler divergence
def kl_divergence(u, v):
    if len(u) != len(v):
        sys.stderr.write("KL Divergence Calculation Error: Length of vectors are not the same (" \
            + str(len(u)) + ", " + str(len(v)) + ")\n")
        raise SystemExit

    result = 0
    for i in range(0, len(u)):
        if (u[i] != 0) and (v[i] != 0):
            result += u[i] * math.log((float(u[i])/v[i]), 2)

    return result


#computation of jensen-shannon divergence
def js_divergence(u, v): 
    m = [float(sum(a))/2 for a in zip(*[u,v])]
    return 0.5*(kl_divergence(u, m) + kl_divergence(v, m))

#convert the format of dist1 and dist2 so that they have the same length
def convert_dist(dist1, dist2, dist2_keys):
    sum_dist1 = sum(dist1.values())
    sum_dist2 = sum( dist2[item] for item in dist2_keys )
    all_keys = set(dist1.keys() + list(dist2_keys))

    mdist1 = []
    mdist2 = []
    for key in all_keys:
        v1 = 0.0
        v2 = 0.0
        if key in dist1:
            v1 = (float(dist1[key])/sum_dist1)
        if key in dist2:
            v2 = (float(dist2[key])/sum_dist2)
        mdist1.append(v1)
        mdist2.append(v2)

    return (mdist1, mdist2)

######
#main#
######
#process tm_wsi file
for line in open(args.wsi_output_dir + "/tm_wsi"):
    data = line.strip().split()
    lemma = data[0].split(".")[0]
    topic = int(data[2].split("/")[0].split(".")[1])
    topic_prob = float(data[2].split("/")[1])
    inst_id = int(data[1].split(".")[2])
    lemma_topic_dist[data[0]][topic] += 1
    
if debug:
    print "======================================================="
    print "Topic Distribution for Lemmas"

#convert the document frequency of topics into proportions
for lemma, topic_dist in sorted(lemma_topic_dist.items()):
    total = sum(topic_dist.values())
    if debug:
        print "\nLemma =", lemma, "; num_inst =", total
    for topic, freq in sorted(topic_dist.items()):
        lemma_topic_dist[lemma][topic] = float(freq) / total
        if debug:
            print "\tTopic", topic, "=", lemma_topic_dist[lemma][topic], "(", freq, ")"

#calculate the system sense ranking for each lemma
for lemma, topic_dist in sorted(lemma_topic_dist.items()):
    l = lemma.split(".")[0]
    sense_rank = defaultdict(float) #{lemma#pos#1: proportion}

    #get the word distribution in topics
    tw_dist = pickle.load(open(args.wsi_output_dir + "/topic_wordprob/" + lemma + ".topics.pickle"))

    if debug:
        print "======================================================="
        print "Computing sense ranking for", lemma

    for sense, word_dist in sorted(dic_sense_dist[lemma].items()):
        weight = 0.0
        sum_word_freq = sum(word_dist.values())
    
        if debug:
            print "--------------------------------"
            print "\nSense =", sense
            print "\tWord Dist =", word_dist
            print "\tSum word freq =", sum_word_freq

        for topic, word_dist2 in tw_dist.items():
            topic_prop = lemma_topic_dist[lemma][topic]
            topic_weight = 0.0
            overlap_weights = [] #tw probability of overlap words
            word_dist2_topN = [ (item[0], item[1]) for item in sorted(word_dist2.items(), \
                key=operator.itemgetter(1), reverse=True) ]
            word_dist2_topN = [ item[0] for item in word_dist2_topN ]

            if debug:
                print "\n\tTopic =", topic, "( proportion =", topic_prop, ")"
                print "\tTop-N Topic Words =", word_dist2_topN[:20]

            #convert to set for faster lookup
            word_dist2_topN = set(word_dist2_topN)

            #calculate js div between word_dist and word_dist2
            (wd1, wd2) = convert_dist(word_dist, word_dist2, word_dist2_topN)
            overlap_weights.append(1.0 - js_divergence(wd1, wd2))
            if (float(sum(overlap_weights)) < -0.01) or (float(sum(overlap_weights)) > 2.01):
                sys.stderr.write("Error: js_divergence value exceeded boundaries - " + \
                    str(sum(overlap_weights)))

            topic_weight = sum(overlap_weights)*topic_prop
            weight += topic_weight

            if debug:
                print "\tSense-Topic Association (inv-JS div) =", sum(overlap_weights)
                print "\tST-assoc * topic proportion for topic =", topic_weight

        sense_rank[sense] = weight

        if debug:
            print "\nFinal weight of the senses (sum ST-assoc * topic prop) =", weight

    #output the system sense rank
    print "Starting Ranks for word", lemma.split(".")[0]
    sum_weights = sum(sense_rank.values())
    if sum_weights == 0.0:
        for sense, rank in sorted(sense_rank.items()):
            print sense, "=", rank
    else:
        for sense, rank in sorted(sense_rank.items(), key=operator.itemgetter(1), reverse=True):
            print sense, "=", rank/sum_weights
