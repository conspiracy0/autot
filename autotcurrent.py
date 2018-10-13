from binance.client import Client
from binance.websockets import BinanceSocketManager
import math
import csv
from collections import deque
import threading
import winsound
import time
class updater(threading.Thread):
	
	def __init__(self, s):
		self.client = Client("","")
		self.botTrades = list()
		self.SMA = deque()
		self.token = s
		self.balanceETH = 1.0
		self.balanceCoin = 1
		self.signal = 0.0
		self.avgGain = 0.0
		self.avgLoss = 0.0 
		self.lastTime = 0
		self.lastOpen = 0.0
		self.lastClose = 0.0
		self.MACDAboveSignal = bool
		self.change = 0.0
		self.lastChange = 0.0
		self.lastValue = 0.0
		self.MACD = 0.0
		self.updates = 0.0
		self.token = s
		self.klines = self.client.get_historical_klines(self.token, Client.KLINE_INTERVAL_1MINUTE, "30 minutes ago UTC")
		self.klinesRSI = self.client.get_historical_klines(self.token, Client.KLINE_INTERVAL_1MINUTE, "250 minutes ago UTC")
		self.signal = deque()
		self.RSItracker = deque()
		self.initRSI() #RSI6
		self.initMACD()
		self.bm = BinanceSocketManager(self.client)
		self.conn_key = self.bm.start_kline_socket(self.token, self.process_message)
		self.bm.start()
		with open('decimals.csv') as csvfile:
			reader = csv.DictReader(csvfile)
			for row in reader:
				if (row['token'] == self.token):
					self.decimals = row['decimals']
		

	def process_message(self, msg):
	#this basically updates everytime theres a new push from the server -- 
	#whenever a kline for the next time period is reached, it updates the RSI and MACD based on the last recieved value
		time = float(msg['k']['t'])
		if time > self.lastTime:
			print(self.token)
			if (self.lastOpen == 0.0 and self.lastClose == 0.0):
				self.lastOpen = float(msg['k']['o'])
				self.lastClose = float(msg['k']['c'])
			self.lastTime = time
			self.updates += 1
			self.updateMetrics() ##only runs update metrics + tracker after the time is confirmed
			self.updateTracker()
			if self.RSI > 62.5:
				winsound.PlaySound('oh.wav', winsound.SND_FILENAME)
			if self.RSI < 20:
				winsound.PlaySound('uwaa.wav', winsound.SND_FILENAME)
			market = self.client.get_symbol_ticker() ## takes all symbol data and searches for TRX
			for value in market:
				if self.token in value['symbol']:
					price = float(value['price'])
			if (((self.RSI > 65 and self.MACDAboveSignal == False and self.balanceCoin> 0) or (self.RSI > 72.5 and self.balanceCoin > 0)) and (self.lastValue < (self.balanceCoin*price)) and (self.updates > 9)):	
				if len(self.botTrades) == 0: #since the equivalent price of TRX for 1 ETH varies, this makes it so that the original price is always equivalent to 1 ETH
					self.balanceCoin = 1/price
				formerTRX = self.balanceCoin
				self.balanceETH = self.balanceCoin*price
				self.balanceCoin = 0
				self.lastValue = self.balanceETH
				self.botTrades.append("Acquired " + str(self.balanceETH) + " ETH for " + str(formerTRX) + " " + self.token[0:3] +  " at " + str(price) + " " + self.token[0:3] + "/ETH")
				self.change = self.balanceETH - 1
				self.lastChange = self.balanceETH - self.lastChange
			if ((self.RSI < 32.5 and self.MACDAboveSignal == True and self.balanceETH > 0) or (self.RSI < 25 and self.balanceETH > 0)):
				formerETH = self.balanceETH
				self.balanceCoin = self.balanceETH/price
			
				self.balanceETH = 0
				self.botTrades.append("Acquired " + str(self.balanceCoin) +" " +  self.token[0:3] + " for " + str(formerETH)+ " ETH at " +str(price)  + " " + self.token[0:3] + "/ETH")
				self.lastValue = self.balanceCoin*price
				self.change = (self.balanceCoin*price) - 1
				self.lastChange = (self.balanceCoin*price) - self.lastChange
			if len(self.botTrades) > 0:
				for value in self.botTrades:
					print(value)
				print("ETH Balance: ", str(self.balanceETH), " " + self.token[0:3] + " Balance: ", str(self.balanceCoin))
				print("Portfolio change from start: ", str(self.change), " ETH")
				print("Portfolio change since last trade: ", str(self.lastChange), " ETH \n")
		#this updates for every call
		self.lastOpen = float(msg['k']['o'])
		self.lastClose = float(msg['k']['c'])

	def initRSI(self): ## THIS USES RSI 6
		print(self.token)
		count = 0
		tempLoss = 0.0
		tempGain = 0.0
		for value in self.klinesRSI:
			opens = float(value[4])
			close = float(value [1])
			if opens == close:
				continue
			if opens > close:
				tempLoss += (opens - close)
			else:
				tempGain += (close - opens)
			count += 1
			if count == 6:
				self.avgGain = tempGain/6
				self.avgLoss = tempLoss/6
				self.RSI = 100 - (100/ (1 + (self.avgGain/self.avgLoss)))
			if count > 6:
				if opens > close:
					self.avgLoss = ((self.avgLoss*5)+(opens - close))/6
				else:
					self.avgGain = ((self.avgGain*5)+(close - opens))/6
				self.RSI = 100 - (100/ (1 + (self.avgGain/self.avgLoss)))
		print("RSI initialized at ", self.RSI)
		
	def updateMetrics(self): 
		#RSI update
		if self.lastOpen > self.lastClose:
			self.avgLoss = ((self.avgLoss*5)+(self.lastOpen - self.lastClose))/6
		else:
			self.avgGain = ((self.avgGain*5)+(self.lastClose - self.lastOpen))/6
		
		self.RSI = 100 - (100/ (1 + (self.avgGain/self.avgLoss)))

		#MACD update
		self.SMA.append(self.lastClose)
		EMA12 = self.SMA[(len(self.SMA)-1)] - (((math.fsum(self.SMA)-(self.SMA[(len(self.SMA)-1)]))/len(self.SMA)) * (2/13)) + (((math.fsum(self.SMA)-(self.SMA[(len(self.SMA)-1)]))/len(self.SMA)))
		EMA26 = self.SMA[(len(self.SMA)-1)] - (((math.fsum(self.SMA)-(self.SMA[(len(self.SMA)-1)]))/len(self.SMA)) * (2/27)) + (((math.fsum(self.SMA)-(self.SMA[(len(self.SMA)-1)]))/len(self.SMA)))
		self.MACD = EMA12 - EMA26
		self.signal.append(self.MACD)
		print("New MACD: ",self.MACD, "  New RSI: ", self.RSI)
		if len(self.signal) > 9:
			self.signal.popleft()
		if len(self.SMA) > 250:
			self.SMA.popleft()
		if len(self.signal) == 9:
			print("Signal line at: ", math.fsum(self.signal)/9)
			if sum(self.signal)/9 > self.MACD: 
				self.MACDAboveSignal = False
			else:
				self.MACDAboveSignal = True
			print("MACD above signal line? ", self.MACDAboveSignal)
		print("Open and Close entered at ", self.lastOpen, self.lastClose)

	def updateTracker(self):
		self.RSItracker.append(self.RSI)
		if self.updates % 20 == 0:
			sub20 = 0
			to30 = 0
			to40 = 0
			to50 = 0
			to60 = 0
			to70 = 0
			to80 = 0
			super80 = 0
			for value in self.RSItracker:
				if value < 20 :
					sub20 += 1
				elif value < 30:
					to30 += 1
				elif value < 40:
					to40 += 1
				elif value < 50:
					to50 += 1
				elif value < 60:
					to60 += 1
				elif value < 70:
					to70 += 1
				elif value < 80:
					to80 += 1
				else:
					super80 += 1
			print("\n")
			print("RSI TRACKING(Last 200):")
			print("<20 RSI: ", sub20)
			print("20-29 RSI: ", to30)
			print("30-39 RSI: ", to40)
			print("40-49 RSI: ", to50)
			print("50-59 RSI: ", to60)
			print("60-69 RSI: ", to70)
			print("70-79 RSI: ", to80)
			print(">80 RSI: ", super80)
		if len(self.RSItracker) > 200:
			self.RSItracker.popleft()

	def initMACD(self):
		for value in self.klines:
			self.SMA.append(float(value[4]))
		EMA12 = self.SMA[29] - (((math.fsum(self.SMA)-(self.SMA[29]))/len(self.SMA)) * (2/13)) + (((math.fsum(self.SMA)-(self.SMA[29]))/len(self.SMA)))
		EMA26 = self.SMA[29] - (((math.fsum(self.SMA)-(self.SMA[29]))/len(self.SMA)) * (2/27)) + (((math.fsum(self.SMA)-(self.SMA[29]))/len(self.SMA)))
		self.MACD = EMA12 - EMA26
		self.signal.append(self.MACD)
		print("MACD initialized at ", self.MACD)

	def calcProfit(self, p): #calculates the correct sell price for everything
		d = 2 # neo
		p = 0.03 # profit margin(percent)
		self.balanceETH = 1 #
		price = 0.129474 # test, using NEO
		actualBuy = (self.balanceETH -(self.balanceETH * 0.0005)) # actual buy amount after you account for buy fee, in ETH
		amtSell = math.floor((actualBuy/price) *(10**d))/float(10**d) # represents amount sellable, in the currency
		target = ((actualBuy *(1+p))+(actualBuy*0.0005))/amtSell
		 
		print(actualBuy)
		print(amtSell)
		print(target)

client = Client("","")
temp = client.get_ticker()
x = list()
print("Starting initialization")
for value in temp:
	if ((float(value['quoteVolume']) > 5000) and ('ETH' in value['symbol'][3:7])):
		try:
			y = updater(value['symbol'])
			x.append(y)
			time.sleep(10)
		except Exception as e:
			print("memed on")
print("****************")
print("Initialization complete. ")
print("****************")
'''[
    [

        1499040000000,      # Open time
        "0.01634790",       # Open
        "0.0000000",       # High
        "0.01575800",       # Low
        "0.01577100",       # Close
        "148976.11427815",  # Volume
        1499644799999,      # Close time
        "2434.19055334",    # Quote asset volume
        308,                # Number of trades
        "1756.87402397",    # Taker buy base asset volume
        "28.46694368",      # Taker buy quote asset volume
        "17928899.62484339" # Can be ignored
    ]
]'''

