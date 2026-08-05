import yfinance as yf

YAHOOPROXY = 'http://127.0.0.1:7890'
yf.set_config(proxy=YAHOOPROXY)

# 获取股票数据
symbol = "600519.SS"
start_date = "2022-01-01"
end_date = "2023-01-01"

data = yf.download(symbol, start=start_date, end=end_date)
print(data.head())