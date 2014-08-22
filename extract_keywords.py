#!/usr/bin/python

# Written by Andrea Kahn
# Last updated Aug. 21, 2014

'''
This script takes as input:
1) a path to the notes file, where each line corresponds with a patient and takes the format MRN[tab]text blob, and
2) a path to the gold data file, where each line corresponds with a patient and takes the format MRN[tab]gold_date_1[tab]gold_date_2 ...

It then prints the standard out lines in the following format:
keyword[tab]position[tab]score

...in descending order by score, where:
1) 'position' is 'PRE-DATE' or 'POST-DATE' (corresponding to the position of the keyword with respect to the date), and
2) 'score' is the sum of the inverse distances between that keyword and the closest date in that position in the same document, less the sum of the inverse distances between that keyword and the closest date in that position in the same document.


Alternatively, the module can be imported and the get_keyword_queue() method can be used directly. This method takes as input:
1) a dictionary of MRNs mapped to lists of text blobs (corresponding to clinic notes for that patient), and
2) a dictionary of MRNs mapped to lists of Date objects (corresponding to the gold dates for the event in question for that patient).

It then returns a priority queue of (keyword, position) tuples and their corresponding scores.
'''

import logging
from sys import argv
from sys import exit
from collections import defaultdict
import Queue
from date import *

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


def main():
    logging.basicConfig()

    notes_filename = argv[1]
    data_filename = argv[2]
    
    notes_file = open(notes_filename)
    data_file = open(data_filename)
    
    notes_dict = {}
    for line in notes_file:
        line = line.strip()
        tokens = line.split('\t')
        if len(tokens) != 2:
            LOG.warning("Unexpected line format (should be MRN[tab]note); skipping line: %s" % line)
        else:
            MRN = tokens[0]
            note = tokens[1]
            if notes_dict.get(MRN) == None:
                notes_dict[MRN] = []
            notes_dict[MRN].append(note)

    data_dict = {}
    for line in data_file:
        line = line.strip()
        tokens = line.split('\t')
        if len(tokens) < 2:
            LOG.warning("Unexpected line format (should be MRN[tab]date ... ); skipping line: %s" % line)
        else:
            MRN = tokens[0]
            for i in xrange(1, len(tokens)):
#               LOG.debug("Trying to make date from: %s" % tokens[i])
                date_vals = make_date(tokens[i])
                if not date_vals:
                    LOG.warning("Could not interpret date expression; skipping line: %s" % line)
                else:
                    if data_dict.get(MRN) == None:
                        data_dict[MRN] = []
                    data_dict[MRN].extend(date_vals)

    data_file.close()
    notes_file.close()        
    
    LOG.info("Getting keyword queue")
    keywords = get_keyword_queue(notes_dict, data_dict)

    while not keywords.empty():
        top = keywords.get()        
        score, keyword_position = top
        keyword, position = keyword_position
        score = -1 * score
        print keyword+'\t'+position+'\t'+str(score)


    
def get_keyword_queue(blobs_dict, gold_dates_dict):
    '''
    This method takes as input:
    (1) a dictionary of MRNs mapped to lists of text blobs (corresponding to clinic notes for that patient), and
    (2) a dictionary of MRNs mapped to lists of Date objects (corresponding to the gold dates for the event in question for that patient).
    It then returns a priority queue of (keyword, position) tuples and their corresponding scores. (Scores returned are multiplied by -1 so that highest-scored keywords are returned first, since python's priority queue returns lowest-scored items first.)
    '''
    # In the following dictionaries:
    # keys are (keyword, position) 2-tuples, where 'position' is the string 'PRE' or the string 'POST', depending on whether the n-gram appeared before or after the date
    # values are lists of the inverse of the distance to the closest correct or incorrect date given the position
    true_date_ngrams = defaultdict(lambda: [])
    false_date_ngrams = defaultdict(lambda: [])

    for MRN in gold_dates_dict:
        gold_dates_list = gold_dates_dict[MRN]
 
        for blob in blobs_dict[MRN]:
#           LOG.debug("\n")
#           LOG.debug("Original text: %s" % blob)
            tagged_text = tag_dates(blob, gold_dates_list)
#           LOG.debug("Tagged text: %s" % tagged_text)
            tokenized_text = custom_tokenize(tagged_text)
            tokens = tokenized_text.split()
#           LOG.debug("Tokenized text: %s" % tokens)
            true_date_indices, false_date_indices = get_date_indices(tokens)
             
#           if (not true_date_indices) and (not false_date_indices):
#               LOG.debug("No dates in this note; moving on to next note")
             
#           else:
            if true_date_indices and false_date_indices:
                
                for i in xrange(len(tokens)):
