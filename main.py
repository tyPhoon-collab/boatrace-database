import os.path
from time import sleep

import requests
import lhafile
import re
import csv
import pandas as pd
import calendar

# http://www1.mbrace.or.jp/od2/K/YYYYMM/kYYMMDD.lzh
# http://www1.mbrace.or.jp/od2/B/YYYYMM/bYYMMDD.lzh

# ダウンロードする際に使用する公式サイトのURL。取得間隔には注意
TEMPLATE_URL = "http://www1.mbrace.or.jp/od2/{4}/{0}{2}/{5}{1}{2}{3}.lzh"
REQUEST_INTERVAL = 3

# サブグループとして設定し、groupsにより、要素をタプルで取得予定
# カッコ内部に一致したものを取得できる
# ex) 1 4041小林基樹41山口55B1 4.40 22.79 5.04 30.43 44 30.77 55 15.69 6 56
# 補足:  {m} -> m字以上
#       体重は必ず2桁
#       少数の有効数字は２桁
#       選手登番をキーとして結合できるようにする
#       会場や風、波は一旦考慮しない
#       回帰などを行う際に、レースタイムなどを使いたいが、一旦考慮しない

#       先頭にレースIDを追加することとする。ex) ＢＴＳ松浦開設記念1
#       中止になったりするため、レースIDと選手登番をキーとして結果と結合する

#       かなり強引だが、HEADERとしてHEADER_PATTERNを探し、その２行下の文字列をレース名とする

#       オッズの取得もかなり強引。もとの形式がTXTで複雑。不成立、特払い、複勝なし、などの場合もある
#       取得できなかったら-1とする

#       同率を考慮していない

PLAYER_ID = "選手登番"
RACE_ID = "レースID"

HEADER_PATTERN = re.compile(r"^\s{28}＊＊＊　競走成績　＊＊＊|^\s{28}＊＊＊　番組表　＊＊＊")
RACE_PATTERN = re.compile(r"\s{10,10}([^\s]+)")

SCHEDULE_HEADER = [RACE_ID, "艇番", PLAYER_ID, "名前", "年齢", "支部", "体重", "階級", "全国勝率", "全国2率", "当地勝率", "当地2率", "モーター2率", "ボート2率"]
SCHEDULE_PATTERN = re.compile(r"^([1-6])\s(\d{4})(\D+)(\d{2})(\D+)(\d{2})([AB][12])\s+(\d+.\d{2})\s+(\d+.\d{2})\s+(\d+.\d{2})\s+(\d+.\d{2})\s+\d+\s+(\d+.\d{2})\s+\d+\s+(\d+.\d{2})")

RESULT_HEADER = [RACE_ID, "順位", PLAYER_ID, "展示"]
RESULT_PATTERN = re.compile(r"\s+0(\d)\s+\d\s+(\d{4})\s+\D+\s\d+\s+\d+\s+(\d+.\d{2})")

ODDS_HEADER = [RACE_ID, "単勝", "複勝1", "複勝2", "2連単", "2連複", "拡連複12", "拡連複13", "拡連複23", "3連単", "3連複"]
ODDS_PATTERNS = (
    re.compile(r"\s+単勝\s+\d\s+(\d+)"), 
    re.compile(r"\s+複勝\s+\d\s+(\d+)"),
    re.compile(r"\s+複勝\s+\d\s+\d+\s+\d\s+(\d+)"),
    re.compile(r"\s+２連単\s+\d-\d\s+(\d+)"),
    re.compile(r"\s+２連複\s+\d-\d\s+(\d+)"),
    re.compile(r"\s+拡連複\s+\d-\d\s+(\d+)"),
    re.compile(r"\s+\d-\d\s+(\d+)"),
    re.compile(r"\s+\d-\d\s+(\d+)"),
    re.compile(r"\s+３連単\s+\d-\d-\d\s+(\d+)"),
    re.compile(r"\s+３連複\s+\d-\d-\d\s+(\d+)\s+人気\s+\d+")
)

class Directory:
    SAVE_DIR = "table"
    ODDS_DIR = "odds"

class DownloadType:
    """URLに渡される識別文字"""
    RESULT = "K"
    SCHEDULE = "B"


def download_result(date: str, **kwargs):
    return download(date, DownloadType.RESULT, **kwargs)


def download_schedule(date: str, **kwargs):
    return download(date, DownloadType.SCHEDULE, **kwargs)


def download(date: str, download_type: str, delimiter: str = '-', decompress: bool = False,
             check_existence: bool = True) -> str or list[str]:
    """
        文字列 YYYY-MM-DD を引数にとることとする
        Windows-31jで保存される
        check_existence: ファイルが存在していたら取得しない
    """

    lzh_filename = f"{download_type}{date}.lzh"

    if check_existence and os.path.exists(lzh_filename):
        print(f"{lzh_filename} すでにダウンロード済みです")

    else:
        year, month, day = date.split(delimiter)
        url: str = TEMPLATE_URL.format(year, year[2:], month, day, download_type, download_type.lower())
        print(f"{url} を取得しています")
        res: requests.Response = requests.get(url)

        # インターバルを置く
        print(f"{REQUEST_INTERVAL}秒スリープしています")
        sleep(REQUEST_INTERVAL)

        # とりあえず保存しておく。何度もアクセスすると迷惑がかかる
        with open(lzh_filename, "wb") as f:
            f.write(res.content)

        print(f"{lzh_filename} を保存しました")

    if decompress:
        f = lhafile.Lhafile(lzh_filename)

        for info in f.infolist():
            filename = info.filename
            with open(filename, "wb") as tf:
                tf.write(f.read(info.filename))

            print(f"{filename} を保存しました")

        return f.namelist()
    else:
        return lzh_filename


