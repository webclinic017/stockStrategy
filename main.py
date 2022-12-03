# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
from backtest.backtest_service import back_test_service
from backtest.stock import Stock

if __name__ == '__main__':
    # stock = Stock('沪深300','sh510310','市盈率')
    # stock = Stock('创业板指', 'sz159915', '市盈率')
    # stock = Stock('国防军工(申万)', 'sh512710', '市净率')
    # stock = Stock('证券公司', 'sh512880', '市净率')
    # stock = Stock('有色金属(申万)', 'sh512400', '市净率')
    # stock = Stock('食品饮料(申万)', 'sz159928', '市盈率')
    # stock = Stock('中证银行', 'sh512820', '市盈率')
    # stock = Stock('中证红利', 'sh515180', '市盈率')
    stock = Stock('全指医药', 'sz159938', '市盈率')




    back_test_service(stock)








