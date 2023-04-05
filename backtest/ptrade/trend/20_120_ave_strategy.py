import logging

import numpy as np
import collections

import pandas as pd
import xcsc_tushare as xc
import pickle
import datetime as dt

def initialize(context):
    # 初始化此策略
    g.is_trade_flag = is_trade()
    if g.is_trade_flag:
        pass
    else:
        set_backtest()
#设置回测条件
def set_backtest():
    set_limit_mode('UNLIMITED')
    set_commission(commission_ratio=0.00005, min_commission =5.0,type="ETF")



def before_trading_start(context, data):
    current_date = context.blotter.current_dt
    trade_date = dt.datetime.strftime(current_date,"%Y%m%d")
    yes_date_str = dt.datetime.strftime( context.previous_date ,"%Y%m%d")
    xc.set_token('4d0cd91bc89c0e6883fe730fb5bebdca577879eedae349e2feb2acc9')
    pro = xc.pro_api(server='http://10.208.110.21:7172')
    df = pro.sw_index_daily(trade_date=trade_date)
    yes_df = pro.sw_index_daily(trade_date=yes_date_str)
    categary = pro.index_code_all(levelnum=2)
    sw_first_list = []
    for i,line in categary.iterrows():
        if line["industriescode"].startswith("61"):
            sw_first_list.append(line["industriesalias"]+".SI")

    max_dic={"code" : "","value":0}
    for i,line in df.iterrows():
        code = line["ts_code"]
        if code in sw_first_list:
            volume = line["volume"]
            yes_volume= yes_df.loc[yes_df["ts_code"]==code,"volume"].iloc[0]
            if volume is not None and volume>0 and yes_volume is not None and yes_volume>0:
                vratio = volume/yes_volume
                if vratio>max_dic["value"]:
                    max_dic["code"]=code
                    max_dic["value"]=vratio
    # log.info(max_dic)
    today_stock= pro.sw_index_member(ts_code=max_dic["code"],cur_sign=1)
    max_stock={"code" : "","value":0}
    for i,line in today_stock.iterrows():
        stock_code = line["con_ts_code"]
        today=pro.daily_basic_ts(ts_code=stock_code,trade_date=trade_date)
        yes=pro.daily_basic_ts(ts_code=stock_code,trade_date=yes_date_str)
        if len(today)!=0 and len(yes)!=0:
            today_turnover_rate= today.ix[0,"turnover_rate"]
            yes_turnover_rate= yes.ix[0,"turnover_rate"]
            if today_turnover_rate is not None and today_turnover_rate>0 and yes_turnover_rate is not None and yes_turnover_rate>0:
                tratio = today_turnover_rate/yes_turnover_rate
                if tratio>max_stock["value"]:
                    max_stock["code"]=stock_code
                    max_stock["value"]=tratio
    log.info(max_stock)
    # set_universe(g.security)


# 交易
def handle_data(context, data):
    pass




