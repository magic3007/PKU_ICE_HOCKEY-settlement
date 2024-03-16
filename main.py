#!/usr/bin/env python
# -*- coding:utf-8 -*-
# %%
import numpy as np
import pandas as pd
import argparse

# %%
levels = [0.85, 0.90, 0.95, 0.98, 1]

# %%
parser = argparse.ArgumentParser(description="Settlement for PKU ICE HOCKEY")
parser.add_argument("-i", type=str, help="input csv file", default="example.csv")
parser.add_argument("-o", type=str, help="output csv file", default="example.out.csv")
parser.add_argument("-e", type=int, help="estimated ice fee", default=1500)
args = parser.parse_args()
input_file = args.i
output_file = args.o
ESTIMATED_ICE_FEE = args.e

# input_file = "example.csv"
# output_file = "example.out.csv"

if not input_file.endswith(".csv"):
    raise ValueError("input file must be a csv file")

if not output_file.endswith(".csv"):
    raise ValueError("output file must be a csv file")
# %%
df = pd.read_csv(input_file)
df = df.dropna(how="all")
df = df.dropna(axis=1, how="all")

num_trainees = df["本周期是否全部不参加"].value_counts()["否"]
num_days = sum(df.columns.str.match(r"\d{4}\.\d{1,2}\.\d{1,2}"))
total_fee = (
    df.loc[df["姓名"] == "冰时费"]
    .iloc[:, 2:]
    .apply(lambda x: x.str.extract(r"(\d+)").astype(float).sum().sum(), axis=1)
    .values[0]
)

assert num_days == 8

print("input_file       : ", input_file)
print("output_file      : ", output_file)
print("#trainees        : ", num_trainees)
print("#days            : ", num_days)
print("Estimated fee    : ", ESTIMATED_ICE_FEE * num_days)
print("Total fee        : ", total_fee)

# %%
df["押金"] = 0
df["应付"] = 0
# %%
deposit = 1.0 * ESTIMATED_ICE_FEE * num_days / num_trainees

for idx, line in df.iterrows():
    if line["本周期是否全部不参加"] == "是":
        df.loc[idx, "押金"] = 0
    elif line["是否是试训队员"] == "是":
        df.loc[idx, "押金"] = 0
    elif line["姓名"] == "冰时费":
        df.loc[idx, "押金"] = 0
    else:
        df.loc[idx, "押金"] = deposit

# %%
weights = np.zeros(len(df))
trial_trainee_fee = 0
for idx, line in df.iterrows():
    if line["本周期是否全部不参加"] == "是" or line["姓名"] == "冰时费":
        continue
    # 分别统计行内 出勤，临时出勤，请假 / 病假，临时请假，未出勤未请假
    c0 = line.str.match(r"出勤").sum()
    c1 = line.str.match(r"临时出勤").sum()
    c2 = line.str.match(r"请假").sum() + line.str.match(r"病假").sum()
    c3 = line.str.match(r"临时请假").sum()  # 不按时请假也属于不请假
    c4 = line.str.match(r"未出勤未请假").sum()  # 不请假相应的训练场次也对其收费
    assert c0 + c1 + c2 + c3 + c4 == num_days
    num_count = c0 + c1 + c3 + c4
    if line["是否是试训队员"] == "是":
        df.loc[idx, "应付"] = num_count * 90
        trial_trainee_fee += num_count * 90
        continue
    l = min(8 - num_count, 4)
    if c1 > 2:
        # 请假但出勤次数>2, 每多一次，提升一个level
        l = min(l + (c1 - 2), 4)
    # 临时请假 和 未出勤未请假, 每多一次，提升一个level
    l = min(l + c3 + c4, 4)
    weights[idx] = num_count * levels[l]
# %%

for idx, line in df.iterrows():
    if (
        line["本周期是否全部不参加"] == "是"
        or line["是否是试训队员"] == "是"
        or line["姓名"] == "冰时费"
    ):
        continue
    df.loc[idx, "应付"] = (total_fee - trial_trainee_fee) * weights[idx] / weights.sum()

# %%
df["权重"] = weights
df["结算"] = df["应付"] - df["押金"]

# %%
df.to_csv(output_file, index=False, encoding="utf_8_sig")
