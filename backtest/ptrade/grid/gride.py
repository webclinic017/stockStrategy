import logging

import numpy as np
import collections

import pandas as pd
import xcsc_tushare as xc
import pickle
import time

def initialize(context):
    # g.security = ['512480.SS','560880.SS','517090.SS','512880.SS','510310.SS','159952.SZ','512680.SS','513100.SS']
    # g.sec_estimate_map = {'512480.SS':"",'560880.SS':"",
    #                       '517090.SS':"",'512880.SS':"",
    #                       '510310.SS':"",'159952.SZ':"",
    #                       '512680.SS':"",'513100.SS':""}
    # g.sec_estimate_indicator = {}
    # xc.set_token('4d0cd91bc89c0e6883fe730fb5bebdca577879eedae349e2feb2acc9')
    # pro = xc.pro_api(server='http://10.208.110.21:7172')
    # df = pro.sw_index_daily(ts_code="801080.SI")
    # log.info(df)

    g.last_month = None
    g.open_dict = {}
    g.grid_price_deque_dict = {}
    g.have_init_grid={}
    g.atr_time = 2
    g.atr_period = 100
    g.is_trade_flag = is_trade()
    g.atr_dict = {}
    if g.is_trade_flag:
        g.path = get_research_path() + "grid_log_prod/griddata.csv"
    else:
        set_backtest()
        g.path = get_research_path() + "grid_log/griddata.csv"

#设置回测条件
def set_backtest():
    set_limit_mode('UNLIMITED')
    set_commission(commission_ratio=0.00005, min_commission =5.0,type="ETF")


def before_trading_start(context, data):
    # 初始化此策略
    sec_path = get_research_path() + "grid_strategy/sec.csv"
    sec_df = pd.read_csv(sec_path)
    g.security = []
    for i, line in sec_df.iterrows():
        g.security.append(line['code'])
    set_universe(g.security)

    for sec in g.security:
        if sec not in g.grid_price_deque_dict:
            g.grid_price_deque_dict[sec] = collections.deque()
            g.have_init_grid[sec]=False
    if g.is_trade_flag:
        init_grid(context)

    log.info("当日持仓金额:%s,持仓收益率:%s,持仓收益%s"%(context.portfolio.positions_value,context.portfolio.returns,context.portfolio.pnl))
    g.trade_per_month_flag={}

    for sec in g.security:
        # 重置月定投flag
        g.trade_per_month_flag[sec] = "N"
        # ATR for Grid
        cal_atr(sec)
        # todo 指数市盈率
        #check 并且重置开仓标志位
        if g.is_trade_flag is not True:
            if context.portfolio.positions[sec].amount==0:
                g.open_dict[sec] = "N"
    log.info("当日ATR数据"+ str(g.atr_dict))

def init_grid(context):
    sec_grid_df = pd.read_csv(g.path)
    for sec in g.security:
        grid_deque = g.grid_price_deque_dict[sec]
        before_grid = sec_grid_df.loc[sec_grid_df["code"]==sec,"grid"]
        if len(before_grid)>0:
            before_grid_value_list = str(before_grid.iloc[0]).split(",")
            for grid in before_grid_value_list:
                grid_deque.append(float(grid))
            g.have_init_grid[sec] = True
        if sec in context.portfolio.positions:
            sec_position = context.portfolio.positions[sec]
            if sec_position.amount > 0 and g.have_init_grid[sec] is False:
                grid_deque.appendleft(sec_position.cost_basis)
                g.have_init_grid[sec] = True
        log.info("初始化网格, code:%s,grid:%s"%(sec,str(grid_deque)))

# 网格及交易
def handle_data(context, data):
    for security in g.security:
        trade(security,context, data)

def on_trade_response (context, trade_list):
    logging.info("网格买入成功:"+str(trade_list))
    for trade in trade_list:
        if trade.status == "8" or trade.status == "7":
            grid_price_deque = g.grid_price_deque_dict[trade["stock_code"]]
            # 买
            if trade["entrust_bs"]=="1":
                grid_price_deque.appendleft(trade["business_price"])
            # 卖
            if trade["entrust_bs"]=="2":
                grid_price_deque.popleft()
                if len(grid_price_deque) == 0:
                    grid_price_deque.appendleft(trade["business_price"])



def trade(security,context, data):
    h = get_history(1, '1m', field=['close', 'volume'], security_list=security, fq='dypre', include=True)
    position = get_position(security)
    openorder = get_open_orders(security)

    #如果存在价格，交易
    if len(h['close'].values)>0:
        current_price = h['close'].values[0]
        # 交易模式手动建仓，回测自动开仓
        if g.is_trade_flag is False:
            open_trading(current_price, security, context, data)
        # 如果有仓位且不存在未完成订单，做网格
        if position.amount>0 and len(openorder)==0:
            profit_ratio = position.last_sale_price/position.cost_basis-1
            profit_value = profit_ratio*position.cost_basis*position.amount
            buy_per_month(security,current_price,position.cost_basis,profit_ratio,profit_value,context)
            grid_trade(security,profit_ratio,profit_value,current_price,context)

