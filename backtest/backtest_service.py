from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from datetime import datetime  # For datetime objects

import backtrader as bt

import backtest.dataloader as dt_loader
from backtest.strategy.test_strategy import TestStrategy
from backtest.strategy.turtle_strategy import (TurtleStrategy,TurtleSizer)
from backtest.strategy.grid_trading_strategy import GridTradingStrategy





def back_test_service(stock):
    # Create a cerebro entity
    cerebro = bt.Cerebro()
    # # Add a backtest-TurtleStrategy
    # cerebro.addstrategy(TurtleStrategy)
    # cerebro.addsizer(TurtleSizer)
    # Add a backtest-GRID


    dt=dt_loader.load_data(stock.code)


    cerebro.addstrategy(GridTradingStrategy,code=stock.name,indicator=stock.indicator)
    # 当日下单，当日收盘价成交

    # Datas are in a subfolder of the samples. Need to find where the script is
    # because it could have been called from anywhere
    # start_date = datetime(2015, 1, 28)
    start_date = datetime(2022, 11, 10)

    end_date = datetime.now()
    # end_date = datetime(2022, 11, 19)

    # Create a Data Feed
    data = bt.feeds.PandasData(dataname=dt, fromdate=start_date, todate=end_date)
    # Add the Data Feed to Cerebro
    cerebro.adddata(data)
    # Set our desired cash start
    cerebro.broker.setcash(50000)
    # Add a FixedSize sizer according to the stake
    # cerebro.addsizer(bt.sizers.FixedSize, stake=10)

    # Set the commission
    cerebro.broker.setcommission(commission=0.003)
    # Print out the starting conditions
    start_money = cerebro.broker.getvalue()
    cerebro.addobserver(bt.observers.TimeReturn,timeframe=bt.TimeFrame.NoTimeFrame)
    benchdata = data
    cerebro.addobserver(bt.observers.Benchmark,
                            data=benchdata,
                            timeframe=bt.TimeFrame.NoTimeFrame)
    cerebro.addobserver(bt.observers.Benchmark,
                        data=benchdata,
                        timeframe=bt.TimeFrame.Years)
    # Run over everything
    cerebro.broker.set_coc(True)

    cerebro.run()
    # Print out the final result
    end_money = cerebro.broker.getvalue()
    print('最后收益: %.2f' % (end_money - start_money))
    # Plot the result
    cerebro.plot()
