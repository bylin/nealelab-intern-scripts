#!/usr/bin/python
# Author: Brian Lin
import subprocess
import argparse
import timestamp
import re
import os
import classes
from FileIO import Fasta

def parseArgs():
	parser = argparse.ArgumentParser(description="Uses probabilistic models to find likely LTR retrotransposon candidates")
	parser.add_argument('fasta', metavar='[fasta]', help="Input .fasta file, containing transposable elements")
	parser.add_argument('-noclean', '--keep_temporary_files', action="store_true", help="Don't clean up hmm and blast output files")
	parser.add_argument('-name', '--job_name', default="GCclassif-{}".format(timestamp), help="Name prepended to this run's output. Default=\"GCclassif-TIMESTAMP\"")
	return parser.parse_args()

def main():
	log('Start hmmern.py\n', 'log')
	runHmmer()
	log('Get raw sequence information\n', 'log')
	rawSeqs = loadRawSeqs()
	for seq in Fasta(orfFile):
		rawSeqs[seq.id.split('|')[0]] = ExtendedSeqRecord(seq)
	log('Parsing HMMER hits\n', 'log')
	parseHmmHits(rawSeqs)
	log('Ranking hits and classifying\n', 'log')
	examineDomainsAndClassify(rawSeqs)
	if not args.keep_temporary_files:
		log('Cleaning temp files\n', 'log')
		clean()

def runHmmer():
	hmmernCmd = 'hmmern.py -hmm {} -i {} -o {}'.format(hmmProfilesForLTRs, args.fasta, hmmHitFile)
	subprocess.call(hmmernCmd, shell=True)

def loadRawSeqs():
	rawSeqDict = {}
	for seq in Fasta(orfFile):
		identifier = seq.id.split('|')[0]
		rawSeqDict[identifier] = ExtendedSeqRecord(seq)
	return rawSeqDict

class ExtendedSeqRecord(object):
	def __init__(self, seq):
		self.seq = seq
		self.hits = []

	def addHit(self, hmmhit):
		self.hits.append(hmmhit)

def parseHmmHits(rawSeqs):
	for line in open(hmmHitFile):
		tabs = re.findall('\S+', line)
		if tabs[0][0] == '#': continue
		rawSeq = tabs[0]
		#rawSeq = tabs[0].split('|')[0]
		hmmName = tabs[3]
		try: 
			orfstart = int(re.findall(':(\d+)-', tabs[-1])[0])
			#orfstart = int(re.findall(':(\d+)-', tabs[0])[0])
		except:
			log("Could not parse line: {}\n".format(line))
			continue
		start = int(tabs[19]) * 3 - 2 + orfstart
		end = int(tabs[20]) * 3 - 5 + orfstart
		score = float(tabs[13])
		hmmhit = classes.HmmHit(hmmName, start, end, score)
		try: rawSeqs[rawSeq].addHit(hmmhit)
		except KeyError:
			log('{} not in rawSeqs\n'.format(rawSeq))

def examineDomainsAndClassify(rawSeqs):
	log('Sequence\tOld classification\tNew classification\n', 'results')
	nerrors = 0
	nsuccess = 0
	for xseq in rawSeqs:
		if len(rawSeqs[xseq].hits) == 0:
			continue
		log('{}: \n'.format(xseq), 'evidence')
		classif, score = classify(sorted(rawSeqs[xseq].hits))
		try:
			old = rawSeqs[xseq].seq.description.split('\t')[1]
			if classif and old != classif:
				log('{}\t{}\t{}\t{}\n'.format(xseq, old, classif, score), 'results')
				nerrors+=1
				print xseq + '\t' + old + '\t' + classif
			else:
				nsuccess+=1
		except:
			if classif:
				log('{}\t{}\n'.format(xseq, classif), 'results')
			print xseq + '\told\t' + classif
	print 'errors: {}\nsuccess: {}'.format(nerrors, nsuccess)

def classify(hitList):
	classifs = []
	for hit,i in zip(hitList, range(0,len(hitList))):
		if hit.name[0:2] == 'GA':
			classify_GAG(hitList[i:], classifs, hit.score)
		if hit.name[0:2] == 'AP':
			classify_AP(hitList[i:], classifs, hit.score)
		elif hit.name[0:2] == 'RT':
			classify_RT(hitList[i:], classifs, hit.score)
		elif hit.name[0:2] == 'RH':
			classify_RH(hitList[i:], classifs, hit.score)
		elif hit.name[0:2] == 'IN':
			classify_INT(hitList[i:], classifs, hit.score)
	return findBestClassif(classifs)

