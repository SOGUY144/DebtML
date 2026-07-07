#!/usr/bin/env python
# coding: utf-8

# In[41]:


import pandas as pd
import numpy as np
df_debt = pd.read_excel("20230521160827_42424.xlsx", skiprows=2)#skip first 2 header rows
#Rename columns (so it's easier to work with)  
df_debt.columns = [
    'Region', 'Province', 'Purpose', 
    'Debt_2547', 'Debt_2549', 'Debt_2550', 'Debt_2552', 'Debt_2554', 
    'Debt_2556', 'Debt_2558', 'Debt_2560', 'Debt_2562', 'Debt_2564', 'Debt_2566'
]
#Forward fill merged cell DON'T DROP
df_debt[['Province', 'Region']] = df_debt[['Province', 'Region']].ffill()
#Drop 2last rows
df_debt = df_debt.drop(df_debt.index[-2:])

#Replace - with 0
df_debt = df_debt.replace('-', 0)
#combine bangkok and vicinity provinces {ใช้ .isin() ในการเปลี่ยนชื่อ Region ของทุกจังหวัดในลิสต์ให้เป็นกลุ่มเดียวกัน}
vicinity_provinces = ['กรุงเทพมหานคร', 'นนทบุรี', 'ปทุมธานี', 'สมุทรปราการ', 'นครปฐม', 'สมุทรสาคร']
df_debt.loc[df_debt['Province'].isin(vicinity_provinces), 'Region'] = 'กรุงเทพมหานครและปริมณฑล'

df_debt_summary = df_debt[df_debt['Purpose'] == 'หนี้สินทั้งสิ้น'].copy()
#Wrangling income
df_income = pd.read_excel("20230521160113_19514.xlsx", skiprows=2) #skip first 2 header rows
df_income = df_income.drop(columns=[df_income.columns[0]]) #drop first column
df_income.columns = [
    'Region', 'Province',
    'Income_2547', 'Income_2549', 'Income_2550', 'Income_2552', 'Income_2554',
    'Income_2556', 'Income_2558', 'Income_2560', 'Income_2562', 'Income_2564', 'Income_2566'
]
df_income[['Region']] = df_income[['Region']].ffill()
#Vicinity provinces for income data
bkk_vicinity = ['กรุงเทพมหานคร', 'นนทบุรี', 'ปทุมธานี', 'สมุทรปราการ', 'นครปฐม', 'สมุทรสาคร']
df_income.loc[df_income['Province'].isin(bkk_vicinity), 'Region'] = 'กรุงเทพมหานครและปริมณฑล'
#drop last row
df_income = df_income.drop(df_income.index[-1:])
#Fill missing values with 0
df_income = df_income.fillna(0)
#clean index
df_income_sorted = df_income.sort_values(by=['Region', 'Province']).reset_index(drop=True)

#remove subtotal rows
df_income_clean = df_income_sorted[df_income_sorted['Region'] != df_income_sorted['Province']].copy()


# In[42]:


# ============================================================
# DAY 1 : Label Definition + Feature Engineering
# ใช้ต่อจาก cell ที่คุณมีอยู่แล้ว: df_debt_summary, df_income_clean
# ============================================================


# ------------------------------------------------------------
# STEP 0 : เตรียมข้อมูลตั้งต้น (รวม Debt summary + Income)
# ------------------------------------------------------------
# df_debt_summary  -> มีแค่แถว "หนี้สินทั้งสิ้น" ต่อจังหวัด (ตามที่คุณเลือกแล้ว)
# df_income_clean  -> รายได้เฉลี่ยต่อจังหวัด

df_debt_summary = df_debt_summary.drop(columns=['Purpose'])
df_merged = pd.merge(
    df_income_clean,
    df_debt_summary,
    on=['Province', 'Region']
)

# wide -> long แบบเดียวกับที่คุณทำใน notebook เดิม (pd.wide_to_long)
df_panel = pd.wide_to_long(
    df_merged,
    stubnames=['Income', 'Debt'],
    i=['Region', 'Province'],
    j='Year',
    sep='_'
).reset_index()

# Year ในข้อมูลเป็น พ.ศ. แบบ string/ปนกัน -> แปลงเป็น int ให้แน่ใจ
df_panel['Year'] = df_panel['Year'].astype(int)
df_panel = df_panel.sort_values(['Province', 'Year']).reset_index(drop=True)


