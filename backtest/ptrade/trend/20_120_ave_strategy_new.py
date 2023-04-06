import datetime
import logging

import numpy as np
import collections
import time


import pandas as pd
import xcsc_tushare as xc
import pickle
import datetime as dt

def initialize(context):
    # 初始化此策略
    g.is_trade_flag = is_trade()
    g.hot_sw=["801080.SI","801750.SI"]
    g.this_position =[]
    # g.today_buy=[]
    # g.cir_value=1000000
    g.num=5
    if g.is_trade_flag:
        pass
    else:
        set_backtest()
#设置回测条件
def set_backtest():
    set_limit_mode('UNLIMITED')
    set_commission(commission_ratio=0.00005, min_commission =5.0)



def before_trading_start(context, data):
    g.today_security=[]
    g.today_buy=[]
    # dif = g.num - len(g.this_position)
    # if dif>0:
    #     current_date = context.blotter.current_dt
    #     trade_date = dt.datetime.strftime(current_date,"%Y%m%d")
    #     yes_date_str = dt.datetime.strftime( context.previous_date ,"%Y%m%d")
    xc.set_token('4d0cd91bc89c0e6883fe730fb5bebdca577879eedae349e2feb2acc9')
    g.pro = xc.pro_api(server='http://10.208.110.21:7172')
        # # # 仿真
        # g.pro = xc.pro_api(env='prd', server='http://116.128.206.39:7172')
        # ashares = get_Ashares()

def after_trading_end(context, data):
    sec_list = {}
    for ts_code in g.hot_sw:
        today_stock = g.pro.sw_index_member(ts_code=ts_code, cur_sign=1)
        # log.info(today_stock)
        sec_list[ts_code] = select_shares(today_stock["con_ts_code"].values)
    log.info(sec_list)
    send_email('805784078@qq.com', ['805784078@qq.com','1204597411@qq.com'], 'wcavijswtjvdbedc', info='明天关注的股票池信息:'+str(sec_list))


def select_shares(stock_list):
    st_info = get_stock_status(stock_list, query_type='ST', query_date=None)
    half_info = get_stock_status(stock_list, query_type='HALT', query_date=None)
    delisting_info = get_stock_status(stock_list, query_type='DELISTING', query_date=None)
    max_value={}
    for security in stock_list:
        if st_info[security] is False and half_info[security] is False and delisting_info[security] is False:
            # 得到十日历史价格
            df = get_history(121, '1d',field=['volume','close','open'], security_list= security, fq='dypre', include=True)
            if(len(df)==121):
                today = df.tail(120)
                yes = df.head(120)
                last = df.tail(2)
                today_vol = last.ix[1, "volume"]
                yes_vol = last.ix[0, "volume"]
                # 取得昨天收盘价
                price_close = last.ix[1, "close"]
                price_open = last.ix[1, "open"]

                # 得到5日均线价格
                today_ma5 = round(today['close'][-5:].mean(), 3)
                # 得到20日均线价格
                today_ma20 = round(today['close'][-20:].mean(), 3)

                # 得到120日均线价格
                today_ma120 = round(today['close'][-120:].mean(), 3)

                start_price = today.ix[0,"close"]
                end_price = today.ix[119,"close"]
                rat= end_price/start_price
                # 得到20日均线价格
                yes_ma20 = round(yes['close'][-20:].mean(), 3)

                # 得到120日均线价格
                yes_ma120 = round(yes['close'][-120:].mean(), 3)

                # 如20日均线大于120日均线,且小于120均线*1.01.认为金叉,且站在5日线之上的
                if today_ma20 >= today_ma120 and rat>1 and today_ma5< price_close:
                    tratio_this = today_vol / yes_vol
                    if today_ma20<=today_ma120 * 1.02 and yes_ma20<yes_ma120 and price_close<today_ma120 * 1.05:
                        if tratio_this >= 2.0:
                            # log.info(security)
                            # judge_share(pro,trade_date,yes_date_str,security,max_value,tratio_this)
                            max_value[security] = tratio_this
                    # #20日线附近的股票,且当日收盘价>MA20
                    if price_close/today_ma20-1<0.02 and price_close>=today_ma20 and price_close>price_open and today_ma20>yes_ma20:
                        if tratio_this >= 1.5:
                            # log.info(security)

                            # judge_share(pro,trade_date,yes_date_str,security,max_value,tratio_this)
                            max_value[security] = tratio_this
    sorted_dic= sorted(max_value.items(), key=lambda item: item[1],reverse=True)
    # log.info(sorted_dic)
    list_sec =[]
    for item in sorted_dic[:g.num]:
        list_sec.append(item[0])
    # log.info(list_sec)
    return list_sec
    # g.today_security=list_sec
    # set_universe(g.today_security)

# #判断股票是否符合选股条件
# def judge_share(pro,trade_date,yes_date_str,security,max_value,tratio_this):
#     today = pro.daily_basic_ts(ts_code=security, trade_date=trade_date)
#     yes = pro.daily_basic_ts(ts_code=security, trade_date=yes_date_str)
#     if len(today) != 0 and len(yes) != 0:
#         circ_mv = today.ix[0, "circ_mv"]
#         #市值单位是W
#         if circ_mv is not None and circ_mv > 0 and circ_mv <= g.cir_value:
#             max_value[security]=tratio_this

# 交易
def handle_data(context, data):
    # if len(g.today_security)>0:
    #     open_trade(context)
    # else:
    #     sell(context)
    pass

# def open_trade(context):
#     per_cost = context.portfolio.cash/len(g.today_security)
#     for sec in g.today_security:
#         order_target_value(sec,per_cost)
#         g.this_position.append(sec)
#         g.today_buy.append(sec)
#
# def sell(context):
#     for sec in g.this_position:
#         if sec not in g.today_buy:
#             df = get_history(1, '1d', field=['close'], security_list = sec, fq='dypre',
#                              include=True)
#             current_price = df['close'].values[0]
#             df_8 = get_history(8, '1d', field=['close'], security_list=sec, fq='dypre',
#                              include=True)
#             MA5 = round(df_8['close'][-5:].mean(), 3)
#             MA8 = round(df_8['close'][-8:].mean(), 3)
#
#             # 当日收盘价低于5日线,第二天清仓
#             if(MA5 <= MA8):
#                 order_target_value(sec, 0)
#                 g.this_position.remove(sec)








