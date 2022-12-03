# Create a Stratey
import backtrader as bt

import collections
from backtest.dataloader import DataLoader
import pandas as pd
import math



class GridTradingStrategy(bt.Strategy):
    params = (
        ('code', '沪深300'),
        ('indicator', '市盈率'),
    )
    def log(self, txt, dt=None):
        ''' Logging function fot this backtest'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.dtload = DataLoader(self.params.code, self.params.indicator)

        # Indicators for Grid
        self.TR = bt.indicators.Max((self.datahigh(0) - self.datalow(0)), abs(self.dataclose(-1) - self.datahigh(0)),
                                    abs(self.dataclose(-1) - self.datalow(0)))
        self.ATR = bt.indicators.SimpleMovingAverage(self.TR, period=14, subplot=True)
        self.grid_wide = self.ATR*0.9
        self.grid_price_deque = collections.deque()

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.last_month = None
        self.cost = None
        self.profit_ratio = None
        self.profit_value =None
        self.stock_ratio =None
        self.has_clear = False
        self.order_is_grid = False
        self.time = 5.0
        self.day=0
        self.stockMoney = 0
        self.needClear = False




    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            if order.status in [order.Submitted]:
                self.log("提交订单成功:数量：%.2f" % order.size)
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                if self.order_is_grid:
                    self.grid_price_deque.appendleft(self.buyprice)
                    self.order_is_grid = False
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))
                if self.order_is_grid:
                    self.grid_price_deque.popleft()
                    self.order_is_grid = False
            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        # Simply log the closing price of the series from the reference
        # self.log('Close, %.2f' % self.dataclose[0])
        self.grid_wide = self.ATR*self.time
        self.needClear=False

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Check if we are in the market
        if not self.position:
            self.open_trading()
        else:
            # 计算当日仓位状态
            self.calculate_position_status()
            # 是否触发清仓检查
            self.clear_or_decrease_check()
            if (not self.needClear):
                # 月定投执行
                self.buy_per_month()
                # 网格交易执行
                self.buy_grid_trading()


        self.day = self.day+1
        self.stockMoney = self.stockMoney+self.broker.getvalue()-self.broker.get_cash()
    def calculate_position_status(self):
        current_price = self.dataclose[0]
        position = self.position
        self.profit_ratio = (current_price / position.price) - 1
        self.profit_value = self.broker.getvalue() - self.broker.startingcash
        self.stock_ratio = 1 - self.broker.get_cash()/self.broker.getvalue()
        self.log("检查当日仓位状态，持仓收益率为 %.2f，收益金额为 %.2f，仓位股票占比 %.2f" % (self.profit_ratio, self.profit_value,self.stock_ratio))

    # 月定投逻辑
    def buy_per_month(self):
        # 得到当天的时间
        current_date = self.datas[0].datetime.date(0)
        price = self.dataclose[0]
        # 如果当天是月初，开始定投
        if self.last_month is None or str(current_date)[:-3] > self.last_month:
            self.last_month = str(current_date)[:-3]
            # 现价<成本价-1ATR，加仓200
            if(self.position.price-self.ATR > price):
                self.buy_stock(money=200*self.time)


    # 开仓逻辑
    def open_trading(self):
        #市盈率小于等于平均值开始建仓
        current_date = self.datas[0].datetime.date(0)
        indicator = self.dtload.get_by_date(current_date.isoformat())
        if indicator is not None and not pd.isnull(indicator.最低30):
            self.buy_stock(money=5000)
            self.log("开始建仓，买入金额 %.2f" % (5000))

    # 网格交易逻辑
    def buy_grid_trading(self):
        current_price = self.dataclose[0]
        # 判定是否可以开始第一次网格交易
        can_trigger_first_grid = self.need_trigger_first_grid()
        position = self.position
        self.log("当前持仓收益率%s,网格宽度%.4f,current_price:%s,position.price:%s" % (self.profit_ratio,self.grid_wide,current_price,position.price))
        # 触发买入,第一次触发网格买入或者当前价格<=上一次网格买入价格-网格宽度
        if (can_trigger_first_grid and len(self.grid_price_deque) == 0) or (len(self.grid_price_deque) !=0 and current_price <= self.grid_price_deque[0]-self.grid_wide):
            self.log("触发网格买入")
            if(self.profit_ratio<0):
                self.buy_stock(800*self.time)
            else:
                self.buy_stock(300*self.time)
            self.order_is_grid = True

        #触发卖出，当前价格>=上一次网格买入价格+网格宽度
        if len(self.grid_price_deque)!=0 and current_price >= self.grid_price_deque[0] + self.grid_wide and position.size > 0:
            self.log("触发网格卖出")
            if self.profit_ratio < 0:
                self.sell_stock(300*self.time)
            elif self.profit_ratio<= 0.2:
                self.sell_stock(600*self.time)
            else:
                self.sell_stock(800*self.time)
            self.order_is_grid = True

    # 清仓减仓逻辑
    def clear_or_decrease_check(self):
        # 清仓逻辑
        current_date = self.datas[0].datetime.date(0)
        indicator = self.dtload.get_by_date(current_date.isoformat())
        # if indicator is not None and not pd.isnull(indicator.最高30):
        if self.profit_ratio>=0.6 and self.profit_value >= 6000:
            self.log("执行清仓，清仓时持仓收益率为 %.2f，收益金额为 %.2f" % (self.profit_ratio, self.profit_value))
            self.needClear = True
            self.order_target_percent(target=0)

        # if(self.profit_ratio >= 0.2 and self.stock_ratio > 0.5):
        #     self.log("执行减仓，减仓时持仓收益率为 %.2f，收益金额为 %.2f" % (self.profit_ratio, self.profit_value))
        #     self.sell_stock(200)

    # 是否能触发开启网格交易
    def need_trigger_first_grid(self):
        # # 触发网格逻辑,市盈率小于等于平均值做网格
        # current_date = self.datas[0].datetime.date(0)
        # indicator = self.dtload.get_by_date(current_date.isoformat())
        # if indicator is None:
        #     return False
        # if pd.isnull(indicator.最低30):
        #     return False
        return True



    def buy_stock(self,money):
        size = int(money / self.dataclose[0])
        self.log("提交订单，买入日期:%s,买入数量:%s" % (self.datas[0].datetime.date(0), size))
        self.order = self.buy(size=size)

    def sell_stock(self,money):
        # size = math.ceil(int(money / self.dataclose[0])/100)*100
        size = int(money / self.dataclose[0])
        self.log("提交订单，卖出日期:%s,卖出数量:%s" % (self.datas[0].datetime.date(0), size))
        self.order = self.sell(size=size)

    def stop(self):
        self.log('Ending Value %.2f,start value %.2f,profit is %.2f,aveCost is %.2f,aveRevenueRatio is %.2f' % (self.broker.getvalue(),self.broker.startingcash,self.profit_value,self.stockMoney/self.day,(self.profit_value/(self.stockMoney/self.day))/(self.day/365)))