# def after_trading_end(context, data):
#     grid_list=[]
#     for sec in g.grid_price_deque_dict.keys():
#         dic={}
#         dic["code"]=sec
#         list = []
#         for ele in g.grid_price_deque_dict[sec]:
#             list.append(str(ele))
#         dic["grid"]=",".join(list)
#         grid_list.append(dic)
#     pf = pd.DataFrame(grid_list, columns=["code", "grid"])
#     pf.to_csv(g.path, index=False)

# 开仓逻辑
def open_trading(current_price,security,context, data):
    # #市盈率小于等于平均值开始建仓
    # current_date = self.datas[0].datetime.date(0)
    # indicator = self.dtload.get_by_date(current_date.isoformat())
    # if indicator is not None and not pd.isnull(indicator.最低30):
    if g.open_dict[security]=="N":
        grid_price_deque = g.grid_price_deque_dict[security]
        order_id = order_value(security, 20000)
        if order_id is not None:
            order = get_order(order_id)[0]
            # log.info(order)
            if order.status =="8" or order.status =="7":
                log.info(security+":开始建仓，买入金额 %.2f" % (20000))
                g.open_dict[security]='Y'
                grid_price_deque.appendleft(current_price)

def grid_trade(security,profit_ratio,profit_value,current_price,context):
    grid_price_deque = g.grid_price_deque_dict[security]
    cash = context.portfolio.cash
    # 触发买入,第一次触发网格买入或者当前价格<=上一次网格买入价格-网格宽度
    if current_price <= grid_price_deque[0] - g.atr_dict[security]*g.atr_time and cash>300:
        if (profit_ratio < 0):
            grid_trade_buy(current_price,security,4800,grid_price_deque)
        else:
            grid_trade_buy(current_price,security,1800,grid_price_deque)

    # 触发卖出，当前价格>=上一次网格买入价格+网格宽度
    if  current_price >= grid_price_deque[0] + g.atr_dict[security]*g.atr_time:
        if profit_ratio < 0:
            grid_trade_buy(current_price,security,-1800,grid_price_deque)
        elif profit_ratio <= 0.2:
            grid_trade_buy(current_price,security,-3600,grid_price_deque)
        else:
            grid_trade_buy(current_price,security,-4800,grid_price_deque)

def grid_trade_buy(current_price,security,amount,grid_price_deque):
    log.info(security + ":触发网格买入:"+str(amount))
    position = get_position(security)
    num = int(amount/current_price)
    num= num%100*100
    if num > position.amount:
        num = position.amount
    limit_price = current_price
    if amount>0:
        limit_price = round(current_price*1.02,3)
    if amount<0:
        limit_price = round(current_price*0.98,3)

    if g.is_trade_flag is True:
        order_id = order_market(security, num,4,limit_price)
    else:
        order_id = order(security, num)

    # if g.is_trade_flag is False:
    #回测这里网格出入队列，交易用trade主推接口
    if order_id is not None:
        # order =get_order(order_id)[0]
        # log.info(order)
        # if order.status == "8" or order.status == "7":
        log.info(security + ":网格买入成功:" + str(amount))
        if amount>0:
            grid_price_deque.appendleft(current_price)
        if amount<0:
            grid_price_deque.popleft()
            if len(grid_price_deque) == 0:
                grid_price_deque.appendleft(current_price)


# 月定投逻辑
def buy_per_month(security,current_price,cost_basis,profit_ratio,profit_value,context):
    # 得到当天的时间,
    current_date = context.blotter.current_dt
    cash = context.portfolio.cash

    # 如果当天是月初，开始定投
    if g.trade_per_month_flag[security] =="N" and (g.last_month is None or str(current_date)[:-12] > g.last_month):
        g.last_month = str(current_date)[:-12]
        # 现价<成本价-1ATR，加仓200
        if (cost_basis-current_price >= g.atr_dict[security]*g.atr_time and cash>300):
            log.info(security+ g.last_month + ":月定投，买入金额 %.2f" % (1200))
            order_value(security, 1200)
            g.trade_per_month_flag[security] = "Y"

def cal_atr(security):
    h = get_history(g.atr_period+1, '1d', field=['close', 'high', 'low'], security_list=security, fq='dypre', include=True)
    close = h["close"].values
    high = h["high"].values
    low = h["low"].values
    tr_list = [0 for _ in range(len(close)-1)]
    for i in range(1, len(close)):
        tr_list[i - 1] =max((high[i] - low[i]), abs(close[i - 1] - high[i]), abs(close[i - 1] - low[i]))
    g.atr_dict[security] = round(np.nanmean(tr_list), 3 )