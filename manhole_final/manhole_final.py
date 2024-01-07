# 라이브러리 불러오기 
import pandas as pd
import datetime
import streamlit as st
from geopy.geocoders import Nominatim
from streamlit_option_menu import option_menu
from streamlit_js_eval import streamlit_js_eval
import plotly.express as px
import folium
from streamlit_folium import folium_static
import openpyxl
from openpyxl_image_loader import SheetImageLoader
from io import BytesIO

# 시간 정보 가져오기
now_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)

# ----------------------------------------------- ▼ 함수 생성 START ▼ -----------------------------------------------
# 데이터 파일 읽기
def load_data():
    manhole_details = pd.read_excel('./manhole_final/맨홀관리대장_서식.xlsx')
    manhole_search = pd.read_excel('./manhole_final/manhole_search.xlsx')
    return manhole_details, manhole_search

manhole_details, manhole_search = load_data()
    
# geocoding : 거리주소 -> 위도/경도 변환 함수
# Nominatim 파라미터 : user_agent="geoapiExercises", timeout=None
# 리턴 변수(위도,경도) : lati, long
# 참고: https://m.blog.naver.com/rackhunson/222403071709
def geocode(address):
    try:
        geolocator = Nominatim(user_agent="geoapiExercises", timeout=None)
        location = geolocator.geocode(address)
        return (location.latitude, location.longitude) if location else (None, None)
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None, None

color_sequence = [
    "#FF6D00",
    "#FFE0B2",   # 가장 밝음
    "#FFB74D"
]

def plot_pie_chart(df, column, title):
    fig = px.pie(df, names=column, title=title,
                 color_discrete_sequence=color_sequence)
    return fig

# 그룹별 맨홀 재질 파이 차트 그리기
def plot_grouped_pie_chart(df, group_column, pie_column):
    grouped = df.groupby(group_column)
    figs = []
    for name, group in grouped:
        fig = px.pie(group, names=pie_column, title=f"{name}",
                    color_discrete_sequence=color_sequence)
        figs.append(fig)
    return figs

# 지도 위치 표시 마커 함수
def add_location_marker(map_obj, lat, lon, popup_text):
    folium.Marker(
        [lat, lon],
        popup='Some popup text',
        icon=folium.Icon(color='red', icon='arrow')
    ).add_to(map_obj)

# Streamlit 앱 설정
st.set_page_config(layout="wide")

