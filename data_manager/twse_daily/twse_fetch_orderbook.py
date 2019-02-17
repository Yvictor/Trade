import os
import time
import datetime as dt
import requests
import pandas as pd
import tqdm

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36"}
DATASET_PATH = os.environ.get('DATASET_PATH', 'data/msgpack')
DATASET_NAME = os.environ.get('DATASET_NAME', 'twse_orderbook.msgpack')
DATASET = os.path.join(DATASET_PATH, DATASET_NAME)

def twse_store_orderbook():
    if os.path.exists(DATASET):
        df = pd.read_msgpack(DATASET)
        df_first = df[df['時間'].map(lambda x: x.time())==dt.time(9,0,0)]
        already_fetch_date = list(df_first['時間'].map(lambda x: x.date()))
    else:
        df = pd.DataFrame()
        already_fetch_date = [dt.date(2000,1,1)]

    df_list = []
    for i in tqdm.tqdm(range(5000)):
        date_index = dt.date.today() + dt.timedelta(days=-i)
        if date_index not in already_fetch_date and date_index >= max(already_fetch_date):#dt.isoweekday()<6:
            url = f'http://www.tse.com.tw/exchangeReport/MI_5MINS?response=json&date={dt.date.strftime(date_index,"%Y%m%d")}'
            res = requests.get(url, headers=HEADERS)
            time.sleep(3)
            try:
                data = res.json()
            except:
                time.sleep(12)
                res = requests.get(url, headers=HEADERS)
                try:
                    data = res.json()
                except:
                    print(f'error: {i}')
            if data['stat'] == 'OK':
                df_single = pd.DataFrame(data['data'], columns=data['fields'])
                df_single['時間'] = df_single['時間'].map(lambda x: dt.datetime.combine(date_index, dt.time(*[int(i) for i in x.split(':')])))
                df_list.append(df_single)
            elif data['stat'] == '查詢日期小於93年10月15日，請重新查詢!':
                print('done')
                break
            elif data['stat'] == '很抱歉，沒有符合條件的資料!':
                print(f'{date_index} data not exist.')
            else:
                print(data)
                break
        else:
            print('Data exist.')
            break

    if df_list:
        df_new = pd.concat(df_list)
        for col in df_new.columns[1:]:
            df_new[col] = df_new[col].map(lambda x: int(('').join(x.split(','))))
        df = pd.concat([df_new, df]).sort_values('時間')
        df.to_msgpack(DATASET, compress='zlib')
        print('saved orderbook.')
