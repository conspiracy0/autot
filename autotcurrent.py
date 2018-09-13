from binance.client import Client
from binance.websockets import BinanceSocketManager
import math
from collections import deque

class updater:
	updates = 0.0
	RSI = 0.0
	client = Client("","") #Api keys go here
	MACD = 0.0
	balanceETH = 1.0
	balanceCoin = 18600
	signal = deque()
	SMA = deque()
	avgGain = 0.0
	avgLoss = 0.0 
	botTrades = list()
	lastTime = 0
	lastOpen = 0.0
	lastClose = 0.0
	MACDAboveSignal = None
	change = 0.0
	lastChange = 0.0
	RSItracker = deque()
	klines = client.get_historical_klines('TRXETH', Client.KLINE_INTERVAL_1MINUTE, "30 minutes ago UTC")
	klinesRSI = client.get_historical_klines('TRXETH', Client.KLINE_INTERVAL_1MINUTE, "250 minutes ago UTC")
	def __init__(self):
		updater.initRSI() #RSI6
		updater.initMACD()
	def process_message(msg):
	#this basically updates everytime theres a new push from the server -- 
	#whenever a kline for the next time period is reached, it updates the RSI and MACD based on the last recieved value
		time = float(msg['k']['t'])
		if time > updater.lastTime:
			if (updater.lastOpen == 0.0 and updater.lastClose == 0.0):
				updater.lastOpen = float(msg['k']['o'])
				updater.lastClose = float(msg['k']['c'])
			updater.lastTime = time
			updater.updates += 1
			updater.updateMetrics() ##only runs update metrics after the time is confirmed
			updater.updateTracker()
			if ((updater.RSI > 60 and updater.MACDAboveSignal == False and updater.balanceCoin> 0) or (updater.RSI > 70 and updater.balanceCoin > 0)):
				market = updater.client.get_symbol_ticker() ## takes all symbol data and searches for TRX
				price = 0.0
				for value in market:
					if 'TRXETH' in value['symbol']:
						price = float(value['price'])
				if len(updater.botTrades) == 0: #since the equivalent price of TRX for 1 ETH varies, this makes it so that the original price is always equivalent to 1 ETH
					updater.balanceCoin = 1/price
				formerTRX = updater.balanceCoin
				updater.balanceETH = updater.balanceCoin*price
				updater.balanceCoin = 0
				updater.botTrades.append("Acquired " + str(updater.balanceETH) + " ETH for " + str(formerTRX)+ " TRX at " +str(price)  + " TRX/ETH")
				updater.change = updater.balanceETH - 1
				updater.lastChange = updater.balanceETH - updater.lastChange
			if ((updater.RSI < 40 and updater.MACDAboveSignal == True and updater.balanceETH > 0) or (updater.RSI < 25 and updater.balanceETH > 0)):
				market = updater.client.get_symbol_ticker() ## takes all symbol data and searches for TRX
				price = 0.0
				for value in market:
					if 'TRXETH' in value['symbol']:
						price = float(value['price'])
				formerETH = updater.balanceETH
				updater.balanceCoin = updater.balanceETH/price
				updater.balanceETH = 0
				updater.botTrades.append("Acquired " + str(updater.balanceCoin) + " TRX for " + str(formerETH)+ " ETH at " +str(price)  + " TRX/ETH")
				updater.change = (updater.balanceCoin*price) - 1
				updater.lastChange = (updater.balanceCoin*price) - updater.lastChange
			if len(updater.botTrades) > 0:
				for value in updater.botTrades:
					print(value)
				print("ETH Balance: ", str(updater.balanceETH), "TRX Balance: ", str(updater.balanceCoin))
				print("Portfolio change from start: ", str(updater.change), " ETH")
				print("Portfolio change since last trade: ", str(updater.lastChange), " ETH \n")
		#this updates for every call
		updater.lastOpen = float(msg['k']['o'])
		updater.lastClose = float(msg['k']['c'])

	def initRSI(): ## THIS USES RSI 6
		count = 0
		tempLoss = 0.0
		tempGain = 0.0
		for value in updater.klinesRSI:
			opens = float(value[4])
			close = float(value [1])
			if opens > close:
				tempLoss += (opens - close)
			else:
				tempGain += (close - opens)
			count += 1
			if count == 6:
				updater.avgGain = tempGain/6
				updater.avgLoss = tempLoss/6
				updater.RSI = 100 - (100/ (1 + (updater.avgGain/updater.avgLoss)))
			if count > 6:
				if opens > close:
					updater.avgLoss = ((updater.avgLoss*5)+(opens - close))/6
				else:
					updater.avgGain = ((updater.avgGain*5)+(close - opens))/6
				updater.RSI = 100 - (100/ (1 + (updater.avgGain/updater.avgLoss)))
		print("RSI initialized at ", updater.RSI)
		
	def updateMetrics(): 
		#RSI update
		if updater.lastOpen > updater.lastClose:
			updater.avgLoss = ((updater.avgLoss*5)+(updater.lastOpen - updater.lastClose))/6
		else:
			updater.avgGain = ((updater.avgGain*5)+(updater.lastClose - updater.lastOpen))/6
		
		updater.RSI = 100 - (100/ (1 + (updater.avgGain/updater.avgLoss)))

		#MACD update
		updater.SMA.append(updater.lastClose)
		EMA12 = updater.SMA[(len(updater.SMA)-1)] - (((math.fsum(updater.SMA)-(updater.SMA[(len(updater.SMA)-1)]))/len(updater.SMA)) * (2/13)) + (((math.fsum(updater.SMA)-(updater.SMA[(len(updater.SMA)-1)]))/len(updater.SMA)))
		EMA26 = updater.SMA[(len(updater.SMA)-1)] - (((math.fsum(updater.SMA)-(updater.SMA[(len(updater.SMA)-1)]))/len(updater.SMA)) * (2/27)) + (((math.fsum(updater.SMA)-(updater.SMA[(len(updater.SMA)-1)]))/len(updater.SMA)))
		updater.MACD = EMA12 - EMA26
		updater.signal.append(updater.MACD)
		print("New MACD: ",updater.MACD, "  New RSI: ", updater.RSI)
		if len(updater.signal) > 9:
			updater.signal.popleft()
		if len(updater.SMA) > 250:
			updater.SMA.popleft()
		if len(updater.signal) == 9:
			print("Signal line at: ", math.fsum(updater.signal)/9)
			if sum(updater.signal)/9 > updater.MACD: 
				updater.MACDAboveSignal = False
			else:
				updater.MACDAboveSignal = True
			print("MACD above signal line? ", updater.MACDAboveSignal)
		print("Open and Close entered at ", updater.lastOpen, updater.lastClose)

	def updateTracker():
		updater.RSItracker.append(updater.RSI)
		if updater.updates % 20 == 0:
			sub20 = 0
			to30 = 0
			to40 = 0
			to50 = 0
			to60 = 0
			to70 = 0
			to80 = 0
			super80 = 0
			for value in updater.RSItracker:
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
		if len(updater.RSItracker) > 200:
			updater.RSItracker.popleft()
		
	def initMACD():
		for value in updater.klines:
			updater.SMA.append(float(value[4]))
		EMA12 = updater.SMA[29] - (((math.fsum(updater.SMA)-(updater.SMA[29]))/len(updater.SMA)) * (2/13)) + (((math.fsum(updater.SMA)-(updater.SMA[29]))/len(updater.SMA)))
		EMA26 = updater.SMA[29] - (((math.fsum(updater.SMA)-(updater.SMA[29]))/len(updater.SMA)) * (2/27)) + (((math.fsum(updater.SMA)-(updater.SMA[29]))/len(updater.SMA)))
		updater.MACD = EMA12 - EMA26
		updater.signal.append(updater.MACD)
		print("MACD initialized at ", updater.MACD)

updater()
bm = BinanceSocketManager(updater.client)
conn_key = bm.start_kline_socket('TRXETH', updater.process_message)
bm.start()


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

