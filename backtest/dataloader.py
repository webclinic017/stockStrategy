import akshare as ak
import pandas as pd
from datetime import datetime


def get_history_index_valuation(code,indicator):
    index_value_hist_funddb_df = ak.index_value_hist_funddb(symbol=code, indicator=indicator)
    index_value_hist_funddb_df.index=pd.to_datetime(index_value_hist_funddb_df.日期)
    # pd.set_option('display.max_rows',None)
    # print(index_value_hist_funddb_df)
    return index_value_hist_funddb_df


class DataLoader(object):

    def __init__(self, symbol, indicator):
        self.index_value_hist_funddb_df = get_history_index_valuation(symbol,indicator)


    def get_by_date(self, date):
        try:
            return self.index_value_hist_funddb_df.loc[date]
        except BaseException as e:
            print('发生了异常：', e)
            return None


if __name__ == '__main__':
    # bt = get_latest_index_valuation('000300.SH')
    # print(bt)
    dtload = DataLoader('创业板指','市盈率')
    print(dtload.get_by_date("2021-10-11"))

@staticmethod
def load_data(code):
    stock_info = ak.fund_etf_hist_sina(symbol=code)
    # print(stock_info)
    stock_info.index = pd.to_datetime(stock_info.date)
    stock_info['openinterest'] = 0
    stock_info = stock_info[['open', 'high', 'low', 'close', 'volume', 'openinterest']]
    return stock_info


def get_latest_index_valuation(code):
    index_valuation = ak.index_value_name_funddb()
    index_valuation.index = index_valuation.指数代码
    return index_valuation.loc[code]
