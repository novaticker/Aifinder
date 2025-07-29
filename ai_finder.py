# ai_finder.py

import numpy as np
from datetime import datetime, timedelta

class AIFinder:
    def __init__(self):
        self.price_history = {}  # {symbol: [price1, price2, ...]}
        self.volume_history = {}  # {symbol: [volume1, volume2, ...]}
        self.threshold_zscore = 3.0  # Z-score threshold for anomaly

    def update(self, symbol, price, volume):
        now = datetime.utcnow()

        if symbol not in self.price_history:
            self.price_history[symbol] = []
            self.volume_history[symbol] = []

        # Append new data
        self.price_history[symbol].append((now, price))
        self.volume_history[symbol].append((now, volume))

        # Keep last 3 minutes of data
        self.price_history[symbol] = [x for x in self.price_history[symbol] if now - x[0] <= timedelta(minutes=3)]
        self.volume_history[symbol] = [x for x in self.volume_history[symbol] if now - x[0] <= timedelta(minutes=3)]

        # Analyze
        return self.detect_spike(symbol)

    def detect_spike(self, symbol):
        prices = [p for t, p in self.price_history[symbol]]
        volumes = [v for t, v in self.volume_history[symbol]]

        if len(prices) < 10 or len(volumes) < 10:
            return False, None

        # Z-score
        price_z = (prices[-1] - np.mean(prices)) / (np.std(prices) + 1e-6)
        volume_z = (volumes[-1] - np.mean(volumes)) / (np.std(volumes) + 1e-6)

        if price_z > self.threshold_zscore and volume_z > self.threshold_zscore:
            return True, {
                'symbol': symbol,
                'price': prices[-1],
                'price_z': round(price_z, 2),
                'volume_z': round(volume_z, 2),
                'detected_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            }

        return False, None
