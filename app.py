# app.py
import streamlit as st
from collections import Counter, defaultdict

st.set_page_config(page_title="事業所診断", layout="centered")

# --- 質問データ（5問） ---
# type: "checkbox" は複数選択可、"radio" は一択
questions = [
    {
        "id": 1,
        "text": "分野",
        "type": "checkbox",
        "options": ["急性期病院", "一般病院", "外来クリニック", "透析・外来クリニック", "健診", "訪問看護", "介護福祉施設"]
    },
    {
        "id": 2,
        "text": "地域",
        "type": "checkbox",
        "options": ["神奈川県川崎市", "神奈川県横浜市", "東京都昭島市", "東京都立川市", "埼玉県狭山市"]
    },
    {
        "id": 3,
        "text": "年代",
        "type": "radio",
        "options": ["20代", "30代", "40代", "50代以上"]
    },
    {
        "id": 4,
        "text": "キャリア",
        "type": "checkbox",
        "options": ["キャリアを積みたい", "キャリアを活かしたい"]
    },
    {
        "id": 5,
        "text": "宿直",
        "type": "checkbox",
        "options": ["宿直あり", "宿直なし"]
    },
]

# --- 10個の答え候補（表示用のラベル） ---
RESULT_LABELS = {
    "A1": "川崎幸病院",
    "A2": "横浜石心会病院",
    "A3": "川崎地域ケア病院",
    "A4": "川崎幸クリニック",
    "A5": "第二川崎幸クリニック",
    "A6": "新緑脳神経外科",
    "A7": "川崎クリニック",
    "A8": "さいわい鹿島田クリニック",
    "A9": "川崎健診クリニック",
    "A10": "アルファメディック・クリニック",
    "A11": "さいわい訪問看護ステーション",
    "A12": "立川新緑クリニック",
    "A13": "昭島腎クリニック",
    "A14": "立川訪問看護ステーションわかば",
    "A15": "立川介護老人保健施設わかば",
    "A16": "埼玉石心会病院",
    "A17": "さやま総合クリニック",
    "A18": "さやま地域ケアクリニック",
    "A19": "さやま腎クリニック",
    "A20": "いきいき訪問看護ステーション鵜ノ木",
    "A21": "特別養護老人ホームオリーブ"
}

# --- 各選択肢がどの答え候補に紐づくか（タグ付け） ---
# ひとつの選択肢が複数の答えに紐づいていてOK
mapping = {
    # Q1
    "急性期病院": ["A1", "A16"],
    "一般病院": ["A2", "A3"],
    "外来クリニック": ["A4", "A5", "A6", "A12", "A17", "A18"],
    "透析・外来クリニック": ["A7", "A8", "A13", "A19"],
    "健診": ["A9", "A10"],
    "訪問看護": ["A11", "A14", "A20"],
    "介護福祉施設": ["A15", "A21"], 

    # Q2
    "神奈川県川崎市": ["A1", "A3", "A4", "A5", "A7", "A8", "A9", "A10", "A11"],
    "神奈川県横浜市": ["A2", "A6"],
    "東京都昭島市": ["A13"],
    "東京都立川市": ["A12", "A14", "A15"],
    "埼玉県狭山市": ["A16", "A17", "A18", "A19", "A20", "A21"],

    # Q3
    "20代": ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "A11", "A12", "A13", "A14",
            "A15", "A16", "A17", "A18", "A19", "A20", "A21"],
    "30代": ["A4", "A5", "A6", "A7", "A8", "A9", "A10", "A11", "A12", "A13", "A14",
            "A15", "A17", "A18", "A19", "A20", "A21"],
    "40代": ["A11", "A14", "A15", "A18", "A20", "A21"],
    "50代以上": ["A11", "A14", "A15", "A20", "A21"],

    # Q4
    "キャリアを積みたい": ["A1", "A2", "A16"],
    "キャリアを活かしたい": ["A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "A11", "A12", "A13", "A14",
            "A15", "A17", "A18", "A19", "A20", "A21"],

    # Q5
    "宿直あり": ["A1", "A2", "A3", "A16", "A18"],
    "宿直なし": ["A4", "A5", "A6", "A7", "A8", "A9", "A10", "A11", "A12", "A13", "A14",
            "A15", "A17", "A19", "A20", "A21"],
}

# --- UI ---
st.title("事業所診断（Streamlit）")
st.write("あなたに合った事業所を診断してみよう！　表示条件：**3つ以上一致**")

# use a form so user selects all answers and submits once
with st.form("quiz_form"):
    user_selections = []  # flattened list of chosen option strings
    st.write("**該当するものを選んでください**")
    for q in questions:
        st.markdown(f"**{q['text']}**")
        if q["type"] == "checkbox":
            selected = st.multiselect("選択肢（複数可）", q["options"], key=f"q{q['id']}")
            # multiselect returns list
            user_selections.extend(selected)
        else:  # radio
            selected = st.radio("選択肢（1つ）", q["options"], key=f"q{q['id']}")
            user_selections.append(selected)

    submitted = st.form_submit_button("診断する")

# --- 判定ロジック（関数化してテストしやすく） ---
def compute_results(selections, mapping, threshold=3):
    """
    selections: list of selected option strings
    mapping: dict option -> list of result keys (e.g. "A1")
    threshold: minimumカウントで結果として採用
    returns: list of tuples [(result_key, count), ...] sorted by count desc
    """
    counter = Counter()
    # Each chosen option may map to several result keys
    for opt in selections:
        for key in mapping.get(opt, []):
            counter[key] += 1

    # filter by threshold
    matched = [(k, v) for k, v in counter.items() if v >= threshold]
    matched.sort(key=lambda x: (-x[1], x[0]))
    return matched, counter

# --- 表示（結果） ---
if submitted:
    if not user_selections:
        st.warning("1つ以上の選択が必要です。")
    else:
        matched, all_counts = compute_results(user_selections, mapping, threshold=3)

     #   st.subheader("🔎 カウント状況（内部）")
        # show raw counts in a neat way
    #    counts_display = {RESULT_LABELS.get(k, k): v for k, v in all_counts.items()}
     #   st.json(counts_display)

        st.subheader("✅ 診断結果")
        if matched:
            st.success(f"{len(matched)}件が条件（3以上）を満たしました：")
            for key, cnt in matched:
                st.markdown(f"**{RESULT_LABELS[key]}** — スコア: {cnt}")
                # ここに詳細説明や画像、リンクなどを追加可能
                # st.write("説明テキスト...")
        else:
            st.info("該当するタイプがありませんでした（3以上の一致なし）。")
            # フォールバック：上位3つを表示
            top3 = sorted(all_counts.items(), key=lambda x: -x[1])[:3]
            if top3:
                st.write("一致数が多い上位（参考）:")
                for k, v in top3:
                    st.write(f"- {RESULT_LABELS.get(k,k)} — スコア: {v}")
