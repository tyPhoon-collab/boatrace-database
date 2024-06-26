import os.path
from time import sleep
from matplotlib.pyplot import table
import requests
import lhafile
import csv
import pandas as pd
import calendar
import sqlite3

from patterns import *

PLAYER_ID = "選手登番"
RACE_ID = "レースID"
DB_NAME = "boatrace.db"

class Directory:
    SAVE_DIR = "table"
    ODDS_DIR = "odds"
    ENV_DIR = "env"
    LZH_DIR = "lzh"
    TXT_DIR = "txt"
    
    @classmethod
    def makedirs(cls):
        os.makedirs(cls.SAVE_DIR, exist_ok=True)
        os.makedirs(cls.ODDS_DIR, exist_ok=True)
        os.makedirs(cls.ENV_DIR , exist_ok=True)
        os.makedirs(cls.LZH_DIR, exist_ok=True)
        os.makedirs(cls.TXT_DIR, exist_ok=True)
        
class Downloader:
    # http://www1.mbrace.or.jp/od2/K/YYYYMM/kYYMMDD.lzh -> 競艇結果表
    # http://www1.mbrace.or.jp/od2/B/YYYYMM/bYYMMDD.lzh -> 競艇番組表

    """URLに渡される識別文字"""
    RESULT = "K"
    SCHEDULE = "B"

    # ダウンロードする際に使用する公式サイトのURL。取得間隔には注意
    TEMPLATE_URL = "http://www1.mbrace.or.jp/od2/{4}/{0}{2}/{5}{1}{2}{3}.lzh"
    REQUEST_INTERVAL = 3

    @classmethod
    def download_result(cls, date: str, **kwargs):
        return cls.download(date, cls.RESULT, **kwargs)

    @classmethod
    def download_schedule(cls, date: str, **kwargs):
        return cls.download(date, cls.SCHEDULE, **kwargs)

    @classmethod
    def download(cls, date: str, download_type: str, delimiter: str = '-', decompress: bool = False,
                 check_existence: bool = True) -> str or list[str]:
        """
            文字列 YYYY-MM-DD を引数にとることとする
            Windows-31jで保存される
            check_existence: ファイルが存在していたら取得しない
        """

        lzh_filename = f"{download_type}{date}.lzh"
        lzh_path = os.path.join(Directory.LZH_DIR, lzh_filename)

        if check_existence and os.path.exists(lzh_path):
            # print(f"{lzh_filename} すでにダウンロード済みです")
            pass

        else:
            year, month, day = date.split(delimiter)
            url: str = cls.TEMPLATE_URL.format(year, year[2:], month, day, download_type, download_type.lower())
            print(f"{url} を取得しています")
            res: requests.Response = requests.get(url)

            # インターバルを置く
            print(f"{cls.REQUEST_INTERVAL}秒スリープしています")
            sleep(cls.REQUEST_INTERVAL)

            # とりあえず保存しておく。何度もアクセスすると迷惑がかかる
            with open(lzh_path, "wb") as f:
                f.write(res.content)

            print(f"{lzh_filename} を保存しました")

        if decompress:
            return cls.decompress(lzh_path)
        else:
            return lzh_path

    @classmethod
    def decompress(cls, lzh_path: str) -> list[str]:
        f = lhafile.Lhafile(lzh_path)
        
        for info in f.infolist():
            filename = info.filename
            with open(os.path.join(Directory.TXT_DIR, filename), "wb") as tf:
                tf.write(f.read(info.filename))

            # print(f"{filename} を保存しました")

        return [os.path.join(Directory.TXT_DIR, filename) for filename in f.namelist()]