#                   LOG.debug("Considering token %s" % tokens[i])
                    
                    # Skip date tokens
                    if i not in (true_date_indices + false_date_indices):
                    
                        # Ignore case
                        token = tokens[i].lower()
                
                        inv_dist_to_next_true_date = get_ngram_distances(i, true_date_indices, 'PRE-DATE')
#                       LOG.debug("Inverse distance to next true date is %s" % inv_dist_to_next_true_date)
                        inv_dist_to_next_false_date = get_ngram_distances(i, false_date_indices, 'PRE-DATE')
#                       LOG.debug("Inverse distance to next false date is %s" % inv_dist_to_next_false_date)
                        
                        if inv_dist_to_next_true_date > inv_dist_to_next_false_date:
                            true_date_ngrams[(token, 'PRE-DATE')].append(inv_dist_to_next_true_date)
                        elif inv_dist_to_next_false_date > inv_dist_to_next_true_date:
                            false_date_ngrams[(token, 'PRE-DATE')].append(inv_dist_to_next_false_date)
                        else:
                            if inv_dist_to_next_false_date != 0:
                                LOG.warning("Inverse distance to true and false dates are the same; skipping")
                    
                        inv_dist_to_prev_true_date = get_ngram_distances(i, true_date_indices, 'POST-DATE')
#                       LOG.debug("Inverse distance to previous true date is %s" % inv_dist_to_prev_true_date)
                        inv_dist_to_prev_false_date = get_ngram_distances(i, false_date_indices, 'POST-DATE')
#                       LOG.debug("Inverse distance to previous false date is %s" % inv_dist_to_prev_false_date)

                        if inv_dist_to_prev_true_date > inv_dist_to_prev_false_date:
                            true_date_ngrams[(token, 'POST-DATE')].append(inv_dist_to_prev_true_date)
                        elif inv_dist_to_prev_false_date > inv_dist_to_prev_true_date:
                            false_date_ngrams[(token, 'POST-DATE')].append(inv_dist_to_prev_false_date)
                        else:
                            if inv_dist_to_prev_false_date != 0:
                                LOG.warning("Inverse distance to true and false dates are the same; skipping")

    # Score the ngrams by taking the difference between the sum of their distances from false dates and the sum of their distances from true dates
    # Store the ngrams by these scores in a priority queue
    # Extremely negative score (i.e., popped first from queue) = high correlation
    ngrams = Queue.PriorityQueue()
    for ngram in true_date_ngrams:
        LOG.debug("Summing distances for ngram %s" % str(ngram))
        
        LOG.debug("True date distances: %s" % true_date_ngrams[ngram])
#       normalize_for_word_freq(true_date_ngrams[ngram])
#       LOG.debug("True date distances after normalizing for keyword frequency: %s" % true_date_ngrams[ngram])
#       normalize_for_date_freq(true_date_ngrams[ngram])
#       LOG.debug("True date distances after normalizing for true/false date frequency: %s" % true_date_ngrams[ngram])

        LOG.debug("False date distances: %s" % false_date_ngrams[ngram])
#       normalize_for_word_freq(false_date_ngrams[ngram])
        normalize_for_word_freq_2(true_date_ngrams[ngram], false_date_ngrams[ngram])
#       LOG.debug("False date distances after normalizing for keyword frequency: %s" % false_date_ngrams[ngram])
#       normalize_for_date_freq(false_date_ngrams[ngram])
#       LOG.debug("False date distances after normalizing for true/false date frequency: %s" % false_date_ngrams[ngram])

        score = sum(false_date_ngrams[ngram]) - sum(true_date_ngrams[ngram])
        LOG.debug("Score: %s" % score)
        ngrams.put((score, ngram))
    
    return ngrams


def tag_dates(text, gold_dates):
    '''
    This method takes as input:
    (1) a text blob, and
    (2) a list of Date objects corresponding to the gold dates for the specified event for the current patient.
    It then returns the text blob with the date expressions corresponding to gold dates replaced with the string TRUE_DATE and those corresponding with other dates with the string FALSE_DATE.
    '''
    # Get a list of (Date object, char index of start of date expression, char index of end of date expression) 3-tuples
    date_expressions = extract_dates_and_char_indices(text)

    to_return = ''
    text_start = 0
    i = 0
    
    while i < len(date_expressions):
        date_val, date_start, date_end = date_expressions[i]
        to_return += text[text_start:date_start]
#       LOG.debug("Looking for %s in gold dates list" % date_val)

        is_true_date = False
        for gold_date in gold_dates:
            if gold_date.is_fuzzy_match(date_val):
                is_true_date = True

        if is_true_date:
            to_return += 'TRUE_DATE'
        else:
            to_return += 'FALSE_DATE'
        text_start = date_end
        i += 1
    
    to_return += text[text_start:]

    return to_return


