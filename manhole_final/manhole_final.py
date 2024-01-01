
# 라이브러리 불러오기 
import pandas as pd
import numpy as np
import datetime
import joblib
from keras.models import load_model
from haversine import haversine
from urllib.parse import quote
import streamlit as st
from streamlit_folium import st_folium
import folium
import branca
from geopy.geocoders import Nominatim
import ssl
from urllib.request import urlopen
import plotly.express as px
import streamlit as st
from streamlit_option_menu import option_menu
import streamlit.components.v1 as html
from  PIL import Image
import io
from st_aggrid import AgGrid, GridUpdateMode
from st_aggrid.grid_options_builder import GridOptionsBuilder
from streamlit_js_eval import streamlit_js_eval

# 시간 정보 가져오기
now_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)

# ----------------------------------------------- ▼ 함수 생성 START ▼ -----------------------------------------------
# 데이터 파일 읽기
def load_data():
    manhole_details = pd.read_excel('./맨홀관리대장_서식.xlsx')
    manhole_search = pd.read_csv('./manhole_search.csv', encoding='euc-kr')
    return manhole_details, manhole_search

manhole_details, manhole_search = load_data()

# 맨홀 데이터 필터링 함수
def filter_manholes(df, search_query):
    if search_query:
        return df[df['설치주소'].str.contains(search_query, na=False)]
    else:
        return df
 
# geocoding : 거리주소 -> 위도/경도 변환 함수
# Nominatim 파라미터 : user_agent="geoapiExercises", timeout=None
# 리턴 변수(위도,경도) : lati, long
# 참고: https://m.blog.naver.com/rackhunson/222403071709
def geocode(address):
    try:
        geolocator = Nominatim(user_agent="geoapiExercises", timeout=None)
        location = geolocator.geocode(address)
        if location:
            return location.latitude, location.longitude
        else:
            return None, None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None, None

# 필터링된 결과에 맞는 상세 정보 찾기
def get_manhole_details_by_address(selected_address):
    details = manhole_details[manhole_details['설치주소'] == selected_address]
    return details

# 필터링된 결과에 맞는 상세 정보 찾기
def get_manhole_details(selected_address):
    details = manhole_details[manhole_details['설치주소'] == selected_address]
    return details

def on_checkbox_change():
    st.session_state['search_performed'] = True

def refresh():
    Server.get_current()._reloader.reload()
    
def download_csv(df):
    df.to_csv(f"C:/Users/user/Downloads/manhol_searched_{cnt}.csv", index=False)

st.set_page_config(layout="wide")

def main():
    
    with st.sidebar:
        choose = option_menu("Main Menu", ["맨홀 관리 현황", "전수 조사 현황"],
                             icons=['gear', 'graph-up-arrow'],
                             menu_icon="menu-button-wide", default_index=0,
                             styles={
                             # default_index = 처음에 보여줄 페이지 인덱스 번호
            "container": {"padding": "4!important", "background-color": "#fafafa"},
            "icon": {"color": "black", "font-size": "25px"}, 
            "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#000000"},
            "nav-link-selected": {"background-color": "#ED2024"},
        } # css 설정
        )

    if choose == "맨홀 관리 현황":
        # Streamlit 앱 설정
        st.title(':hole: Manhole Master')
        col110, col111, col112, col113 = st.columns([0.2, 0.3, 0.3, 0.3])
        with col110:
            st.markdown("")
            st.info("맨홀 목록 조회")
            st.markdown("")

        # 필터링 및 지도 표시에 사용할 열 선택
        selected_columns = ['관리번호', '맨홀종류', '관할지자체', '맨홀뚜껑재질',
                            '차도도보구분', '도로포장종류', '관리기관', '설치주소', '설치년도', '내부점검일자', '외부점검일자']
        df = manhole_search[selected_columns]
        df_origin = manhole_details.copy()
        
        # 필터링된 결과 초기화
        filtered_df = df.copy()
        filtered_df['내부점검일자'] = pd.to_datetime(filtered_df['내부점검일자'], format='%Y-%m-%d')
        filtered_df['외부점검일자'] = pd.to_datetime(filtered_df['외부점검일자'], format='%Y-%m-%d')

        # Multibox에서 선택 가능한 항목 리스트
        options = ['맨홀종류', '관할지자체', '맨홀뚜껑재질', '차도도보구분', '도로포장종류', '관리기관', '설치년도', '내부점검일자', '외부점검일자']

        date_options = {
            '설치년도': range(1990, 2024),
            '내부점검일자': pd.date_range(start='1990-01-01', end='2024-12-31', freq='D'),
            '외부점검일자': pd.date_range(start='1990-01-01', end='2024-12-31', freq='D')
        }

        # 선택한 항목에 대한 세부 항목 딕셔너리
        sub_options = {
            '맨홀종류': ['상수도', '도시가스(밸브)', '통신', '하수도', '한전'],
            '관할지자체': ['강남구', '강동구', '강북구', '강서구', '관악구', '광진구', '구로구', '금천구', '노원구', '도봉구', '동대문구', '동작구', '마포구', '서대문구', '서초구', '성동구', '성북구', '송파구', '양천구', '영등포구', '용산구', '은평구', '종로구', '중구', '중랑구'],
            '맨홀뚜껑재질': ['주철', '콘크리트'],
            '차도도보구분': ['보도', '차도'],
            '도로포장종류': ['고압보도', '아스팔트'],
            '관리기관': ['SH공사', '수도사업소', '지자체_치수과', '한국전력공사', '㈜예스코'],
            '설치년도': date_options['설치년도'],
            '내부점검일자': date_options['내부점검일자'],
            '외부점검일자': date_options['외부점검일자']
        }

        # 선택한 항목에 대한 세부 항목들을 담을 딕셔너리
        selected_sub_options = {}

        # 선택한 항목에 대한 Multibox 생성
        selected_options = st.multiselect('조회 항목 선택', options)

        selected_dates = {}
        # 선택한 항목에 대한 Multibox를 만들고, 선택한 세부 항목들을 종합
        for option in selected_options:
            if option in date_options:
                if option == '설치년도':
                    min_value, max_value = 1990, 2024
                    date_range = st.slider(f'{option} 선택', min_value=min_value, max_value=max_value, value=(min_value, max_value))
                    selected_dates[option] = date_range
                else:
                    min_value, max_value = datetime.datetime(1990,1,1), datetime.datetime(2024,12,31)
                    date_range = st.slider(f'{option} 선택', min_value=min_value, max_value=max_value, value=(min_value, max_value))
                    selected_dates[option] = date_range
            else:
                sub_option = st.multiselect(option, sub_options[option])
                selected_sub_options[option] = sub_option
        
        cnt = 0
        with st.form(key='today_record'):
            if st.form_submit_button(label='Search'):
                cnt += 1

                global download_df
                selected_df = filtered_df.copy()
                download_df = selected_df.copy()
                
                for col, val in selected_dates.items():
                    selected_df = selected_df.loc[(selected_df[col] >= val[0]) & (selected_df[col] <= val[1])]
                    selected_df.reset_index(inplace=True)
                    selected_df.drop(columns=['index'], inplace=True)
                    
                for col, val in selected_sub_options.items():
                    selected_df = selected_df.loc[selected_df[col].isin(val)]
                    selected_df.reset_index(inplace=True)
                    selected_df.drop(columns=['index'], inplace=True)
                
                d_count = len(selected_df)
                if d_count > 0:
                    st.write("맨홀 목록 조회 결과입니다.")
                    st.dataframe(selected_df)
                    download_df = selected_df.copy()
                    
                else:
                    selected_df.reset_index(inplace=True)
                    st.markdown("이력이 없습니다.")

        extra_submit_button1 = st.button("Refresh")
        if extra_submit_button1:
            streamlit_js_eval(js_expressions="parent.window.location.reload()")
        
        extra_submit_button2 = st.button("Download")
        if extra_submit_button2:
            download_csv(download_df)
    
    elif choose == "전수 조사 현황":
        st.write("메뉴 이름2에 해당하는 페이지입니다.")
    #elif choose == "메뉴 이름3... 등등":
        #st.write("메뉴 이름3... 등등에 해당하는 페이지입니다.")

if __name__ == "__main__":
    main()