# ------------------------------------------------------------
# STEP 1 : คำนวณ DTI (ของปีนั้นๆ) -> ใช้สร้าง LABEL เท่านั้น
# ------------------------------------------------------------
# Annual_Income = รายได้เฉลี่ยต่อเดือน x 12
df_panel['Annual_Income'] = df_panel['Income'] * 12
df_panel['DTI'] = df_panel['Debt'] / df_panel['Annual_Income'].replace(0, np.nan)
df_panel['DTI'] = df_panel['DTI'].fillna(0)

# --- ตั้ง Threshold ---
# DTI > 1.0 หมายถึง หนี้สินเฉลี่ยเกินรายได้ทั้งปี (ใช้ตรงกับ benchmark
# ที่อ้างถึงในงานวิจัยที่ใช้ฐานข้อมูล NSO เดียวกัน และตรงกับกราฟ
# Top-10 ที่คุณทำไว้แล้วในโน้ตบุ๊กเดิม)
DTI_THRESHOLD = 1.0

df_panel['Label'] = (df_panel['DTI'] > DTI_THRESHOLD).astype(int)
# Label = 1 -> High-Risk Distress
# Label = 0 -> Stable

print("สัดส่วน Label ทั้งหมด:")
print(df_panel['Label'].value_counts(normalize=True))
# ดูตรงนี้ก่อน! ถ้า Label=1 มีสัดส่วนน้อยมาก (เช่น <10%) ยืนยันว่า
# เป็น imbalanced classification ตามที่ระบุไว้ใน proposal
# (ต้องใช้ Precision/Recall วัดผล ไม่ใช่ Accuracy เฉยๆ)


# ------------------------------------------------------------
# STEP 2 : สร้าง FEATURE แบบ Leakage-Safe
# ------------------------------------------------------------
# กฎเหล็ก: ห้ามใช้ Debt, Income, DTI ของ "ปีปัจจุบัน" เป็น feature
# เพราะ Label คำนวณมาจากค่าพวกนี้ตรงๆ (= Label leakage)
# สิ่งที่ "ใช้ได้" คือค่าของ "ปีก่อนหน้า" (lag) เพราะเป็นข้อมูลที่
# มีอยู่จริงก่อนจะรู้ผลของปีปัจจุบัน

def add_gap_and_lag(group):
    """ทำงานทีละจังหวัด (group by Province) เรียงตามปีแล้ว shift หาค่า lag"""
    group = group.sort_values('Year').copy()

    group['Year_prev'] = group['Year'].shift(1)
    group['gap'] = group['Year'] - group['Year_prev']  # ช่วงห่างปีไม่เท่ากัน!

    group['Debt_lag'] = group['Debt'].shift(1)
    group['Income_lag'] = group['Income'].shift(1)
    group['DTI_lag'] = group['DTI'].shift(1)

    return group

def annualized_growth(curr, prev, gap):
    with np.errstate(invalid='ignore', divide='ignore', over='ignore'):
        g = (curr / prev) ** (1 / gap) - 1
    return g

def add_gap_lag_and_growth(group):
    group = group.sort_values('Year').copy()

    group['Year_prev'] = group['Year'].shift(1)
    group['gap'] = group['Year'] - group['Year_prev']

    group['Debt_lag'] = group['Debt'].shift(1)
    group['Income_lag'] = group['Income'].shift(1)
    group['DTI_lag'] = group['DTI'].shift(1)

    growth_gap = group['gap'].shift(1)

    group['Debt_growth_ann'] = annualized_growth(
        group['Debt_lag'],
        group['Debt_lag'].shift(1),
        growth_gap
    )

    group['Income_growth_ann'] = annualized_growth(
        group['Income_lag'],
        group['Income_lag'].shift(1),
        growth_gap
    )

    return group

df_panel = df_panel.groupby('Province', group_keys=False).apply(add_gap_lag_and_growth)
# --- Region encoding ---
df_panel = pd.get_dummies(df_panel, columns=['Region'], prefix='Region')


