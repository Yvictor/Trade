import os
import time
import datetime as dt
import requests
import numpy as np
import pandas as pd
import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from . import twse_store_ohlc, twse_store_orderbook

DATASET_PATH = os.environ.get('DATASET_PATH', 'data/msgpack')
WEB_URL = os.environ.get('WEB_URL', 'http://localhost:5000')

def concat_data():
    df_ohlc = pd.read_msgpack(f'{DATASET_PATH}/twse_ohlc.msgpack').rename(columns={'日期':'date', 
                                                                '開盤指數':'open', 
                                                                '最高指數':'high', 
                                                                '最低指數': 'low', 
                                                                '收盤指數': 'close'}).reset_index(drop=True)

    df_ob = pd.read_msgpack(f'{DATASET_PATH}/twse_orderbook.msgpack')

    df_ob_open = df_ob[df_ob['時間'].map(lambda x: x.time()==dt.time(9,0,0))].copy()
    df_ob_close = df_ob[df_ob['時間'].map(lambda x: x.time()==dt.time(13,30,0))].copy()

    df_ob_open['date'] = df_ob_open['時間'].map(lambda x: x.date())#.strftime('%Y%m%d')
    df_ob_open = df_ob_open.rename(columns={'累積委託買進筆數':'order_buy', '累積委託賣出筆數': 'order_sell'})[['date', 'order_buy', 'order_sell']]

    df_ob_close['date'] = df_ob_close['時間'].map(lambda x: x.date())
    df_ob_close = df_ob_close.rename(columns={'累積成交金額':'volume'})[['date', 'volume']]

    df_twse = df_ohlc.set_index('date').join(df_ob_open.set_index('date')).join(df_ob_close.set_index('date')).dropna()
    print('data concat done.')
    return df_twse

def update_server_twse_data(df_twse):
    para = {'format': 'msgpack',
            'fetch_col': 'open,high,low,close,order_buy,order_sell,volume'}
    res = requests.get(f'{WEB_URL}/api/v1/twse', params=para)
    df_fetch = pd.read_msgpack(res.content).dropna()
    exist_dates = df_fetch.index.astype(str)
    update_dates = [d for d in df_twse.index.astype(str) if d not in exist_dates]
    update_datas = dict(Dates=update_dates, 
                        Values=df_twse.loc[[np.datetime64(d) for d in update_dates]].to_dict(orient='records'))
    param = {'token': '50206fe71bb906d5e9d8d9655bdeaaa8cbd01bbabc3a2d59eaf5785fe67e533e'}
    res = requests.post(f'{WEB_URL}/api/v1/twse', params=param, json=update_datas)
    print(res.json())

def dependency_job():
    # parallel but need to limit query fps
    twse_store_ohlc()
    twse_store_orderbook()
    # dependency job
    #update_server_twse_data(concat_data())

if __name__ == '__main__':
    jobstores = {
        'default': MemoryJobStore()
    }
    executors = {
        'default': ThreadPoolExecutor(4),
        'processpool': ProcessPoolExecutor(2)
    }
    scheduler = BlockingScheduler(jobstores=jobstores, executors=executors, timezone=pytz.timezone('Asia/Taipei'))
    
    dependency_job()
    scheduler.add_job(dependency_job, trigger='cron', hour='18', minute='0', id='dependency_job')
    scheduler.start()




