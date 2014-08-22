Author: Andrea Kahn
amkahn@uw.edu
Aug. 20, 2014


Motivation:
To learn keywords that tend to appear in close proximity to date expressions corresponding with a particular clinical event significantly more often than they appear in close proximity to other date expressions. These keywords can then be fed into an event extraction system that identifies the date of a clinical event for a particular patient using the patient's clinic notes, by identifying which dates appear most frequently within a set window around the input keywords.


Files:
extract_keywords.py: The module for keyword extraction. It can be run as an executable from the command line, or it can be imported and its get_keyword_queue() method can be used directly.
date.py: A module for the processing of date expressions in text (imported and used by extract_keywords.py).


Input:
1) A path to the notes file, where each line corresponds with a note and takes the format MRN[tab]text blob.
2) A path to the gold data file, where each line corresponds with a patient and takes the format MRN[tab]gold_date_1[tab]gold_date_2
...where gold_date_n takes the format YYYY, YYYY-MM, or YYYY-MM-DD.

Command line usage: ./extract_keywords.py <note-file> <gold-data-file>


Output:
The program prints to standard out lines in the following format:
keyword[tab]position[tab]score

...in descending order by score, where:
1) 'position' is 'PRE-DATE' or 'POST-DATE' (corresponding to the position of the keyword with respect to the date), and
2) 'score' is the sum of the inverse distances between that keyword and the closest date in that position in the same document, less the sum of the inverse distances between that keyword and the closest date in that position in the same document.


Module usage:
Alternatively, the module can be imported and the get_keyword_queue() method can be used directly. This method takes as input:
1) a dictionary of MRNs mapped to lists of text blobs (corresponding to clinic notes for that patient), and
2) a dictionary of MRNs mapped to lists of Date objects (corresponding to the gold dates for the event in question for that patient).

It then returns a priority queue of (keyword, position) tuples and their corresponding scores.


Specifications:
This program was developed in python 2.7.5.
It uses the following python modules: sys, logging, collections, Queue, re, datetime.


Logging:
Set to WARNING level. To change, edit the following lines:
extract_keywords.py: line 34
date.py: line 15