# ------------------------------------------------------------
# STEP 3 : ตัด Feature ที่ "ห้ามใช้" ออก + ตัดแถวที่ไม่มี lag (ปีแรกของแต่ละจังหวัด)
# ------------------------------------------------------------
LEAKY_COLS = ['Debt', 'Income', 'Annual_Income', 'DTI']  # ของปีปัจจุบัน ห้ามใช้เป็น X

feature_cols = [c for c in df_panel.columns
                 if c not in LEAKY_COLS + ['Label', 'Province', 'Year',
                                            'Year_prev', 'gap']]

df_model = (
    df_panel
    .replace([np.inf, -np.inf], np.nan)
    .dropna(subset=feature_cols)
    .copy()
)

print("\nFeature columns ที่จะใช้เทรนโมเดล:")
print(feature_cols)


# ------------------------------------------------------------
# STEP 4 : Train/Test Split แบบ Out-of-Time
# ------------------------------------------------------------
TEST_YEAR = 2566  # ปีล่าสุด -> เทส, ปีก่อนหน้าทั้งหมด -> เทรน

train_df = df_model[df_model['Year'] < TEST_YEAR]
test_df = df_model[df_model['Year'] == TEST_YEAR]

X_train, y_train = train_df[feature_cols].astype(float), train_df['Label']
X_test, y_test = test_df[feature_cols].astype(float), test_df['Label']

print(f"\nTrain shape: {X_train.shape}, Test shape: {X_test.shape}")
print("Train Label distribution:\n", y_train.value_counts(normalize=True))
print("Test Label distribution:\n", y_test.value_counts(normalize=True))


# In[43]:


df_merged.head(30)


# In[44]:


df_panel.head(30)


# In[45]:


# get_ipython().run_line_magic('pip', 'install statsmodels')
# get_ipython().run_line_magic('pip', 'install scikit-learn')
# get_ipython().run_line_magic('pip', 'install lightgbm')


# In[46]:


# ============================================================
# SCALING : เพิ่ม cell นี้ระหว่าง Day 1 และ Day 2
# ใส่หลัง cell Day 1 ที่สร้าง X_train, X_test เสร็จแล้ว
# ใส่ก่อน cell Day 2 ที่เทรนโมเดล
# ============================================================

from sklearn.preprocessing import StandardScaler

# StandardScaler ทำงานยังไง:
# แปลงทุก feature ให้มี mean=0, std=1
# สูตร: x_scaled = (x - mean) / std
# ผลคือทุก feature อยู่ใน scale เดียวกัน
# Debt_lag (หลักแสน) และ DTI_lag (0-2) จะอยู่ scale เดียวกัน

scaler = StandardScaler()

# fit เฉพาะ train เท่านั้น ห้าม fit กับ test
# เหตุผล: ถ้า fit กับ test = โมเดลรู้ข้อมูลอนาคต = leakage
# .fit_transform() = fit แล้ว transform ในขั้นตอนเดียว
X_train_scaled = scaler.fit_transform(X_train)

# test ใช้แค่ .transform() (ไม่ fit ใหม่)
# ใช้ mean/std จาก train มา scale test เท่านั้น
X_test_scaled = scaler.transform(X_test)

# แปลงกลับเป็น DataFrame เพื่อให้ชื่อ column ไม่หาย
# (numpy array ไม่มีชื่อ column ถ้าไม่แปลงกลับ statsmodels จะ error)
X_train_scaled = pd.DataFrame(
    X_train_scaled,
    columns=X_train.columns,
    index=X_train.index
)
X_test_scaled = pd.DataFrame(
    X_test_scaled,
    columns=X_test.columns,
    index=X_test.index
)

print("Scaling เสร็จแล้ว")
print(f"X_train_scaled shape: {X_train_scaled.shape}")
print(f"X_test_scaled shape: {X_test_scaled.shape}")
print("\nตัวอย่างค่าหลัง scale (ควรอยู่ใกล้ๆ 0 ทั้งหมด):")
print(X_train_scaled.describe().loc[['mean', 'std']].round(2))


# In[47]:


# ============================================================
# DAY 2 : Baseline Modeling
# ใช้ต่อจาก Day 1: X_train, y_train, X_test, y_test, train_df, feature_cols
# ============================================================

import statsmodels.api as sm
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
import lightgbm as lgb
import pandas as pd

