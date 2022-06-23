import re

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

HEADER_PATTERN = re.compile(r"^\s{28}＊＊＊　競走成績　＊＊＊|^\s{28}＊＊＊　番組表　＊＊＊")
RACE_NAME_PATTERN = re.compile(r"\s{10,10}([^\s]+)")
RACE_PLACE_PATTERN = re.compile(r"ボートレース(\D+)\s")
SCHEDULE_PATTERN = re.compile(r"^([1-6])\s(\d{4})(\D+)(\d{2})(\D+)(\d{2})([AB][12])\s+(\d+.\d{2})\s+(\d+.\d{2})\s+(\d+.\d{2})\s+(\d+.\d{2})\s+\d+\s+(\d+.\d{2})\s+\d+\s+(\d+.\d{2})")
RESULT_PATTERN = re.compile(r"\s+0(\d)\s+\d\s+(\d{4})\s+\D+\s\d+\s+\d+\s+(\d+.\d{2})")
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