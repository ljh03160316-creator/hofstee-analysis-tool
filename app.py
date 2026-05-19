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
    
    # 폰트 파일이 없으면 다운로드
    if not os.path.exists(font_path):
        try:
            urllib.request.urlretrieve(font_url, font_path)
        except Exception as e:
            return "sans-serif"
            
    # 폰트 매니저에 등록
    try:
        fm.fontManager.addfont(font_path)
        font_prop = fm.FontProperties(fname=font_path)
        return font_prop.get_name()
    except:
        return "sans-serif"

font_name = load_korean_font()

# matplotlib/seaborn 한글 및 마이너스 깨짐 설정
rc_params = {
    'font.family': font_name,
    'axes.unicode_minus': False
}
mpl.rcParams.update(rc_params)
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = font_name
plt.rcParams['axes.unicode_minus'] = False

# ==========================================
# 웹페이지 제목 및 설명
# ==========================================
st.set_page_config(page_title="Hofstee 방식 웹앱 실험실", layout="centered")
st.title("📊 Hofstee 방식 분할점수 설정 시뮬레이터")
st.markdown("""
'지필평가조회-교과목별일람표 조회-전체학급'에서 다운로드한 엑셀(XLS-data) 파일을 업로드하고, 
성취도별 허용 기준을 입력하여 **Hofstee 합격선(교점)**을 계산하는 웹앱입니다.
""")

st.divider()

# ==========================================
# 1. 엑셀 파일 업로드 및 데이터 정제
# ==========================================
st.header("1단계: 데이터 업로드")
uploaded_file = st.file_uploader("나이스에서 지필평가조회 탭의 **교과목별일람표-전체학급** 엑셀 파일(XLS-data)을 선택해주세요.", type=["xls", "xlsx"])

if uploaded_file is not None:
    try:
        # 1~4행은 건너뛰고 5행을 제목으로 가져옴
        df_raw = pd.read_excel(uploaded_file, skiprows=4, header=0)

        first_column = df_raw.columns[0]  # 첫 번째 열 (반번호 또는 번호)

        # A열의 데이터를 숫자형으로 강제 변환
        df_raw['temp_numeric_id'] = pd.to_numeric(df_raw[first_column], errors='coerce')

        # NaN이 아닌 행(정상적인 숫자 번호가 있던 행)만 추출
        df_student_rows = df_raw[df_raw['temp_numeric_id'].notna()].copy()

        # B열부터 마지막 열까지 학급 열 지정
        target_columns = df_student_rows.columns[1:-1]

        st.success(f"🎯 자동으로 감지된 학급 열: {list(target_columns)}")

        # 선택한 학급 열들의 데이터를 하나로 길게 이어 붙임
        all_scores_series = df_student_rows[target_columns].stack()

        # 데이터 정제: 결측치 제거 및 정상적인 시험 점수 범위(0~100점)만 추출
        all_scores_numeric = pd.to_numeric(all_scores_series, errors='coerce').dropna()
        valid_scores = all_scores_numeric[(all_scores_numeric >= 0) & (all_scores_numeric <= 100)]

        # 최종 분석용 데이터프레임 생성
        df = pd.DataFrame({'score': valid_scores.values})
        
        st.info(f"🎯 [정제 완료] 실제 학생 점수 데이터 총 {len(df)}개 수합 완료!")

        # 2. 누적 분포 계산 (S-Curve)
        df['score_round'] = df['score'].round().astype(int)
        dist_data = df.groupby('score_round', as_index=False).size().rename(columns={'score_round': 'score', 'size': 'n'})
        dist_data = dist_data.sort_values('score', ascending=False)

        # 역방향 누적합 및 비율 계산
        dist_data['cum_n'] = dist_data['n'].cumsum()
        total_n = dist_data['n'].sum()
        dist_data['cum_prop'] = (dist_data['cum_n'] / total_n) * 100

        # 시각화를 위해 다시 점수를 오름차순으로 정렬
        dist_data = dist_data.sort_values('score').reset_index(drop=True)

        st.divider()

        # ==========================================
        # 3. 사용자 임의 허용 기준 입력받기 (UI 컴포넌트로 변경)
        # ==========================================
        st.header("2단계: Hofstee 허용 기준 영역 설정")
        st.markdown("""
        지필(수행)평가에 대한 성취도별 허용 점수 범위 및 누적비율 허용 범위를 지정하세요.  
        (예시) A성취도 분할점수/비율 확인을 위한 입력치  
        -> 점수 최소 = 80, 점수 최대 = 90, 누적 비율 최소 = 10, 누적 비율 최대 = 20  
          
        **B성취도부터는 성취도의 누적 비율이므로, 누적 비율 권장치 입력할 때 A비율을 합친 값으로 입력**  
        (예) 성취도 A 비율은 대략 20%이고, 성취도 B 비율을 20~30%로 설정하고 싶을 때,  
             입력할 누적 비율 최소 = 40, 누적 비율 최대 = 50 으로 입력할 것!""")

        col1, col2 = st.columns(2)
        with col1:
            user_xmin = st.number_input("해당 성취도의 평가 **점수** 권장 **최소** 기준값 (X축 최소)", value=70.0, step=1.0)
            user_xmax = st.number_input("해당 성취도의 평가 **점수** 권장 **최대** 기준값 (X축 최대)", value=85.0, step=1.0)
        with col2:
            user_ymin = st.number_input("해당 성취도의 **누적 비율** 권장 **최소** 기준값 (Y축 최소, %)", value=10.0, step=1.0)
            user_ymax = st.number_input("해당 성취도의 **누적 비율** 권장 **최대** 기준값 (Y축 최대, %)", value=30.0, step=1.0)

        # 사각형의 너비와 높이 계산
        rect_width = user_xmax - user_xmin
        rect_height = user_ymax - user_ymin

        # ==========================================
        # 3-2. 대각선과 S-Curve의 교점 구하기
        # ==========================================
        # 대각선 직선 방정식의 기울기(a)와 Y절편(b) 계산 (y = ax + b)
        if user_xmax != user_xmin:
            slope_line = (user_ymin - user_ymax) / (user_xmax - user_xmin)
            intercept_line = user_ymax - slope_line * user_xmin
        else:
            slope_line = 0
            intercept_line = 0

        intersection_x = None
        intersection_y = None

        # 정렬된 dist_data를 순회하며 인접한 두 점 사이의 선분을 확인
        for i in range(len(dist_data) - 1):
            x1, y1 = dist_data.loc[i, 'score'], dist_data.loc[i, 'cum_prop']
            x2, y2 = dist_data.loc[i+1, 'score'], dist_data.loc[i+1, 'cum_prop']

            if x2 != x1:
                slope_scurve = (y2 - y1) / (x2 - x1)
                intercept_scurve = y1 - slope_scurve * x1

                if slope_line != slope_scurve:
                    candidate_x = (intercept_scurve - intercept_line) / (slope_line - slope_scurve)

                    # 교점이 S-Curve 선분 내에 있고, 설정한 사각형 범위 내에 있는지 확인
                    if (x1 <= candidate_x <= x2) and (user_xmin <= candidate_x <= user_xmax):
                        intersection_x = candidate_x
                        intersection_y = slope_line * intersection_x + intercept_line
                        break

        # ==========================================
        # 4. 결과 출력 및 그래프 시각화
        # ==========================================
        st.divider()
        st.header("3단계: 분석 결과 및 시각화")

        if intersection_x is not None:
            st.success(f"🎯 **Hofstee 합격선(교점) 계산 성공**")
            metric_col1, metric_col2 = st.columns(2)
            metric_col1.metric("분할점수 (컷오프 점수)", f"{intersection_x:.2f} 점")
            metric_col2.metric("누적 탈락 비율", f"{intersection_y:.2f} %")
        else:
            st.warning("⚠️ 대각선과 S-Curve가 설정한 허용 기준 범위(사각형 내부) 내에서 만나지 않습니다. 허용 기준 범위를 조절해 주세요.")

        # 그래프 그리기
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # S-Curve 및 가이드라인
        sns.lineplot(data=dist_data, x='score', y='cum_prop', color='blue', linewidth=2.5, label='S-Curve', ax=ax)
        ax.add_patch(plt.Rectangle((user_xmin, user_ymin), rect_width, rect_height, color='red', alpha=0.15))
        ax.plot([user_xmin, user_xmax], [user_ymax, user_ymin], color='darkgreen', linestyle='--', linewidth=2, label='Hofstee Line')

        # 교점이 존재할 경우 강조 표시
        if intersection_x is not None:
            ax.scatter(intersection_x, intersection_y, color='red', s=100, zorder=5, edgecolor='black')
            ax.text(intersection_x + 1, intersection_y + 3,
                     f"분할점수: {intersection_x:.1f}점\n(분포비율: {intersection_y:.1f}%)",
                     color='red', weight='bold', fontsize=10,
                     bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="red", lw=1, alpha=0.8))

        # 타이틀 및 레이블 설정
        ax.set_title("Hofstee Method Cut-off Intersection", fontsize=14, pad=15)
        ax.set_xlabel("지필/수행평가 점수(점)", fontsize=11)
        ax.set_ylabel("누적비율(%)", fontsize=11)
        ax.set_xlim(min(dist_data['score'].min() - 5, user_xmin - 5), 105)
        ax.set_ylim(-5, 105)
        ax.legend(loc='upper right')

        # 스트림릿에 그래프 출력
        st.pyplot(fig)

    except Exception as e:
        st.error(f"파일을 처리하는 중 오류가 발생했습니다. 성적 일람표 양식이 맞는지 확인해주세요. 오류 메시지: {e}")

else:
    st.info("💡 성적 분석을 위해 상단의 엑셀 파일을 업로드해주세요.")