class Parser:
    SCHEDULE_HEADER = [RACE_ID, "艇番", PLAYER_ID, "名前", "年齢", "支部", "体重", "階級", "全国勝率", "全国2率",
                       "当地勝率", "当地2率", "モーター2率","ボート2率"]
    RESULT_HEADER = [RACE_ID, "順位", PLAYER_ID, "展示"]
    ODDS_HEADER = [RACE_ID, "単勝", "複勝1", "複勝2", "2連単", "2連複", "拡連複12", "拡連複13", "拡連複23", "3連単", "3連複"]
    ENV_HEADER = [RACE_ID, "天候", "風向", "風速", "波高", "会場"]

    @classmethod
    def parse_result(cls, file, **kwargs):
        return cls.parse(file, RESULT_PATTERN, header=cls.RESULT_HEADER, **kwargs)

    @classmethod
    def parse_schedule(cls, file, **kwargs):
        return cls.parse(file, SCHEDULE_PATTERN, header=cls.SCHEDULE_HEADER, **kwargs)

    @classmethod
    def parse_odds(cls, file, **kwargs):
        return cls.parse(file, ODDS_PATTERN, header=cls.ODDS_HEADER, odds=True, **kwargs)
    
    @classmethod
    def parse_env(cls, file, **kwargs):
        return cls.parse(file, ENV_PATTERN, header=cls.ENV_HEADER, env=True, **kwargs)

    @classmethod
    def parse(cls, file, pattern: re.Pattern, header: list = None, save_as_csv: bool = True, odds: bool = False, env: bool = False,
              filename: str = None, date: str = None, con=None, table_name=None) -> str or None:
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
                    # かなり強引な取得をしている。
                    # 元データが全角と半角入り乱れているのが悪い。かと言ってどちらかに合わせるわけにもいかないため、ゴリ押しする
                    # ２行下にレース名がある
                    for _ in range(2):
                        line = f.readline()

                    ret = re.match(RACE_NAME_PATTERN, line)
                    race_name = ret.groups()[0]

                    # さらに２行下に会場名がある
                    for _ in range(2):
                        line = f.readline()

                    ret = re.search(RACE_PLACE_PATTERN, line)
                    race_place = ret.groups()[0]

                    race_num = 0

                if re.search(r"H\d+m|Ｈ[^ｍ]+ｍ", line):
                    # レースのラウンドを更新。
                    race_num += 1

                if ret := re.search(pattern, line):
                    race_id: str = f"{date}{race_place}{race_name}{race_num}R"
                    row = []

                    if odds:
                        # 5人が違反するとレース不成立となる。
                        if "レース不成立" in line:
                            print(race_id, "不成立のレースを検知")
                            row = [-1] * len(ODDS_PATTERNS)

                        else:
                            for kind, _pattern in zip(cls.ODDS_HEADER[1:], ODDS_PATTERNS):
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

                    elif env:
                        row = list(ret.groups())
                        row.append(race_place)
                        
                    else:
                        # 間に挟まっている全角スペースを置換するかどうか
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

            filename = write(filename, rows, header, con, table_name)
    
            if filename:
                print(f"{filename} を保存しました")
    
            return filename

        else:
            for row in rows:
                print(row)


def write(filename: str, rows: list[list], header: list, con=None, table_name=None) -> str or None:
    if con:
        df = pd.DataFrame(rows, columns=header)
        df.to_sql(table_name, con, None, 'append', index=False)
        return

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

def make_boatrace_data(date: str, only_result: bool = True, con: str=None) -> None:
    """
    date format :str -> YYYY-MM-DD
    """
    Directory.makedirs()

    r_files: list[str] = Downloader.download_result(date, decompress=True)
    s_files: list[str] = Downloader.download_schedule(date, decompress=True)
    
    for r_file in r_files:
        Parser.parse_result(r_file, filename=os.path.join(Directory.SAVE_DIR, f"{date}.csv"), date=date, con=con, table_name="result")
        Parser.parse_env(r_file, filename=os.path.join(Directory.ENV_DIR, f"{date}.csv"), date=date, con=con, table_name="env") 
        Parser.parse_odds(r_file, filename=os.path.join(Directory.ODDS_DIR, f"{date}.csv"), date=date, con=con, table_name="odds")
        
    for s_file in s_files:
        Parser.parse_schedule(s_file, filename=os.path.join(Directory.SAVE_DIR, f"{date}.csv"), date=date, con=con, table_name="schedule")
        
    if con:
        env = pd.read_sql("SELECT * FROM env", con)
        result = pd.read_sql("SELECT * FROM result", con)
        schedule = pd.read_sql("SELECT * FROM schedule", con)

        race = pd.merge(pd.merge(env, result, on=[RACE_ID]), schedule, on=[RACE_ID, PLAYER_ID])
        race.to_sql("race", con, None, 'append', index=False)
            
    # if only_result:
    #     for file in r_files + s_files:
    #         os.remove(file)


def make_months_boatrace_data(year: int, *months, **kwargs):
    for month in months:
        days: int = calendar.monthrange(year, month)[1]
        for day in range(1, days + 1):
            date: str = f"{year}-{month:02}-{day:02}"
            make_boatrace_data(date, **kwargs)

def make_years_boartrace_data(*years, **kwargs):
    for year in years:
        make_months_boatrace_data(year, *range(1, 12+1), **kwargs)

if __name__ == '__main__':
    # 毎回初期化する。この程度のデータ量ならば、一括削除してしまうのが楽
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
    # 以下で接続。今回はpandasのto_sqlを使用してデータベースに登録
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    
    # make_boatrace_data("2020-08-14", con=con)
    # make_boatrace_data("2020-09-15", only_result=False)
    # make_boatrace_data("2020-09-16", only_result=False)
    # make_boatrace_data("2020-09-17", only_result=False)
    # parse_odds("K200906.TXT")
    make_months_boatrace_data(2020, 8, con=con)
    # make_months_boatrace_data(2020, 1,2,3,4,5,6,7,8,9,10,11,12, con=con)
    # make_years_boartrace_data(2020, 2021, con=con)
    
    con.commit()
    con.close()

