import streamlit as st
import pandas as pd
from openpyxl import load_workbook
import requests
from bs4 import BeautifulSoup
import time
import re

# 设置网页标题，以及使用宽屏模式
st.set_page_config(
    page_title="AUTOCHECK",
    layout="wide"

)
#放气球
if 'first_visit' not in st.session_state:
    st.session_state.first_visit=True
    #此处可初始化全局变量
    st.balloons()
# 隐藏右边的菜单以及页脚
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
# 左边导航栏
sidebar = st.sidebar.radio(
    "导航栏",
    ("监控系统告警处理", "ETOPS检测")
)
#告警超时检测
class analyze:
    def __init__(self,source_file):
        self.source_file = source_file

    def warning_analyze(self):
        df=pd.read_excel(source_file)
        df.dropna(subset=['机型', '席位信息'], inplace=True)
        df['响应时间']=pd.to_numeric(df['响应时间'],errors='coerce')
        df['日期小时'] = df['事件时间'].str[:18]
        df.groupby(['航班号', '机号', '机型', '起飞机场', '目的机场', '异常类型', '日期小时']).apply(lambda x:x.sort_values('响应时间',ascending=True))

        df.drop_duplicates(subset=['航班号', '机号', '机型', '起飞机场', '目的机场', '异常类型', '日期小时'], keep='first', inplace=True)
        df.drop('日期小时', axis=1, inplace=True)

        df_filtered = df[df['响应时间'] >= 300]
        df_filtered = df_filtered[~((df_filtered['航班号'].str[:3] == 'CAO') | (df_filtered['航班号'].str[:4] == 'CCA0'))]
        return df_filtered
#etops检测
class EtopsChecker:
    def __init__(self, date,st):
        self.start_date = date[:8]
        self.end_date = date[8:]
        self.st=st
        self.form = {}
        self.check_form = []

    def get_flt(self):
        hea = {'Host': '10.10.102.102', 'Connection': 'keep-alive', 'Content-Length': '128', 'Cache-Control': 'max-age,0',
               'Origin': 'http://10.10.102.102', 'Upgrade-Insecure-Requests': '1', 'Content-Type': 'application/x-www-form-urlencoded',
               'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36',
               'Accept': 'text/html,application/xhtml+xml,application/xml;q,0.9,image/webp,image/apng,*/*;q,0.8,application/signed-exchange;v,b3',
               'Referer': 'http://10.10.102.102/oracle/busi_his_flt_query.asp', 'Accept-Encoding': 'gzip, deflate',
               'Accept-Language': 'zh-CN,zh;q,0.9', 'Cookie': 'ASPSESSIONIDSAQRAASA,HOGBDMCDPEJBJHODCPMDADNI; ASPSESSIONIDSAQTBASA,FEHPNLHDCGEPPOPNBMPMBGCB; ASPSESSIONIDQAQRABTA,DJBKIIPDOOLGMKLKDIPIFGNP'
               }
        url = 'http://10.10.102.102/oracle/etops_check.asp'
        form = [('from_date', self.start_date), ('END_date', self.end_date), ('flt', ''),
                ('B1', '')]
        r = requests.post(url, headers=hea, data=form, timeout=5)
        r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'html.parser')
        data = soup.find('table', bgcolor='#ACDEA4')
        list_ = data.find_all('a')
        datalist = []
        for l in list_:
            if 'etops_FLT_ID' in l['href']:
                datalist.append('http://10.10.102.102/oracle/' + l['href'])
        return datalist

    def check_(self, datalist):
        check_result = []
        self.n = 0  # 百分比分子
        progress_bar=self.st.progress(0)
        for k, v in self.form.items():
            url = 'http://10.10.102.102/oracle/etops_FLT_ID_click.asp?GLOBAL_PK=' + k + '&FLT_PK=' + v
            response = requests.get(url, timeout=60)  # 超时设置为10秒
            response.encoding = 'GBK'
            html_str = response.text
            soup = BeautifulSoup(response.text, 'html.parser')
            t = soup.find_all('td')
            for i in range(len(t)):
                if '应发时间' in t[i].text:
                    t1 = re.search(r"应发时间：(\d{4}-\d{1,2}-\d{1,2}\s\d{1,2}:\d{1,2}:\d{1,2})", t[i].text).group()[5:]
                    t1_ = time.strptime(t1, "%Y-%m-%d %H:%M:%S")
                    try:
                        t2 = re.search(r"实发时间：(\d{4}-\d{1,2}-\d{1,2}\s\d{1,2}:\d{1,2}:\d{1,2})", t[i].text).group()[5:]
                        t2_ = time.strptime(t1, "%Y-%m-%d %H:%M:%S")
                    except:
                        if t1_ <= time.localtime():
                            check_result.append(url)
                            self.st.write(v + 'FAULT')
                        else:
                            self.st.write(v + '未完成')
                        break

                elif bool('Image53.gif' in html_str):
                    check_result.append(url)
                    self.st.write(v + 'FAULT')
                    break
                else:
                    continue
            # 显示百分比
            self.n = self.n + 1
            percent = round(float(self.n)/float(len(self.form)),2)
            progress_bar.progress(percent)
        progress_bar.progress(100)
        return check_result

    def run(self):
        datalist = self.get_flt()
        for d in datalist:
            key = re.findall(r'GLOBAL_PK=(\d*)', d)[0]
            value = re.findall(r'flt_id=(\d*)', d)[0]
            # 删除货航航班
            if value[:2] == '10' and len(value) == 4:
                continue
            else:
                self.form[key] = value
        self.check_form = self.check_(datalist)
        self.st.write('------过滤货航航班后该时间段共计' + str(len(self.form)) + '班------')
        if len(self.check_form) != 0:
            self.st.write('------问题网络地址详见------')
            for c in self.check_form:
                self.st.write(c)
        else:
            self.st.write('------该时间段内ETOPS天气发送正常------') 


if sidebar == "监控系统告警处理":
    st.header("监控系统告警")
    st.write("上传需要检测的告警excel")
    source_file = st.file_uploader("上传文件：", key="source_file")
    if st.button('生成处理结果', key="generate_result"):
        if source_file:
            with st.spinner('正在处理数据，请稍等...'):
                warning=analyze(source_file)
                warnresult=warning.warning_analyze()
                st.write(warnresult)
                st.write('注意切换左侧导航栏会清空数据，请及时处理数据')
        else:
            st.write('未检测到需要处理的文件')

if sidebar == "ETOPS检测":
    st.header("ETOPS")
    st.write('请确保可访问钛金世界')
    input_date = st.text_input("请输入ETOPS检查日期：（例2023041920230519）", key="input_date")
    if st.button('检测etops', key="check_etops"):
        if input_date and len(input_date)==16 and int(input_date[:8])<=int(input_date[8:]):
            etops=EtopsChecker(input_date,st)
            etopsresult=etops.run()
            st.write('注意切换左侧导航栏会清空数据，请及时处理数据')
        else:
            st.write('请检查输入日期')
