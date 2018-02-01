#!/usr/bin/env python

import sys
import time
import json
import math
import numpy
import random
import requests
import datetime
import subprocess

badHours = [5, 6, 17, 18]
miningCutoffPrice = 3.0

#======================================
#======================================
class SmartMiner(object):
	def __init__(self):
		self.minercmd = "~/devel/monero.sh"
		self.proc = None
		return

	#======================================
	def getUrl(self, url):
		fails = 0
		while(fails < 3):
			try:
				resp = requests.get(url, timeout=1)
				break
			except requests.exceptions.ReadTimeout:
				print "FAILED request"
				fails+=1
				time.sleep(random.random()+ fails**2)
				continue
			except requests.exceptions.ConnectTimeout:
				print "FAILED connect"
				fails+=2
				time.sleep(random.random()+ fails**2)
				continue

		if fails >= 3:
			print "ERROR: too many failed requests"
			sys.exit(1)
		data = json.loads(resp.text)
		time.sleep(random.random())
		return data

	#======================================
	def getCurrentComedRate(self):
		comedurl = "https://hourlypricing.comed.com/api?type=5minutefeed"
		data = self.getUrl(comedurl)
		firsttime = int(data[0]['millisUTC'])
		comedtime = datetime.datetime.fromtimestamp(firsttime/1000.)

		#--------------------------------------
		now = datetime.datetime.now()
		if now.hour != comedtime.hour:
			print "warning new hour has started, price unknown"
			if (now.hour - comedtime.hour) > 1 or now.minute > 8:
				print "data is too old, waiting for current data"
				self.disable()
				return None
		print "Current Price %.2f"%(float(data[0]['price']))

		#--------------------------------------
		x = []
		currentPrices = []
		for p in data:
			ms = int(p['millisUTC'])
			price = float(p['price'])

			comedtime = datetime.datetime.fromtimestamp(ms/1000.)
			day = comedtime.day

			#print timestruct
			xhour = float(comedtime.hour) + comedtime.minute/60.
			if comedtime.day != now.day:
				continue
			if comedtime.hour != now.hour:
				continue
			print "    %d:%02d -- %.2f"%(comedtime.hour, comedtime.minute, price)
			x.append(xhour)
			currentPrices.append(price)
			
		#--------------------------------------
		yarray = numpy.array(currentPrices, dtype=numpy.float64)
		ymean = yarray.mean()
		ystd = yarray.std()
		ymedian = numpy.median(yarray)
		ymax = yarray.max()
		print ("avg %d:00 -> %2.2f +- %2.2f -> %.1f/%.1f"
			%(int(x[0]), ymean, ystd, yarray.min(), ymax))
		datapoints = numpy.array([ymean, ymax, ymedian], dtype=numpy.float64)
		print datapoints
		finalrate = datapoints.mean()
		return finalrate

	#======================================
	def enable(self):
		if self.proc is None:
			cmd = "nice -+19 %s"%(self.minercmd)
			self.proc = subprocess.Popen(cmd, shell=True,
				stdout=subprocess.PIPE, stderr=subprocess.PIPE, )
			print "started miner program, pid %d"%(self.proc.pid)
			return
		print "miner already running, pid %d"%(self.proc.pid)

	#======================================
	def disable(self):
		if self.proc is not None:
			print "killing miner"
			self.proc.kill()
			# wait for kill to finish?
			self.proc.communicate()
			self.proc = None
		pass

	#======================================
	def __del__(self):
		self.disable()
		pass

#======================================
if __name__ == '__main__':
	count = 0
	refreshTime = 300
	smartminer = SmartMiner()
	while(True):
		#--------------------------------------
		if count > 0:
			factor = (math.sqrt(random.random()) + math.sqrt(random.random()))/1.414
			sleepTime = refreshTime*factor
			print("Sleep %d seconds"%(sleepTime))
			time.sleep(sleepTime)
		count += 1

		#--------------------------------------
		now = datetime.datetime.now()
		hour = now.hour
		if hour in badHours:
			if now.minute < 20:
				print "mining disabled, bad hour, sleep until %d:20"%(hour)
				smartminer.disable()
				minutesToSleep = 20 - now.minute
				sleepTime = minutesToSleep*60 - refreshTime
				if sleepTime > 0:
					time.sleep(sleepTime)
				continue
		else:
			print "good hour %d"%(hour)

		#--------------------------------------
		rate = smartminer.getCurrentComedRate()
		if rate is None:
			continue
		print("final rate %.2f"%(rate))

		#--------------------------------------
		if rate > 2.0*miningCutoffPrice and now.minute > 20:
			print "mining disable over six cents per kWh ( %.2f )"%(rate)
			smartminer.disable()
			print "wait out the rest of the hour"
			minutesToSleep = 60 - now.minute
			sleepTime = minutesToSleep*60 - refreshTime
			if sleepTime > 0:
				time.sleep(sleepTime)
			continue

		#--------------------------------------
		if rate > float(miningCutoffPrice):
			print "mining disabled, rate too high, %.2f cents per kWh"%(rate)
			smartminer.disable()
			continue

		#--------------------------------------
		print "mining enabled"
		smartminer.enable()


