import os
os.environ["OMP_NUM_THREADS"] = "1"
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn.cluster._kmeans")

import pandas as pd
from sqlalchemy import create_engine
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import re
from matplotlib import rcParams
import matplotlib.font_manager as fm

font_path = "C:/Windows/Fonts/msjh.ttc"
my_font = fm.FontProperties(fname=font_path)
rcParams['font.family'] = my_font.get_name()
rcParams['axes.unicode_minus'] = False

# 讀取資料
engine = create_engine("mysql+mysqlconnector://root:123456789@localhost/watsons")
df = pd.read_sql("SELECT * FROM watsons_products", engine)

brand_list = [
    "蘇菲", "KOTEX靠得住", "蕾妮亞", "好自在", "MDMMD", "康乃馨",
    "愛康ICON", "PURE N SOFT", "HIBIS", "ELIS", "OB歐碧", "天心生醫MITENXIN",
    "TRIPLEPROBIO益菌革命", "SOFY", "COMFORT", "EVERYDAYCOMFORT","LAURIER","凱娜"
]
filter_brand = df[df["品牌"].isin(brand_list)].copy()

keywords = r"(?:漏尿|慕絲|暖宮貼|淨白露|潔膚液|慕斯|體貼|噴霧|吸水)"
product = filter_brand[~filter_brand["商品名稱"].str.contains(keywords, case=False, na=False)]
product = product.reset_index(drop=True)
product = product[~product["商品名稱"].str.contains("箱購", case=False, na=False)]

product["是否組合包"] = product["是否組合包"].map({"是": 1, "否": 0})
products = product[["品牌","商品名稱","特價","銷量","是否組合包","類型","長度"]].copy()

def extract_length(row):
    name = row["商品名稱"]
    item_type = row["類型"]
    if pd.notna(item_type) and "褲型" in item_type:
        return 50
    if pd.notna(item_type) and "棉條" in item_type:
        return 0
    if pd.notna(name):
        match = re.search(r"(\d{2,3}(?:\.\d+)?)\s*(?:cm|公分)", name, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    if pd.notna(name) and ("夜用" in name or "量多" in name):
        return 35
    if pd.notna(name) and ("一般" in name or "衛生棉" in name):
        return 23
    if pd.notna(name) and "護墊" in name:
        return 15      
    return row["長度"]

def fill_type(row):
    type_ = row["類型"]
    length = row["補全長度"]  
    if pd.notna(type_):
        return type_ 
    if pd.isna(length):
        return None 
    if length == 0:
        return "棉條"
    elif length >= 50:
        return "褲型"
    elif length <= 20:
        return "護墊"
    elif 20.5 <= length <= 29:
        return "日用"
    elif length >= 30:
        return "夜用"
    else:
        return None 

products["補全長度"] = products.apply(extract_length, axis=1)
products["補全類型"] = products.apply(fill_type, axis=1)

# 依是否組合包拆成兩份資料
df_pack = products[products["是否組合包"] == 1].copy()
df_single = products[products["是否組合包"] == 0].copy()

def preprocess_and_cluster(df, group_name, best_k):
    print(f"\n=== {group_name} 分群分析 ===")
    features = df[["特價", "銷量", "補全長度", "補全類型", "品牌"]].copy()
    
    cat_cols = ["補全類型", "品牌"]
    num_cols = ["特價", "銷量", "補全長度"]

    ohe = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    cat_data = ohe.fit_transform(features[cat_cols])
    
    scaler = StandardScaler()
    num_data = scaler.fit_transform(features[num_cols])
    
    X = np.hstack([num_data, cat_data])

    inertias = []
    K_range = range(2, 11)
    for k in K_range:
        kmeans = KMeans(n_clusters=k, random_state=42)
        kmeans.fit(X)
        inertias.append(kmeans.inertia_)

    plt.figure(figsize=(8, 4))
    plt.plot(K_range, inertias, 'bo-')
    plt.xlabel("群數 k")
    plt.ylabel("總內部誤差 (Inertia)")
    plt.title(f"{group_name} Elbow Method")
    plt.grid(True)
    plt.show()

    kmeans = KMeans(n_clusters=best_k, random_state=42)
    labels = kmeans.fit_predict(X)
    df["cluster"] = labels

    pca = PCA(n_components=2, random_state=42)
    X_pca = pca.fit_transform(X)

    plt.figure(figsize=(10, 7))
    sns.scatterplot(x=X_pca[:, 0], y=X_pca[:, 1], hue=labels, palette="Set2", s=60, edgecolor="k")
    plt.title(f"{group_name} KMeans 分群視覺化 (k={best_k})")
    plt.xlabel("PCA 1")
    plt.ylabel("PCA 2")
    plt.legend(title="群集編號")
    plt.grid(True)
    plt.show()

    # 群集摘要
    for i in range(best_k):
        cluster_data = df[df["cluster"] == i]
        print(f"\n-- {group_name} 群集 {i} --")
        print(f"筆數: {len(cluster_data)}")
        print(f"平均價: {cluster_data['特價'].mean():.2f}")
        print(f"平均銷量: {cluster_data['銷量'].mean():.2f}")
        print(f"平均長度: {cluster_data['補全長度'].mean():.2f}")
        print("品牌分布:")
        print(cluster_data["品牌"].value_counts())
    
    return df

df_pack_clustered = preprocess_and_cluster(df_pack, "組合包", best_k=4)
df_single_clustered = preprocess_and_cluster(df_single, "非組合包", best_k=6)
