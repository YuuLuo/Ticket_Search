from datetime import timedelta

DEFAULT_YEAR = 2026
TARGET_CLASSES = "V"
MAX_RESULTS = 5000

ROUTE = [
    "LAX", "SEA", "ANC", "MSP", "GRR",
    "DTW", "CVG", "DCA", "LGA","SYR","JFK","BOS",
    "DXB"
]

MIN_LAYOVER = timedelta(minutes=45)
MAX_LAYOVER = timedelta(hours=24)

BROWSER_USER_DATA_DIR = ".browser_data"
EXPERTFLYER_URL = "https://www.expertflyer.com"
