import streamlit as st
import pandas as pd
from openpyxl import load_workbook
import requests
from bs4 import BeautifulSoup
import time
import sys
import re
import datetime

# 设置网页标题，以及使用宽屏模式
st.set_page_config(
    page_title="AUTOCHECK",
    layout="wide"

)
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
# 初始化全局配置
if 'first_visit' not in st.session_state:
    st.session_state.first_visit=True
    st.balloons()
    st.etopsdate=datetime.datetime.now().strftime('%Y%m%d')+'-'+datetime.datetime.now().strftime('%Y%m%d')
#告警超时检测
class analyze:
    def __init__(self,source_file):
        self.source_file = source_file

    def warning_analyze(self):
        self.df=pd.read_excel(source_file)
        self.df.dropna(subset=['机型'], inplace=True)
        self.df['响应时间']=pd.to_numeric(self.df['响应时间'],errors='coerce')
        self.df['日期小时'] = self.df['事件时间'].str[:18]
        self.df.groupby(['航班号', '机号', '机型', '起飞机场', '目的机场', '异常类型', '日期小时']).apply(lambda x:x.sort_values('响应时间',ascending=True))

        self.df.drop_duplicates(subset=['航班号', '机号', '机型', '起飞机场', '目的机场', '异常类型', '日期小时'], keep='first', inplace=True)
        self.df.drop('日期小时', axis=1, inplace=True)
    def outtime(self):
        self.warning_analyze()
        df_filtered = self.df[self.df['响应时间'] >= 300]
        df_filtered = df_filtered[~((df_filtered['航班号'].str[:3] == 'CAO') | (df_filtered['航班号'].str[:4] == 'CCA0'))]
        return df_filtered
    def outline(self):
        self.warning_analyze()
        deviation_wxnum=0
        deviation_atcnum=0
        circle_wxnum=0
        circle_atcnum=0
        go_aroundnum=0
        go_aroundline=''
        alt_num=0
        altline=''
        for row in self.df.iterrows():
            dataline=row[1]
            rmk=str(dataline['备注'])
            if dataline['异常类型']=='偏航告警':
                if '管制指挥' in rmk:
                    deviation_atcnum+=1
                if '天气绕飞' in rmk:
                    deviation_wxnum+=1
            if dataline['异常类型']=='盘旋等待':
                if '管制指挥' in rmk:
                    circle_atcnum+=1
                if '天气' in rmk:
                    circle_wxnum+=1
            if dataline['异常类型']=='复飞':
                if '正在核实' in rmk:
                    pass
                elif '假告警' in rmk:
                    pass
                elif'终止进近' in rmk:
                    pass
                elif '已着陆' in rmk:
                    pass
                else:
                    go_aroundnum+=1
                    go_aroundline=go_aroundline+'{}{}在{}复飞；'.format(str(dataline['航班号'])[1:],rmk,str(dataline['目的机场']))
            if dataline['异常类型']=='备降':
                if '目的机场天气' in rmk:
                    alt_num+=1
                    altline=altline+'{}因{}(天气)备降(备降场)；'.format(str(dataline['航班号'])[1:],str(dataline['目的机场']))
                else:
                    alt_num+=1
                    altline=altline+'{}因{}备降(备降场)；'.format(str(dataline['航班号'])[1:],rmk)
            if dataline['异常类型']=='返航':
                if '目的机场天气' in dataline['备注']:
                    alt_num+=1
                    altline=altline+'{}因{}(天气)返航(备降场)；'.format(str(dataline['航班号'])[1:],str(dataline['起飞机场']))
                else:
                    alt_num+=1
                    altline=altline+'{}因{}返航(备降场)；'.format(str(dataline['航班号'])[1:],rmk)
        outline_='值班小结：偏航{}班：{}班WX，{}班ATC； 盘旋{}班：{}班WX，{}班ATC； 复飞{}班：{} 备降{}班：{}'.format(str(deviation_wxnum+deviation_atcnum)
        ,str(deviation_wxnum)
        ,str(deviation_atcnum)
        ,str(circle_wxnum+circle_atcnum)
        ,str(circle_wxnum)
        ,str(circle_atcnum)
        ,str(go_aroundnum)
        ,go_aroundline
        ,str(alt_num)
        ,altline
        )
        return outline_

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
        status_text = st.empty()
        flight_text = st.empty()
        text=''
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
                            text=text + v + 'FAULT/'
                        else:
                            text=text + v + '未完成/'
                        break

                elif bool('Image53.gif' in html_str):
                    check_result.append(url)
                    text=text + v + 'FAULT/'
                    break
                else:
                    continue
            # 显示百分比
            self.n = self.n + 1
            percent = round(float(self.n)/float(len(self.form)),4)
            progress_bar.progress(percent)
            # 更新状态文本
            status_text.markdown(
                        f"""
                        <div>
                        <div style='position:absolute; width:100%; height:100%; top:0; left:0; display:flex; align-items:center; justify-content:center; font-size:24px;'>
                        Progress: {percent*100:.2f}%
                        </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            flight_text.text(text)
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
    st.write("从国航监控系统导出告警信息管理EXCEL，上传它")
    source_file = st.file_uploader("上传文件：", key="source_file")
    if st.button('300s告警超时处理结果', key="generate_result"):
        if source_file:
            with st.spinner('正在处理数据，请稍等...'):
                warning=analyze(source_file)
                warnresult=warning.outtime()
                st.write(warnresult)
        else:
            st.write('未检测到需要处理的文件')
    st.write("-------------------------------------------------------------------------")
    if st.button('交接班内容'):
        if source_file:
            with st.spinner('正在处理数据，请稍等...'):
                warning=analyze(source_file)
                outline_=warning.outline()
                st.write(outline_)
        else:
            st.write('未检测到需要处理的文件')
    st.write("-------------------------------------------------------------------------")
    left_column, right_column = st.columns(2)
    with left_column:
        url="https://assets1.lottiefiles.com/packages/lf20_2xoRs4A4MD.json"
        r = requests.get(url)
        if r.status_code == 200:
            lottie_coding=r.json()
    with right_column:
        st.write("如果您有不错的点子或建议，使本站模块和功能更加美观丰富，请积极把您的想法告诉我！")
        st.write("@KXY 13811619564")
        st.write("感谢您的支持！")

if sidebar == "ETOPS检测":
    st.header("ETOPS(--限内网电脑打开本地文件使用--)")
    st.write("--让桌面名为etopschecker.exe程序解决你ETOPS天气发送疏忽的困扰--")
    input_date = st.text_input("请输入ETOPS检查日期：（例20230419-20230519）", key="input_date",value=st.etopsdate)
    if st.button('检测etops', key="check_etops"):
        if input_date and len(input_date)==17 and int(input_date[:8])<=int(input_date[9:]):
            input_date=input_date[:8]+input_date[9:]
            etops=EtopsChecker(input_date,st)
            etopsresult=etops.run()
        else:
            st.write('请检查输入日期')
    st.write("-------------------------------------------------------------------------")
    st.header("本地使用方法说明")
    left_column, right_column = st.columns(2)
    left_column.markdown("step1：打开开始菜单选择anaconda3(64-bit)文件夹中的任意终端")
    left_column.image(r"image/step1.png")
    right_column.markdown("step2：复制粘贴指令'streamlit run AUTO_CHECK.py'")
    right_column.image(r"image/step2.png")
    