def custom_tokenize(text):
    '''
    This method takes a string as input and returns a version of the string in which punctuation has been replaced with whitespace, except in the case of punctuation-containing patterns that could be dates, medication dosages, etc. and should thus be treated as individual tokens.
    FIXME: don't split contractions, possessives
    '''
    delimiters = re.compile(r'(?![\s/-])\W')
    to_return = delimiters.sub(' ', text)
    to_return = re.sub(r'([^0-9])[/-]', r'\1 ', to_return)
    return to_return


def get_date_indices(token_list):
    '''
    This method takes as input a list of tokens, after punctuation has been removed, date expressions corresponding to gold dates have been replaced with the string TRUE_DATE, and date expressions corresponding with other dates with the string FALSE_DATE. It then returns two lists:
    (1) A list of token indices of gold dates (TRUE_DATE tokens), and
    (2) A list of token indices of other dates (FALSE_DATE tokens).
    '''
    true_date_indices = []
    false_date_indices = []
    
    for i in xrange(len(token_list)):
#       LOG.debug("Considering token %s" % token_list[i])
        if token_list[i]=='TRUE_DATE':
            true_date_indices.append(i)
        elif token_list[i]=='FALSE_DATE':
            false_date_indices.append(i)
    
    return (true_date_indices, false_date_indices)


def get_ngram_distances(token_index, date_indices, token_position):
    '''
    This method takes as input:
    1) the index of the token,
    2) a list of indices of TRUE_DATE or FALSE_DATE tokens in the document, and
    3) a string, either 'PRE-DATE' or 'POST-DATE', corresponding to the position of the token with respect to the dates we'd like to consider.
    It then returns the maximum inverse distance (i.e., inverse of the minimum positive distance) to a date whose index appears in the list, taking into account the desired token position (0 if no date in the desired position).
    '''
    # If there are {true, false} dates in the document, calculate the distance to the closest, taking into account specified token position
    if date_indices:

        # NB: Taking the maximum of the inverse distance ensures that you get the smallest positive distance
        if token_position == 'PRE-DATE':
            inv_dist_to_next_date = max([(date_index - token_index)**(-1) for date_index in date_indices])
        elif token_position == 'POST-DATE':
            inv_dist_to_next_date = max([(token_index - date_index)**(-1) for date_index in date_indices])
        else:
            LOG.warning("Token position must be 'PRE-DATE' or 'POST-DATE'; setting distance to 0")

        # If inverse distance is negative, no {true, false} date in the specified position
        # We want to treat this as we would the case where no {true, false} date appeared in the document at all, i.e. distance = infinity, inverse distance = 0
        if inv_dist_to_next_date < 0:
            inv_dist_to_next_date = 0

    # If no {true, false} dates in the document, distance to next {true, false} date is infinity; inverse distance is 0
    else:
        inv_dist_to_next_date = 0

    return inv_dist_to_next_date


def normalize_for_word_freq(dist_list):
    '''
    This method takes a list of inverse distances to either TRUE_DATE or FALSE_DATE tokens and normalizes them to account for the relative frequency of the keyword.
    '''
    # Normalization constant is the number of times the keyword shows up in the desired position with respect to a {true, false} date
    norm_constant = len(filter(lambda x: x > 0, dist_list))
    LOG.debug("The word-frequency normalization constant is %s" % norm_constant)
    if norm_constant > 0:
        for i in xrange(len(dist_list)):
            dist_list[i] *= 1.0/norm_constant


def normalize_for_word_freq_2(dist_list_1, dist_list_2):
    '''
    This method takes two lists of inverse distances to either TRUE_DATE and FALSE_DATE tokens, respectively, and normalizes them to account for the relative frequency of the keyword. This is the appropriate method to use where only the inverse distance to the closest TRUE OR FALSE date is added to the appropriate list, not the inverse distance to the closest TRUE date AND the closest FALSE date.
    '''
    # Normalization constant is the number of times the keyword shows up in the desired position with respect to a {true, false} date
    norm_constant = len(dist_list_1) + len(dist_list_2)
    LOG.debug("The word-frequency normalization constant is %s" % norm_constant)
    if norm_constant > 0:
        for i in xrange(len(dist_list_1)):
            dist_list_1[i] *= 1.0/norm_constant
        for i in xrange(len(dist_list_2)):
            dist_list_2[i] *= 1.0/norm_constant


def normalize_for_date_freq(dist_list):
    '''
    This method takes a list of inverse distances to either TRUE_DATE or FALSE_DATE tokens and normalizes them to account for the relative frequency of TRUE_DATE vs. FALSE_DATE tokens.
    '''
    # Normalization constant is the number of times the keyword shows up at all
    norm_constant = len(dist_list)
    LOG.debug("The date-frequency normalization constant is %s" % norm_constant)
    if norm_constant > 0:
        for i in xrange(len(dist_list)):
            dist_list[i] *= 1.0/norm_constant


if __name__=='__main__':
    main()