def main():
    # 사용자 정의 CSS를 스트림릿 앱에 삽입
    custom_css = """
    <style>
        
        /* 선택된 옵션의 배경 색상 변경 */
        .st-bx .st-dv, .st-bx .st-eg {
            background-color: #FFB74D;
        }

        
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)
    
    with st.sidebar:
        choose = option_menu("Main Menu", ["맨홀 관리 현황", "전수 조사 정보", "점검 대상 도출"],
                             icons=['gear', 'graph-up-arrow', 'check-circle'],
                             menu_icon="menu-button-wide", default_index=0,
                             styles={
                                 "container": {"padding": "4!important", "background-color": "#fafafa"},
                                 "icon": {"color": "black", "font-size": "25px"},
                                 "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#000000"},
                                 "nav-link-selected": {"background-color": ["#FFB74D"]},
                             }
                             )
    
    # Tab1에 해당
    if choose == "맨홀 관리 현황":
        # 맨홀 데이터에서 관리번호 추출
        manhole_numbers = manhole_search['관리번호'].unique().tolist()
        st.title(':hole: Manhole Master')
        #col110, col111, col112, col113 = st.columns([0.2, 0.3, 0.3, 0.3])
        #col110, col111 = st.columns([1, 0])
        #with col110:
        st.markdown("")
        st.info("맨홀 목록 조회")
        st.markdown("")

        # 필터링 및 지도 표시에 사용할 열 선택
        selected_columns = ['관리번호', '맨홀종류', '관할지자체', '맨홀뚜껑재질',
                            '차도도보구분', '도로포장종류', '관리기관', '설치주소',
                            '설치년도', '내부점검일자', '외부점검일자']
        df = manhole_search[selected_columns]
        df_origin = manhole_details.copy()
        
        # 필터링된 결과 초기화
        filtered_df = df.copy()
        filtered_df['내부점검일자'] = pd.to_datetime(filtered_df['내부점검일자'], format='%Y-%m-%d')
        filtered_df['외부점검일자'] = pd.to_datetime(filtered_df['외부점검일자'], format='%Y-%m-%d')

        # Multibox에서 선택 가능한 항목 리스트
        options = ['맨홀종류', '관할지자체', '맨홀뚜껑재질', '차도도보구분', '도로포장종류',
                   '관리기관', '설치년도', '내부점검일자', '외부점검일자']

        date_options = {
            '설치년도': range(1990, 2024),
            '내부점검일자': pd.date_range(start='1990-01-01', end='2024-12-31', freq='D'),
            '외부점검일자': pd.date_range(start='1990-01-01', end='2024-12-31', freq='D')
        }

        # 선택한 항목에 대한 세부 항목 딕셔너리
        sub_options = {
            '맨홀종류': ['상수도', '도시가스(밸브)', '통신', '하수도', '한전'],
            '관할지자체': ['강남구', '강동구', '강북구', '강서구', '관악구', '광진구', '구로구', '금천구', '노원구', '도봉구',
                      '동대문구', '동작구', '마포구', '서대문구', '서초구', '성동구', '성북구', '송파구', '양천구', '영등포구',
                      '용산구', '은평구', '종로구', '중구', '중랑구'],
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
        
        #extra_submit_button2 = st.button("Download")
        #if extra_submit_button2:
            #download_csv(download_df)
            
    # Tab2에 해당
    if choose == "전수 조사 정보":
        # 조사 진행 상황 -> 미조사/진행중/완료 => 전체, 지역, 관리기관별 선택 요소 반영하여 제시(파이차트)
        st.info("1. 조사 진행 상황")
        survey = st.radio("분류 옵션 선택", ('전체', '지역', '관리기관'), key='survey')

        if survey == '전체':
            pie_chart = plot_pie_chart(manhole_search, '조사 진행 상황', '전체 조사 진행 상황')
            st.plotly_chart(pie_chart)
        elif survey == '지역':
            area_options = manhole_search['관할지자체'].unique()
            selected_area = st.selectbox("지역 선택", area_options, key='area_survey')
            filtered_data = manhole_search[manhole_search['관할지자체'] == selected_area]
            area_chart = plot_pie_chart(filtered_data, '조사 진행 상황', f"{selected_area} 조사 진행 상황")
            st.plotly_chart(area_chart)
        elif survey == '관리기관':
            management_options = manhole_search['관리기관'].unique()
            selected_management = st.selectbox("관리기관 선택", management_options, key='management_survey')
            filtered_data = manhole_search[manhole_search['관리기관'] == selected_management]
            management_chart = plot_pie_chart(filtered_data, '조사 진행 상황', f"{selected_management} 조사 진행 상황")
            st.plotly_chart(management_chart)
            
        # 맨홀 재질 분류 -> 콘크리트/주철을 전체, 지역, 관리기관별 선택 요소 반영하여 제시(파이차트)
        st.info("2. 맨홀 재질 분류")
        material = st.radio("분류 옵션 선택", ('전체', '지역', '관리기관'), key='material')

        if material == '전체':
            pie_chart = plot_pie_chart(manhole_search, '맨홀뚜껑재질', '전체 맨홀 재질 분류')
            st.plotly_chart(pie_chart)
        elif material == '지역':
            area_options = manhole_search['관할지자체'].unique()
            selected_area = st.selectbox("지역 선택", area_options, key='area_material')
            filtered_data = manhole_search[manhole_search['관할지자체'] == selected_area]
            area_chart = plot_pie_chart(filtered_data, '맨홀뚜껑재질', f"{selected_area} 맨홀 재질 분류")
            st.plotly_chart(area_chart)
        elif material == '관리기관':
            management_options = manhole_search['관리기관'].unique()
            selected_management = st.selectbox("관리기관 선택", management_options, key='management_material')
            filtered_data = manhole_search[manhole_search['관리기관'] == selected_management]
            management_chart = plot_pie_chart(filtered_data, '맨홀뚜껑재질', f"{selected_management} 맨홀 재질 분류")
            st.plotly_chart(management_chart)

        # 맨홀 목록 시각화 -> 전체, 지역, 관리기관별 선택 요소 반영하여 교체 대상 비율 제시(파이차트)
        st.info("3. 맨홀 상태 분류")
        visualization_option = st.radio("분류 옵션 선택", ('전체', '지역', '관리기관'), key='visualization_option')

        if visualization_option == '전체':
            pie_chart = plot_pie_chart(manhole_search, '교체', '전체 맨홀 상태 분류')
            st.plotly_chart(pie_chart)
        elif visualization_option == '지역':
            area_options = manhole_search['관할지자체'].unique()
            selected_area = st.selectbox("지역 선택", area_options, key='area_selection_viz')
            filtered_data = manhole_search[manhole_search['관할지자체'] == selected_area]
            area_chart = plot_pie_chart(filtered_data, '교체', f"{selected_area} 맨홀 상태 분류")
            st.plotly_chart(area_chart)
        elif visualization_option == '관리기관':
            management_options = manhole_search['관리기관'].unique()
            selected_management = st.selectbox("관리기관 선택", management_options, key='management_selection_viz')
            filtered_data = manhole_search[manhole_search['관리기관'] == selected_management]
            management_chart = plot_pie_chart(filtered_data, '교체', f"{selected_management} 맨홀 상태 분류")
            st.plotly_chart(management_chart)

    # Tab3에 해당
    if choose == "점검 대상 도출":
        # 점검 필요 여부 확인
        st.info("1. 점검 대상 확인")
        st.write("맨홀 외부점검 상태 확인")

        # 마지막 외부 점검 이후 경과일 계산
        today = pd.Timestamp('today')
        manhole_search['경과일'] = (today - pd.to_datetime(manhole_search['외부점검일자'])).dt.days

        # 6개월(180일) 초과 시 점검 필요로 표시
        manhole_search['inspection_due'] = manhole_search['경과일'] > 180

        # 점검 필요 맨홀 표시
        overdue_inspections = manhole_search[manhole_search['inspection_due']]
        if len(overdue_inspections) > 0:
            col110, col111 = st.columns([0.5, 0.5])
            with col110:
                st.error("점검이 필요합니다. (6개월 이상 미점검)")
                overdue_inspections_sorted = overdue_inspections.sort_values(by='경과일', ascending=False)
                st.dataframe(overdue_inspections_sorted[['관리번호', '설치주소', '외부점검일자', '경과일']])

        # 6개월 이내에 점검된 맨홀 표시
        recent_inspections = manhole_search[~manhole_search['inspection_due']]
        if len(recent_inspections) > 0:
            col210, col211 = st.columns([0.5, 0.5])
            with col210:
                st.success("6개월 이내에 점검된 맨홀입니다.")
                recent_inspections_sorted = recent_inspections.sort_values(by='경과일', ascending=False)
                st.dataframe(recent_inspections_sorted[['관리번호', '설치주소', '외부점검일자', '경과일']])

        st.info("2. 세부 정보 확인")
        # 관할지자체 선택
        selected_area = st.selectbox("관할지자체 선택", manhole_search['관할지자체'].unique(), key='area_selection')
        area_manholes = manhole_search[manhole_search['관할지자체'] == selected_area]

        # 관할지자체에 따른 관리번호 선택
        selected_manhole_number = st.selectbox("관리번호 선택", area_manholes['관리번호'].unique(), key='manhole_selection')

        # 맨홀 위치 표시 버튼
        if st.button("맨홀 위치 표시"):
            selected_address = area_manholes[area_manholes['관리번호'] == selected_manhole_number]['설치주소'].iloc[0]
            lat, lon = geocode(selected_address)
            if lat and lon:
                m = folium.Map(location=[lat, lon], zoom_start=16)
                # 위치 표시 추가
                add_location_marker(m, lat, lon, "맨홀 위치")
                # 대시보드에 지도 표시
                folium_static(m)
            else:
                st.error(f"관리번호 '{selected_manhole_number}'의 맨홀 위치를 찾을 수 없습니다.")


        st.write("---")  # 구분선 추가

    #elif choose == "메뉴 이름3... 등등":
        #st.write("메뉴 이름3... 등등에 해당하는 페이지입니다.")

if __name__ == "__main__":
    main()