def findBestClassif(classifs):
	if len(classifs) > 0:
		classifs = sorted(classifs, key=lambda x:x[1], reverse=True)
		#print bestClassif[1]
		log('\t' + ','.join('{}:{}'.format(c[0], c[1]) for c in classifs) + '\n', 'evidence')
		return classifs[0][0], classifs[0][1] # return classif and score
	else:
		return '', -1

# Classify_: represents states in a state diagram. 
# This is coded deterministically, but all paths are iterated through to maximize the cumlative HMM hit score of a series of linked hits.
# That way, we consider all possibilities and combinations of protein domain hits.
def classify_GAG(hitList, classifs, currentScore):
	for hit, i in zip(hitList[1:], range(1, len(hitList))):
		if hit.name[0:2] == 'AP':
			classify_AP(hitList[i:], classifs, hit.score + currentScore)
		elif hit.name[0:2] == 'RT':
			classify_RT(hitList[i:], classifs, hit.score + currentScore)
		elif hit.name[0:2] == 'RH':
			classify_RH(hitList[i:], classifs, hit.score + currentScore)
		elif hit.name[0:2] == 'IN':
			classify_INT(hitList[i:], classifs, hit.score + currentScore)

def classify_AP(hitList, classifs, currentScore):
	for hit, i in zip(hitList[1:], range(1, len(hitList))):
		if hit.start-hitList[0].end > 800:
			continue
		if hit.name[0:2] == 'RT':
			classify_RT(hitList[i:], classifs, hit.score + currentScore)
		elif hit.name[0:2] == 'RH':
			classify_RH(hitList[i:], classifs, hit.score + currentScore)
		elif hit.name[0:2] == 'IN':
			classify_INT(hitList[i:], classifs, hit.score + currentScore)

def classify_RT(hitList, classifs, currentScore):
	for hit, i in zip(hitList[1:], range(1, len(hitList))):
		if hit.start-hitList[0].end > 2000:
			continue
		if hit.name[0:2] == 'RH':
			classify_RH(hitList[i:], classifs, hit.score + currentScore)
		elif hit.name[0:2] == 'IN':
			classify_EN(hitList[i:], classifs, hit.score + currentScore)

def classify_RH(hitList, classifs, currentScore):
	for hit, i in zip(hitList[1:], range(1, len(hitList))):
		if hit.start-hitList[0].end > 2000:
			continue
		elif hit.name[0:2] == 'IN':
			classify_EN(hitList[i:], classifs, hit.score + currentScore)

def classify_EN(hitList, classifs, currentScore):
	for hit in hitList[1:]:
		if hit.start-hitList[0].end > 2000:
			continue
		if hit.name[0:2] == 'EN':
			classifs.append(('Gypsy', hit.score + currentScore))
	classifs.append(('Gypsy', currentScore))

def classify_INT(hitList, classifs, currentScore):
	for hit, i in zip(hitList[1:], range(1, len(hitList))):
		if hit.start-hitList[0].end > 2000:
			continue
		elif hit.name[0:2] == 'RT':
			classify_INT_RT(hitList[i:], classifs, hit.score + currentScore)
		elif hit.name[0:2] == 'RH':
			classifs.append(('Copia', hit.score + currentScore))

def classify_INT_RT(hitList, classifs, currentScore):
	for hit in hitList[1:]:
		if hit.start-hitList[0].end > 2000:
			continue
		elif hit.name[0:2] == 'RH':
			classifs.append(('Copia', hit.score + currentScore))
	classifs.append(('Copia', currentScore))

def clean():
	os.remove(orfFile)
	os.remove(hmmHitFile)
	os.remove(evidenceFile)
	os.remove(logFile)

def log(string, logtype):
	if logtype == 'evidence' and 'evidenceFileHandle' in globals():
		evidenceFileHandle.write(string)
	if logtype == 'log' and 'logFileHandle' in globals():
		logFileHandle.write(string)
	if logtype == 'results' and 'resultsFileHandle' in globals():
		resultsFileHandle.write(string)

if __name__ == '__main__':
	#setup global & static variables
	timestamp = timestamp.timestamp()
	args = parseArgs()
	hmmProfilesForLTRs = '/share/jyllwgrp/nealedata/databases/ltr-Pfam.hmm'
	targetSeqs = '/share/jyllwgrp/nealedata/databases/pier-1.3.fa'
	orfFile = args.fasta + '.orfs'
	logFile = '{}-log.txt'.format(args.job_name)
	hmmHitFile = '{}-hmmer-output.txt'.format(args.job_name)
	evidenceFile = '{}-evidence.txt'.format(args.job_name)
	resultsFile = '{}-results.txt'.format(args.job_name)
	evidenceFileHandle = open(evidenceFile, 'w')
	resultsFileHandle = open(resultsFile, 'w')
	logFileHandle = open(logFile, 'w')
	main()
	
