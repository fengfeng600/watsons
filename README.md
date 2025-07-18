專案題目
女性生理用品商品分群與分析 — 屈臣氏為例

專案簡介
本專案利用屈臣氏女性生理用品銷售資料，透過資料清理、特徵萃取與KMeans分群，分析產品在品牌、價格、銷量、包裝型態與產品類型上的差異。結果可協助業者優化產品定位與行銷策略，了解市場結構。

流程說明
        利用python Selenium爬蟲
        將資料用python建立資料庫模型匯入MySQL
        讀取 MySQL 中屈臣氏產品資料
        利用正則表達式從商品名稱萃取長度與類型特徵
        缺值補全與類型補齊
        對品牌與類型進行 OneHot 編碼
        對價格、銷量、長度標準化處理
        分成「組合包」與「非組合包」兩大類別做分群
        使用 Elbow Method 判斷群數，並執行 KMeans 分群
        繪製群集分布圖（PCA降維視覺化）
        群集特徵統計與分析
        
詳細分析資料
https://www.canva.com/design/DAGtaAMUNzk/xchadW7kcFC0cEblh7aAXg/edit?utm_content=DAGtaAMUNzk&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton


