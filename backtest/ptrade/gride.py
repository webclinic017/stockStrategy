import numpy as np
import collections


def initialize(context):
    # 初始化此策略
    g.security = ['512480.SS','560880.SS','517090.SS','512880.SS','510310.SS','159952.SZ','512680.SS','513100.SS']
    set_universe(g.security)
    g.path = get_research_path() + "grid_strategy/griddata.txt"
    log.info(g.path)
    g.grid_price_deque_dict = {}
    g.open_dict={}
    for sec in g.security:
        g.open_dict[sec]="N"
        g.grid_price_deque_dict[sec] = collections.deque()
    is_trade_flag = is_trade()
    if is_trade_flag:
        pass
    else:
        set_backtest()
#设置回测条件
def set_backtest():
    set_limit_mode('UNLIMITED')
    set_commission(commission_ratio=0.00005, min_commission =5.0)

def before_trading_start(context, data):
    log.info("当日持仓金额:%s,持仓收益率:%s,持仓收益%s"%(context.portfolio.positions_value,context.portfolio.returns,context.portfolio.pnl))
    g.trade_per_month_flag={}


# 网格及交易
def handle_data(context, data):
    for security in g.security:
        trade(security,context, data)

def trade(security,context, data):
    h = get_history(1, '1m', field=['close', 'volume'], security_list=security, fq='dypre', include=True)
    if len(h['close'].values)>0:
        current_price = h['close'].values[0]
        # current_price=data[security]
        # log.info(current_price)
        position = get_position(security)
        profit_ratio = position.last_sale_price/position.cost_basis-1
        profit_value = profit_ratio*position.cost_basis*position.amount
        open_trading(current_price,security,context,data)
        if position.amount>0:
            buy_per_month(security,current_price,profit_ratio,profit_value,context)
            grid_trade(security,profit_ratio,profit_value,current_price,context)

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
            # order = get_order(order_id)[0]
            # log.info(order)
            log.info(security+":开始建仓，买入金额 %.2f" % (20000))
            g.open_dict[security]='Y'
            grid_price_deque.appendleft(current_price)

def grid_trade(security,profit_ratio,profit_value,current_price,context):
    grid_price_deque = g.grid_price_deque_dict[security]
    cash = context.portfolio.cash
    # 触发买入,第一次触发网格买入或者当前价格<=上一次网格买入价格-网格宽度
    if current_price <= grid_price_deque[0] * 0.95 and cash>300:
        if (profit_ratio < 0):
            grid_trade_buy(current_price,security,4800,grid_price_deque)
        else:
            grid_trade_buy(current_price,security,1800,grid_price_deque)

    # 触发卖出，当前价格>=上一次网格买入价格+网格宽度
    if  current_price >= grid_price_deque[0] * 1.05:
        if profit_ratio < 0:
            grid_trade_buy(current_price,security,-1800,grid_price_deque)
        elif profit_ratio <= 0.2:
            grid_trade_buy(current_price,security,-3600,grid_price_deque)
        else:
            grid_trade_buy(current_price,security,-4800,grid_price_deque)

def grid_trade_buy(current_price,security,amount,grid_price_deque):
    log.info(security + ":触发网格买入:"+str(amount))
    order_id = order_value(security, amount)
    if order_id is not None:
        # order =get_order(order_id)[0]
        # log.info(order)
        if amount>0:
            grid_price_deque.appendleft(current_price)
        if amount<0:
            grid_price_deque.popleft()
            if len(grid_price_deque) == 0:
                grid_price_deque.appendleft(current_price)


# 月定投逻辑
def buy_per_month(security,current_price,profit_ratio,profit_value,context):
    # 得到当天的时间,
    current_date = context.blotter.current_dt
    cash = context.portfolio.cash

    # 如果当天是月初，开始定投
    if g.trade_per_month_flag[security] is None and g.last_month is None or str(current_date)[:-3] > g.last_month:
        g.last_month = str(current_date)[:-3]
        # 现价<成本价-1ATR，加仓200
        # if(self.position.price-self.grid_wide > price):
        if (profit_ratio<-0.05 and cash>300):
            order_value(security, 1200)
            g.trade_per_month_flag[security] = "Y"
