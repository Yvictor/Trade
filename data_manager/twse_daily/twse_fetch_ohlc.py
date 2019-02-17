import os
import time
import datetime as dt
import requests
import pandas as pd
import tqdm

FETCH_PED = int(os.environ.get('FETCH_PED', '10'))
DATASET_PATH = os.environ.get('DATASET_PATH', 'data/msgpack')
DATASET_NAME = os.environ.get('DATASET_NAME', 'twse_ohlc.msgpack')
DATASET = os.path.join(DATASET_PATH, DATASET_NAME)
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36"}

def twse_store_ohlc():
    if os.path.exists(DATASET):
        df = pd.read_msgpack(DATASET)
        already_fetch_date = list(df['日期'].map(lambda x: x.date()))
    else:
        df = pd.DataFrame()
        already_fetch_date = []

    df_list = []
    date_index = dt.date.today()

    for i in tqdm.tqdm(range(FETCH_PED)):
        if date_index not in already_fetch_date:
            url = f'http://www.twse.com.tw/indicesReport/MI_5MINS_HIST?response=json&date={dt.date.strftime(date_index,"%Y%m%d")}'
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
                    print(f'error: {dt}')
            if data['stat'] == 'OK':
                df_single = pd.DataFrame(data['data'], columns=data['fields'])
                df_list.append(df_single)
                date_index = (date_index + dt.timedelta(days=-30)).replace(day=15)
                date_index += dt.timedelta(days=3-date_index.isoweekday())
            elif data['stat'] == '查詢日期小於93年10月15日，請重新查詢!':
                print('done')
                break
            else:
                print(data)
                break
        else:
            print("Data exist.")

    if df_list:
        df_new = pd.concat(df_list)
        df_new['日期'] = pd.to_datetime(df_new['日期'].map(lambda x: dt.date(*[int(n)+1911 if i==0 else int(n) for i, n in enumerate(x.split('/'))])))
        for col in df_new.columns[1:]:
            df_new[col] = df_new[col].map(lambda x: float(('').join(x.split(','))))
        df = pd.concat([df_new, df]).sort_values('日期').drop_duplicates(subset='日期')
        df.to_msgpack(DATASET)
    print('Done.')