def parse_result(file, **kwargs):
    return parse(file, RESULT_PATTERN, header=RESULT_HEADER, **kwargs)


def parse_schedule(file, **kwargs):
    return parse(file, SCHEDULE_PATTERN, header=SCHEDULE_HEADER, **kwargs)


def parse_odds(file, **kwargs):
    return parse(file, r"\s+単勝", header=ODDS_HEADER, odds=True, **kwargs)
    

def parse(file, pattern: re.Pattern, header: list = None, save_as_csv: bool = True, odds: bool = False, filename: str = None) -> str or None:
    """
    save_as_csv: Falseならプレビューだけする
    """
    rows: list[list] = []
    race_name = None
    race_num = 0

    # 重い while + if + append でやや遅い
    with open(file, "r", encoding="cp932") as f:
        while line := f.readline():
            if re.match(HEADER_PATTERN, line):
                for _ in range(2):
                    line = f.readline()

                ret = re.match(RACE_PATTERN, line)
                race_name = ret.groups()[0]
                race_num = 0

            if re.search(r"H1800m|Ｈ１８００ｍ", line):
                # レースのラウンドを更新。
                race_num += 1
                
            if ret := re.match(pattern, line):
                race_id: str = race_name + str(race_num)
                row = []
                
                if odds:
                    for kind, _pattern in zip(ODDS_HEADER[1:], ODDS_PATTERNS):
                        ret = re.match(_pattern, line)
                        
                        if ret:
                            row.append(ret.groups()[0])
                        else:            
                            print(race_id, kind, "オッズの検知に失敗")
                            row.append(-1)
    
                        # 基本的には１行に１つの情報が取得できるが、複勝だけは横並び。
                        # 処理の都合上、少し強引だが、以下のようにする                    
                        if kind != "複勝1":
                            line = f.readline()
                        
                else:
                    # 全角スペースを置換するかどうか
                    # line = line.replace("\u3000", "")
                    row = list(ret.groups())

                # レースIDを先頭に追加
                row.insert(0, race_id)
                rows.append(row)

    if save_as_csv:
        if filename is None:
            # フォーマットに従っていれば、以下で正常にファイル名が指定される
            filename: str = file.replace(".TXT", ".CSV")
            
            # オッズの取得ならば、K→Oに変換。強引なので後でリファクタリングするかも
            if odds:
                filename = filename.replace("K", "O")
            
        filename = write_csv(filename, rows, header)
        print(f"{filename} を保存しました")
        return filename
    
    else:
        for row in rows:
            print(row)
            

def write_csv(filename: str, rows: list[list], header: list) -> str:
    # 従っていない場合は以下で対応
    if not filename.upper().endswith(".CSV"):
        filename += ".csv"

    # 2次元データをwriterowsによって書き込み、CSVとする
    with open(filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if header:
            writer.writerow(header)
        writer.writerows(rows)

    return filename


def merge(left_file, right_file, filename: str, on=None) -> str:
    # pdでmergeする。
    if on is None:
        on = [PLAYER_ID, RACE_ID]

    left = pd.read_csv(left_file)
    right = pd.read_csv(right_file)
    pd.merge(left, right, on=on).to_csv(filename)
    print(f"{filename} マージしました")

    return filename


def make_boatrace_csv(date: str, filename: str = None, with_odds: bool = True, only_result: bool = True):
    os.makedirs(Directory.SAVE_DIR, exist_ok=True)
    
    r_files: list[str] = download_result(date, decompress=True)
    s_files: list[str] = download_schedule(date, decompress=True)

    r_csv_files = [parse_result(file) for file in r_files]
    s_csv_files = [parse_schedule(file) for file in s_files]

    for r_file, s_file in zip(r_csv_files, s_csv_files):
        merge(r_file, s_file, filename=filename if filename else os.path.join(Directory.SAVE_DIR, f"{date}.csv"))
        
    if with_odds:
        os.makedirs(Directory.ODDS_DIR, exist_ok=True)
        for r_file in r_files:
            parse_odds(r_file, filename=os.path.join(Directory.ODDS_DIR, f"{date}.csv"))

    if only_result:
        for file in r_files + s_files + r_csv_files + s_csv_files:
            os.remove(file)


def make_month_boatrace_csv(year:int, month:int, **kwargs):
    days:int = calendar.monthrange(year, month)[1]
    for day in range(1, days + 1):
        date:str = f"{year}-{month:02}-{day:02}"
        make_boatrace_csv(date, **kwargs)

if __name__ == '__main__':
    # make_boatrace_csv("2020-09-15", only_result=False)
    # parse_odds("K200906.TXT")
    make_month_boatrace_csv(2020, 9)
    