# -*- coding: utf-8 -*-
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import matplotlib as mpl
import matplotlib.font_manager as fm
import urllib.request

# ==========================================
# 0. 스트림릿 클라우드 환경 한글 폰트 설정
# ==========================================
@st.cache_resource
def load_korean_font():
    """리눅스 서버 환경에서 나눔 폰트를 다운로드하고 matplotlib에 등록합니다."""
    font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
    font_path = "NanumGothic.ttf"
    
    if not os.path.exists(font_path):
        try:
            req = urllib.request.Request(font_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(font_path, 'wb') as out_file:
                out_file.write(response.read())
        except Exception as e:
            return "sans-serif"
            
    try:
        if os.path.exists(font_path):
            fm.fontManager.addfont(font_path)
            font_prop = fm.FontProperties(fname=font_path)
            return font_prop.get_name()
    except:
        pass
    return "sans-serif"

font_name = load_korean_font()

rc_params = {
    'font.family': font_name,
    'axes.unicode_minus': False
}
mpl.rcParams.update(rc_params)
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = font_name
plt.rcParams['axes.unicode_minus'] = False

# ==========================================
# 세션 상태(Session State) 초기화 (결과 및 버튼 클릭 상태 저장)
# ==========================================
if 'hofstee_results' not in st.session_state:
    st.session_state.hofstee_results = {}

# 웹페이지 제목 및 설명
st.set_page_config(page_title="Hofstee 방식 웹앱 실험실", layout="centered")
st.title("📊 Hofstee 방식 분할점수 설정 시뮬레이터")
st.markdown("""
'지필평가조회-교과목별일람표 조회-전체학급'에서 다운로드한 엑셀(XLS-data) 파일을 업로드하고, 
성취도별 허용 기준을 입력하여 **Hofstee 합격선(교점)**을 계산하고 저장하는 웹앱입니다.
""")

st.divider()

# ==========================================
# 1. 엑셀 파일 업로드 및 데이터 정제
# ==========================================
st.header("1단계: 데이터 업로드")
uploaded_file = st.file_uploader("나이스에서 지필평가조회 탭의 **교과목별일람표-전체학급** 엑셀 파일(XLS-data)을 선택해주세요.", type=["xls", "xlsx"])

if uploaded_file is not None:
    try:
        df_raw = pd.read_excel(uploaded_file, skiprows=4, header=0)
        first_column = df_raw.columns[0]
        df_raw['temp_numeric_id'] = pd.to_numeric(df_raw[first_column], errors='coerce')
        df_student_rows = df_raw[df_raw['temp_numeric_id'].notna()].copy()
        target_columns = df_student_rows.columns[1:-1]

        st.success(f"🎯 자동으로 감지된 학급 열: {list(target_columns)}")

        all_scores_series = df_student_rows[target_columns].stack()
        all_scores_numeric = pd.to_numeric(all_scores_series, errors='coerce').dropna()
        valid_scores = all_scores_numeric[(all_scores_numeric >= 0) & (all_scores_numeric <= 100)]

        df = pd.DataFrame({'score': valid_scores.values})
        st.info(f"🎯 [정제 완료] 실제 학생 점수 데이터 총 {len(df)}개 수합 완료!")

        # 누적 분포 계산 (S-Curve)
        df['score_round'] = df['score'].round().astype(int)
        dist_data = df.groupby('score_round', as_index=False).size().rename(columns={'score_round': 'score', 'size': 'n'})
        dist_data = dist_data.sort_values('score', ascending=False)

        dist_data['cum_n'] = dist_data['n'].cumsum()
        total_n = dist_data['n'].sum()
        dist_data['cum_prop'] = (dist_data['cum_n'] / total_n) * 100
        dist_data = dist_data.sort_values('score').reset_index(drop=True)

        st.divider()

        # ==========================================
        # 2. 성취도 구간 선택 및 초기값 맵핑
        # ==========================================
        st.header("2단계: 성취도 구간 선택 및 허용 기준 설정")
        
        # 분할점수 구간 선택
        target_step = st.radio(
            "설정할 분할점수 구간을 선택하세요:",
            ["A/B분할점수", "B/C분할점수", "C/D분할점수", "D/E분할점수", "E/미도달분할점수"],
            horizontal=True
        )

        # 구간별 초기값 딕셔너리 세팅
        default_values = {
            "A/B분할점수": {"ymin": 10.0, "ymax": 20.0, "xmin": 80.0, "xmax": 90.0},
            "B/C분할점수": {"ymin": 35.0, "ymax": 45.0, "xmin": 65.0, "xmax": 80.0},
            "C/D분할점수": {"ymin": 60.0, "ymax": 70.0, "xmin": 50.0, "xmax": 65.0},
            "D/E분할점수": {"ymin": 80.0, "ymax": 100.0, "xmin": 40.0, "xmax": 50.0},
            "E/미도달분할점수": {"ymin": 95.0, "ymax": 100.0, "xmin": 30.0, "xmax": 40.0}
        }
        
        current_defaults = default_values[target_step]

        skip_step = False
        if target_step == "E/미도달분할점수":
            skip_step = st.checkbox("❌ 이 구간(E/미도달) 분할점수 설정은 생략합니다.")
            if skip_step:
                if target_step in st.session_state.hofstee_results:
                    del st.session_state.hofstee_results[target_step]
                st.info("💡 E/미도달 구간 설정이 생략되었습니다. 아래 저장 현황을 확인하거나 다른 구간을 설정해주세요.")

        if not skip_step:
            st.markdown("""
            **[입력 순서]**
            1. **누적 비율 권장치(최소/최대)**를 먼저 설정합니다. 
            2. **'비율 설정 완료'** 버튼을 누르면 **평가 점수 권장치(최소/최대)** 입력창이 활성화됩니다.
            """)
            
            st.caption("⚠️ *초기값으로 설정된 값은 권장수치로 개인적인 견해에 바탕합니다.*")

            # 2-1. 누적 비율 먼저 입력받기 (설정된 초기값 적용)
            st.subheader(f"📍 [{target_step}] 누적 비율 설정")
            col_y1, col_y2 = st.columns(2)
            with col_y1:
                user_ymin = st.number_input("누적 비율 권장 최소값 (Y축 최소, %)", min_value=0.0, max_value=100.0, value=current_defaults["ymin"], step=1.0, key=f"ymin_{target_step}")
            with col_y2:
                user_ymax = st.number_input("누적 비율 권장 최대값 (Y축 최대, %)", min_value=0.0, max_value=100.0, value=current_defaults["ymax"], step=1.0, key=f"ymax_{target_step}")

            # 👉 [설정] 버튼 추가
            # 각 구간별로 버튼 클릭 상태를 분리하기 위해 key에 target_step을 결합합니다.
            click_btn = st.button("⚙️ 비율 설정 완료 (점수 입력 활성화)", key=f"btn_{target_step}")
            
            # 세션 상태를 이용해 버튼 클릭 여부를 기억 (구간 이동 시 오작동 방지)
            session_btn_key = f"is_set_{target_step}"
            if click_btn:
                if user_ymax > user_ymin:
                    st.session_state[session_btn_key] = True
                else:
                    st.error("❌ 누적 비율 최대값은 최소값보다 커야 합니다.")
                    st.session_state[session_btn_key] = False

            # 👉 비율 설정이 완료(True) 되었을 때만 아래 로직 실행
            if st.session_state.get(session_btn_key, False):
                st.success(f"✅ 비율 설정 반영 완료: {user_ymin}% ~ {user_ymax}%")
                
                st.subheader(f"📍 [{target_step}] 점수 범위 설정")
                col_x1, col_x2 = st.columns(2)
                with col_x1:
                    user_xmin = st.number_input("평가 점수 권장 최소값 (X축 최소)", min_value=0.0, max_value=100.0, value=current_defaults["xmin"], step=1.0, key=f"xmin_{target_step}")
                with col_x2:
                    user_xmax = st.number_input("평가 점수 권장 최대값 (X축 최대)", min_value=0.0, max_value=100.0, value=current_defaults["xmax"], step=1.0, key=f"xmax_{target_step}")
                
                rect_width = user_xmax - user_xmin
                rect_height = user_ymax - user_ymin

                if user_xmax != user_xmin:
                    slope_line = (user_ymin - user_ymax) / (user_xmax - user_xmin)
                    intercept_line = user_ymax - slope_line * user_xmin
                else:
                    slope_line, intercept_line = 0, 0

                intersection_x = None
                intersection_y = None

                for i in range(len(dist_data) - 1):
                    x1, y1 = dist_data.loc[i, 'score'], dist_data.loc[i, 'cum_prop']
                    x2, y2 = dist_data.loc[i+1, 'score'], dist_data.loc[i+1, 'cum_prop']

                    if x2 != x1:
                        slope_scurve = (y2 - y1) / (x2 - x1)
                        intercept_scurve = y1 - slope_scurve * x1

                        if slope_line != slope_scurve:
                            candidate_x = (intercept_scurve - intercept_line) / (slope_line - slope_scurve)
                            if (x1 <= candidate_x <= x2) and (user_xmin <= candidate_x <= user_xmax):
                                intersection_x = candidate_x
                                intersection_y = slope_line * intersection_x + intercept_line
                                break

                # ==========================================
                # 3. 결과 출력 및 그래프 시각화
                # ==========================================
                st.divider()
                st.header("3단계: 분석 결과 및 시각화")

                if intersection_x is not None:
                    st.success(f"🎯 **Hofstee 합격선(교점) 계산 성공!**")
                    metric_col1, metric_col2 = st.columns(2)
                    metric_col1.metric("분할점수 (컷오프 점수)", f"{intersection_x:.2f} 점")
                    metric_col2.metric("누적 탈락 비율", f"{intersection_y:.2f} %")
                    
                    if st.button(f"💾 현재 [{target_step}] 결과 데이터에 저장하기"):
                        st.session_state.hofstee_results[target_step] = {
                            "분할점수(점)": round(intersection_x, 2),
                            "누적탈락비율(%)": round(intersection_y, 2),
                            "점수범위": f"{user_xmin}~{user_xmax}",
                            "비율범위": f"{user_ymin}~{user_ymax}"
                        }
                        st.toast(f"✅ {target_step} 결과가 성공적으로 기록되었습니다!", icon="💾")
                else:
                    st.warning("⚠️ 대각선과 S-Curve가 설정한 사각형 범위 내에서 만나지 않습니다. 비율이나 점수 범위를 조절해 주세요.")

                fig, ax = plt.subplots(figsize=(10, 5))
                sns.lineplot(data=dist_data, x='score', y='cum_prop', color='blue', linewidth=2.5, label='S-Curve', ax=ax)
                ax.add_patch(plt.Rectangle((user_xmin, user_ymin), rect_width, rect_height, color='red', alpha=0.15))
                ax.plot([user_xmin, user_xmax], [user_ymax, user_ymin], color='darkgreen', linestyle='--', linewidth=2, label='Hofstee Line')

                if intersection_x is not None:
                    ax.scatter(intersection_x, intersection_y, color='red', s=100, zorder=5, edgecolor='black')
                    ax.text(intersection_x + 1, intersection_y + 3,
                             f"분할점수: {intersection_x:.1f}점\n(비율: {intersection_y:.1f}%)",
                             color='red', weight='bold', fontsize=10,
                             bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="red", lw=1, alpha=0.8))

                ax.set_title(f"Hofstee Method Intersection - [{target_step}]", fontsize=14, pad=15)
                ax.set_xlabel("지필/수행평가 점수(점)", fontsize=11)
                ax.set_ylabel("누적비율(%)", fontsize=11)
                ax.set_xlim(max(0, min(dist_data['score'].min() - 5, user_xmin - 5)), 105)
                ax.set_ylim(-5, 105)
                ax.legend(loc='upper right')
                st.pyplot(fig)

            else:
                st.info("💡 상단의 **'비율 설정 완료'** 버튼을 누르시면 점수 입력창과 결과 그래프가 나타납니다.")

        # ==========================================
        # 4. 저장된 분할점수 상시 노출 영역
        # ==========================================
        st.divider()
        st.header("📋 성취도별 분할점수 최종 저장 현황")
        
        if st.session_state.hofstee_results:
            summary_df = pd.DataFrame.from_dict(
                st.session_state.hofstee_results, 
                orient='index'
            )
            desired_order = ["A/B분할점수", "B/C분할점수", "C/D분할점수", "D/E분할점수", "E/미도달분할점수"]
            existing_order = [step for step in desired_order if step in summary_df.index]
            summary_df = summary_df.loc[existing_order]
            
            st.dataframe(summary_df, use_container_width=True)
            
            if st.button("🔄 저장 데이터 전체 초기화"):
                # 모든 세션 데이터 완전히 비우기
                st.session_state.hofstee_results = {}
                for step in desired_order:
                    if f"is_set_{step}" in st.session_state:
                        st.session_state[f"is_set_{step}"] = False
                st.rerun()
        else:
            st.info("아직 저장된 분할점수 결과가 없습니다. 산출된 교점을 확인하고 상단의 '결과 데이터에 저장하기' 버튼을 눌러주세요.")

    except Exception as e:
        st.error(f"파일을 처리하는 중 오류가 발생했습니다. 성적 일람표 양식이 맞는지 확인해주세요. 오류 메시지: {e}")
else:
    st.info("💡 성적 분석을 위해 상단의 엑셀 파일을 업로드해주세요.")