# ------------------------------------------------------------
# MODEL 1A : Logistic Regression ด้วย statsmodels
# -> เป้าหมาย: ดู coefficient + p-value (นัยสำคัญทางสถิติ)
# ------------------------------------------------------------
# add_constant = เพิ่มคอลัมน์ intercept (beta_0) ให้สูตร
# ln(p/(1-p)) = b0 + b1*x1 + ... ครบตามทฤษฎี
X_train_sm = sm.add_constant(X_train)

# หมายเหตุ: บาง column เป็น bool (จาก get_dummies ตอน Day 1)
# ต้องแปลงเป็น float ก่อน ไม่งั้น statsmodels error

# ใช้ scaled data + add intercept
X_train_sm = sm.add_constant(X_train_scaled)

# แปลงเป็น float
X_train_sm = X_train_sm.astype(float)

# ใช้ X_train_sm ตรงนี้ ไม่ใช่ X_train_scaled
logit_model = sm.Logit(y_train, X_train_sm)

logit_result = logit_model.fit(
    method='lbfgs',
    maxiter=1000
)
print("=" * 60)
print("Logistic Regression (statsmodels) -- ใช้ดู coefficient/p-value")
print("=" * 60)
print(logit_result.summary())

# ตัวแปรไหน p-value < 0.05 ถือว่ามีนัยสำคัญทางสถิติ
# ดูคอลัมน์ P>|z| ใน summary ด้านบน


# ------------------------------------------------------------
# MODEL 1B : Logistic Regression ด้วย sklearn
# -> เป้าหมาย: ได้โมเดลที่ใช้ .predict_proba() จริงสำหรับ Streamlit
# ------------------------------------------------------------
# class_weight='balanced' -> แก้ปัญหา imbalanced data
# (กลุ่ม High-Risk มีสัดส่วนน้อยกว่า Stable มาก ตามที่เห็นใน Day 1)
# วิธีทำงาน: ให้น้ำหนัก error ของกลุ่มเล็กมากกว่ากลุ่มใหญ่ตามสัดส่วนผกผัน
log_reg_sklearn = LogisticRegression(
    class_weight='balanced',
    max_iter=1000,
    random_state=42
)
log_reg_sklearn.fit(X_train_scaled, y_train)

print("\nsklearn Logistic Regression -- เทรนเสร็จแล้ว (ใช้สำหรับ deploy)")


# ------------------------------------------------------------
# MODEL 2 : Random Forest
# -> เป้าหมาย: จัดการ non-linear relationship ที่ Logistic จับไม่ได้
# ------------------------------------------------------------
rf_model = RandomForestClassifier(
    n_estimators=300,      # จำนวนต้นไม้ ยิ่งเยอะยิ่งเสถียร แต่ช้าขึ้น
    max_depth=5,           # จำกัดความลึก กัน overfit (ข้อมูลมีแค่ ~700 แถว)
    class_weight='balanced',
    random_state=42
)
rf_model.fit(X_train, y_train)

print("Random Forest -- เทรนเสร็จแล้ว")


# ------------------------------------------------------------
# MODEL 3 : LightGBM
# -> เป้าหมาย: ลอง gradient boosting เทียบกับ RF
# ------------------------------------------------------------
# is_unbalance=True คือ class_weight='balanced' เวอร์ชันของ LightGBM
lgb_model = lgb.LGBMClassifier(
    n_estimators=300,
    max_depth=5,
    learning_rate=0.05,
    is_unbalance=True,
    random_state=42,
    verbose=-1             # ปิด log รก ๆ ตอนเทรน
)
lgb_model.fit(X_train, y_train)

print("LightGBM -- เทรนเสร็จแล้ว")


# ------------------------------------------------------------
# STEP สุดท้าย : เก็บโมเดลทั้งหมดไว้ใน dict เดียว
# -> สะดวกตอนเอาไปวน loop ประเมินผลใน Day 3
# ------------------------------------------------------------
trained_models = {
    'Logistic Regression': log_reg_sklearn,
    'Random Forest': rf_model,
    'LightGBM': lgb_model,
}

print("\nสรุป: เทรนครบ 3 โมเดล พร้อมไป Evaluation แล้ว")
print(list(trained_models.keys()))

