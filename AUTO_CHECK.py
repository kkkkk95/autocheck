import streamlit as st
import pandas as pd
from openpyxl import load_workbook
import requests
from bs4 import BeautifulSoup
import time
import sys
import re
import datetime
import os
import base64
import json

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
    ("监控系统告警处理", "ETOPS检测","SIGMET")
)
# 初始化全局配置
if 'first_visit' not in st.session_state:
    st.session_state.first_visit=True
    st.balloons()
    st.etopsdate=datetime.datetime.now().strftime('%Y%m%d')+'-'+datetime.datetime.now().strftime('%Y%m%d')
    st.sigmetdata=pd.DataFrame(columns=['地名代码', '情报区', '天气现象', '观测或预测的位置', '高度', '移动', '强度趋势'])
    st.valid_num=0
    st.cnl_num=0
    st.invalid_num=0
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
        df_filtered = df_filtered[~((df_filtered['航班号'].str[:3] == 'CAO') | (df_filtered['航班号'].str[:4] == 'CCA0')| (df_filtered['航班号'].str[:3] == 'CCD'))]
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
#除冰
class antice:
    def __init__(self):
        self.iniaddr=os.path.abspath(r'configs.ini')
        self.chromeaddr=os.path.abspath(r'chrome.exe')
        self.do = ChromiumOptions(read_file=False).set_paths(local_port='9888',
                                                browser_path=self.chromeaddr)
        self.page = WebPage(driver_or_options=do, session_or_options=False)
        self.imgaddr=os.path.abspath(r'验证码/img.png')
        
    
    def login(self):
        # 登录
        # 定位到账号
        self.page.ele('#userInput').input('15201235424')
        # 定位到密码
        self.page.ele('#passwordInput').input('AOCdtjk2023')
        # 定位验证码图片
        img = self.page('tag:img').get_src()
        with open (self.imgaddr, "wb") as f:
            f.write(img)
        with open(self.imgaddr, 'rb') as f:
            img_bytes = f.read()
            result = DdddOcr().classification(img_bytes)
        # 输入验证码
        self.page.ele('#captchaData').input(result)
        # 点击登录按钮
        self.page.ele('#doLoginButton').click()


    def fix_pos(self,key):
        self.page.ele(".col-md-4 col-xs-4 col-sm-4 col-lg-4    no-pad-list list-more-label  sjx-sx-list-Box click-status").click()
        if self.page.ele(".list-select-content").wait.display():
            self.page.eles(".select-label select-label-desc-more")[7].after().click()
            if self.page.ele("#deicingFlag").wait.display():
                self.page.ele(".select-checked-show-t").after().click()
                if self.page.ele(".list-select-content").wait.display():
                    if key==0:
                        self.page.eles(".select-label select-label-desc")[0].after().click()
                    else:
                        self.page.eles(".select-label select-label-desc")[1].after().click()
    def narrow_wide(self,key):
        self.page.ele("@name=typeCategory").click()
        if self.page.ele(".list-select-content").wait.display():
            if key==0:
                self.page.eles(".select-label select-label-desc")[0].after().click()
                self.page.eles(".select-label select-label-desc")[1].after().click()
                self.page.eles(".select-label select-label-desc")[2].after().click()
            else:
                self.page.eles(".select-label select-label-desc")[3].after().click()
                self.page.eles(".select-label select-label-desc")[4].after().click()
    def get_result(self):
        time.sleep(6)
        data_list=self.page.ele("#warning-table-b").texts()
        # 清理原始数据列表中的字符串
        cleaned_data = [re.sub(r'\s+', ' ', item).strip() for item in data_list]
        data=cleaned_data[0].split()
        # 总数初始化计数器
        count_all = 0
        # 获取航班号到上站的列索引范围
        start_index = data.index('航班号')
        end_index = data.index('上站')+1
        # 遍历每一行的数据
        for i in data[start_index:end_index]:
            # 尝试将元素转换为整数
            try:
                int_value = int(i)
                count_all += 1
            except ValueError:
                pass
        #待除冰
        current_time = datetime.datetime.now()
        # 初始化计数器
        count = 0
        timelist=self.page.eles(".datagrid-cell datagrid-cell-c5-dCldrDttm")
        # 遍历列表中的每个元素
        for t in timelist:
            # 使用正则表达式进行匹配
            t=t.text[-5:]
            try:
                hour=int(t[0:2])
            except:
                hour=0
            try:
                minute=int(t[3:])
            except:
                minute=0
            # 构造日期对象，将当前时间的年、月、日与提取的小时和分钟组合
            element_time = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # 计算当前时间与提取的时间之间的差值（以分钟为单位）
            time_diff = (current_time - element_time).total_seconds() / 60

            # 如果差值的绝对值小于等于10，则将计数器加1
            if abs(time_diff) <= 10:
                count += 1
        return count_all,count
    def main(self):
        url='https://acdm.bcia.com.cn/login.do'
        self.page.get(url)
        self.login()
        while True:
            if self.page.ele('航班动态'):
                break
            elif self.page.ele('#userInput'):
                self.login()
            else:
                pass
        line={}
        while True:
            if self.page.ele('航班动态'):
                self.page.ele('监控预警').click()
                if self.page.ele("#datagrid-row-r1-1-0"):
                    #进出港
                    self.page.ele("@name=aord").click()
                    if self.page.ele(".list-select-content").wait.display():
                        self.page.eles(".select-label select-label-desc")[2].after().click()
                    #CA
                    self.page.ele(".list-input-serach index-value list-input-serach-s toUp").input('CA') 
                    #标记除冰航班 定点0；机位1
                    self.fix_pos(0)
                    #款窄体 窄体0；宽体1
                    self.narrow_wide(0)
                    self.page.ele("#list-search-btn-c").click()
                    line['fix_narrow']=self.get_result()
                    break
            else:
                continue
        self.page.refresh()
        while True:
            if self.page.ele('航班动态'):
                self.page.ele('监控预警').click()
                if self.page.ele("#datagrid-row-r1-1-0"):
                    #进出港
                    self.page.ele("@name=aord").click()
                    if self.page.ele(".list-select-content").wait.display():
                        self.page.eles(".select-label select-label-desc")[2].after().click()
                    #CA
                    self.page.ele(".list-input-serach index-value list-input-serach-s toUp").input('CA') 
                    #标记除冰航班 定点0；机位1
                    self.fix_pos(0)
                    #款窄体 窄体0；宽体1
                    self.narrow_wide(1)
                    self.page.ele("#list-search-btn-c").click()
                    line['fix_wide']=self.get_result()
                    break
            else:
                continue
        self.page.refresh()
        while True:
            if self.page.ele('航班动态'):
                self.page.ele('监控预警').click()
                if self.page.ele("#datagrid-row-r1-1-0"):
                    #进出港
                    self.page.ele("@name=aord").click()
                    if self.page.ele(".list-select-content").wait.display():
                        self.page.eles(".select-label select-label-desc")[2].after().click()
                    #CA
                    self.page.ele(".list-input-serach index-value list-input-serach-s toUp").input('CA') 
                    #标记除冰航班 定点0；机位1
                    self.fix_pos(1)
                    #款窄体 窄体0；宽体1
                    self.narrow_wide(0)
                    self.page.ele("#list-search-btn-c").click()
                    line['pos_narrow']=self.get_result()
                    break
            else:
                continue
        self.page.refresh()
        while True:
            if self.page.ele('航班动态'):
                self.page.ele('监控预警').click()
                if self.page.ele("#datagrid-row-r1-1-0"):
                    #进出港
                    self.page.ele("@name=aord").click()
                    if self.page.ele(".list-select-content").wait.display():
                        self.page.eles(".select-label select-label-desc")[2].after().click()
                    #CA
                    self.page.ele(".list-input-serach index-value list-input-serach-s toUp").input('CA') 
                    #标记除冰航班 定点0；机位1
                    self.fix_pos(1)
                    #款窄体 窄体0；宽体1
                    self.narrow_wide(1)
                    self.page.ele("#list-search-btn-c").click()
                    line['pos_wide']=self.get_result()
                    break
            else:
                continue
        # 获取当前时间的小时部分
        current_hour = datetime.datetime.now().hour
        data=line
        # 构建句子
        sentence = "截至{}点，首都机场国航已完成除霜{}架，其中宽体{}架，窄体{}架，后续XX架待除。".format(
            current_hour,
            data['fix_narrow'][0]+data['fix_wide'][0]+data['pos_narrow'][0]+data['pos_wide'][0],
            data['fix_wide'][0]+data['pos_wide'][0],
            data['fix_narrow'][0]+data['pos_narrow'][0]
        )
        self.page.quit()
        return line,sentence
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


class sigmet:
    def __init__(self,data,sig,type):
        self.data=data
        self.sig=sig
        self.type=type
        self.new_df=pd.DataFrame(columns=['气象监视台', '情报区', '最低高度','最高高度', '移动', '强度趋势'])
    def fanyi(self):
        pass
    def fenlei(self,sigmet_text):
        parts = []
        if 'CNL' in sigmet_text:
            parts.append('取消报')
        else:
            # 使用正则表达式提取报文中的信息
            try:
                #地名代码
                diming=re.findall(r'([A-Z]{4}(?=\sSIGMET))',sigmet_text)
                if diming!=[]:
                    diming=diming[0]
                else:
                    diming=None
                #情报区或管制区
                fir_pattern = r'([A-Z]{4})[-\s]+([A-Z]{4})\s+(.*\s+FIR)'
                match = re.search(fir_pattern, sigmet_text)
                if match:
                    survwx = match.group(1)
                    fir_code = match.group(2)
                    fir_name=match.group(3)
                #高度
                height_high=height_low=None
                # 匹配 "SFC/4000" 和 "SFC/3000" 格式
                match = re.search(r'SFC/(\d+)', sigmet_text)
                if match:
                    height_low=0
                    height_high=int(match.group(1))
                # 匹配 "SFC/FL4000"格式
                match = re.search(r'SFC/FL(\d+)', sigmet_text)
                if match:
                    height_low=0
                    height_high=int(match.group(1))
                
                # 匹配 "SFC/FL4000" 和 "SFC/3000FT" 格式
                match = re.search(r'SFC/FL(\d+)', sigmet_text)
                if match:
                    height_low=0
                    height_high=int(match.group(1))
                
                # 匹配 "FL 180/290"、"FL 130/330"、"FL 300/400" 和 "FL 270/360" 格式
                match = re.search(r'FL (\d+)/(\d+)', sigmet_text)
                if match:
                    height_low=int(match.group(1))
                    height_high=int(match.group(2))
                # 匹配 "FL180/290"格式
                match = re.search(r'FL(\d+)/(\d+)', sigmet_text)
                if match:
                    height_low=int(match.group(1))
                    height_high=int(match.group(2))
                # 匹配 "TOP FL350" 格式
                match = re.search(r'TOP FL(\d+)', sigmet_text)
                if match:
                    height_low=None
                    height_high=int(match.group(1))

                #移动变化
                m=re.findall(r'(MOV\s(.*?)\s(?=INTSF|WKN|NC)|STNR)',sigmet_text)
                if m!=[]:
                    m=m[0]
                    move=m[0]+' '+m[1]
                else:
                    move=None
                
                #强度变化
                change=re.findall(r'(INTSF|WKN|NC)',sigmet_text)
                if change!=[]:
                    change=change[0]
                else:
                    change=None
                
                #txt格式（天气现象待修正）
                if self.type==1:
                    #天气现象描述
                    wx=re.findall(r'FIR\s(.*?)\s(?=OBS|FCST)',sigmet_text)[0]
                    #观测或预报的位置
                    p=re.findall(r'((OBS|FCST)(.*?)(?=SFC|FL|TOP|ABV|BLW)|CENTRE PSN.*)',sigmet_text)[0]
                    pos=p[0]+p[1]
                    if pos[-1]=='/':
                        pos=pos[:pos.rfind(' ')]  # 找到最后一个空格的位置，并截取字符串
                    if pos[-1]=='=':
                        pos=pos[:-1]  # 去除等于号
                    parts.append([diming,fir_code,fir_name,wx,pos,height_low,height_high,move,change,])
                else:
                    return [survwx,fir_name,height_low,height_high,move,change,]
            except:
                parts.append(sigmet_text+'存在错误字符')
        return parts
    def anay(self):
        #st.write(self.dataall)
        for d in self.dataall:
            d=str(d)
            result=sig2.fenlei(d)[0]
            results.append(result)
        for r in results:
            if r=='取消报':
                st.cnl_num=st.cnl_num+1
                continue
            elif '存在错误字符' in r:
                st.invalid_num=st.invalid_num+1
                continue
            else:
                st.valid_num=st.valid_num+1
                if type==1:
                    st.sigmetdata = pd.concat([st.sigmetdata, pd.DataFrame([r], columns=st.sigmetdata.columns)])
                else:
                    st.sigmetdata = sig2.data
                continue
        

    def to_data(self):
        if self.type==1:
            data = self.data
            # 获取文件内容的字节流
            bytes_data = data.getvalue()

            # 将字节流解码为字符串
            data = bytes_data.decode("utf-8")

            # 使用正则表达式找出所有符合条件的字符串
            pattern = r'[A-Z]{4}\s+SIGMET\s*.*='
            result = re.findall(pattern, data)
            #取出txt中所有segmet报文
            self.dataall=result
            self.anay()
            st.write('此数据有可用数据{}个，取消报{}个，错误数据{}个'.format(st.valid_num,st.cnl_num,st.invalid_num))
            st.write(st.sigmetdata)
        #[fir_code,fir_name,height_low,height_high,move,change,]
        elif self.type==2:
            # 创建进度条
            progress_bar = st.progress(0)
            # 删除"cnl"列不为空的行
            self.data = self.data[self.data['cnl'].isna()]
            # 保留指定的列
            self.data = self.data[['fir_code', 'msg_type', 'wphenomenon', 'start_time', 'raw_message', 'polygon_details']]
            # 提取"polygon_details"列中的"polygonCore"数据
            self.data['lat'] = self.data['polygon_details'].apply(lambda x: round(json.loads(x)[0]['polygonCore'][0], 2) if pd.notna(x) and isinstance(x, str) and len(json.loads(x)) > 0 else None)
            self.data['lon'] = self.data['polygon_details'].apply(lambda x: round(json.loads(x)[0]['polygonCore'][1], 2) if pd.notna(x) and isinstance(x, str) and len(json.loads(x)) > 0 else None)
            # 每行的数据处理
            for index,row in self.data.iterrows():
                sigmet_text=row['raw_message']
                new_data=self.fenlei(sigmet_text)
                if len(new_data)==6:
                    new_row = pd.DataFrame({'地名代码': row['fir_code'], '气象监视台': new_data[0], '情报区': new_data[1], '报文类型': row['msg_type'], '天气现象': row['wphenomenon'], '开始时间': row['start_time'],
                                            '纬度': row['lat'], '经度': row['lon'], '最低高度': new_data[2], '最高高度': new_data[3], '移动': new_data[4], '强度趋势': new_data[5], '原始报文': row['raw_message']}, index=[0])
                
                    st.sigmetdata_csv = pd.concat([st.sigmetdata_csv, new_row], ignore_index=True)
                    # 更新进度条
                    progress_bar.progress(min((index + 1) / len(self.data), 1))
                else:
                    continue
            # 进度条完成
            progress_bar.progress(100)
            st.write(st.sigmetdata_csv)

        else:
            pass

def download_button(file_path, button_text):
    with open(os.path.abspath(file_path), 'rb') as f:
        bytes = f.read()
        b64 = base64.b64encode(bytes).decode()

    # 创建一个名为 "Download File" 的下载链接
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{os.path.basename(file_path)}">{button_text}</a>'

    # 在 Streamlit 应用程序中使用按钮链接
    st.markdown(f'<div class="button-container">{href}</div>', unsafe_allow_html=True)

    # 添加 CSS 样式以将链接样式化为按钮
    st.markdown("""
        <style>
        .button-container {
            display: inline-block;
            margin-top: 1em;
        }
        .button-container a {
            background-color: #0072C6;
            border: none;
            color: white;
            padding: 0.5em 1em;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 16px;
            font-weight: bold;
            border-radius: 4px;
            cursor: pointer;
        }
        .button-container a:hover {
            background-color: #005AA3;
        }
        </style>
    """, unsafe_allow_html=True)


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

if sidebar == "SIGMET":
    st.header("SIGMET数据处理")
    st.write("单一数据预览")
    sigmet_input=st.text_input("请输入sigmet报文：")
    if st.button('数据写入', key="sigmetwritein"):
        if sigmet_input=='':
            st.warning('数据为空')
        else:
            sig1=sigmet('',sigmet_input)
            result=sig1.fenlei(sigmet_input)[0]
            st.sigmetdata = pd.concat([st.sigmetdata, pd.DataFrame([result], columns=st.sigmetdata.columns)])
            st.write(st.sigmetdata)
    st.write("上传数据相关TXT/CSV")
    sigmet_file = st.file_uploader("上传文件：", key="source_file")
    
    results=[]
    
    if st.button('数据上传', key="sigmetupload"):
        if sigmet_file:
            with st.spinner('正在处理数据，请稍等...'):
                # 检测文件格式
                if sigmet_file.name.endswith('.txt'):
                    data = sigmet_file.getvalue().decode("utf-8")
                    type=1
                    sig2=sigmet(sigmet_file,'',type)
                    sig2.to_data()
                    
                elif sigmet_file.name.endswith('.csv'):
                    df = pd.read_csv(sigmet_file)
                    sigmet_file=df
                    type=2
                    sig2=sigmet(sigmet_file,'',type)
                    sig2.to_data()
                else:
                    st.warning('不支持的文件格式。请提供TXT或CSV文件。')
                
        else:
            st.write('未检测到需要处理的文件')
    left_column,right_column=st.columns(2)
    with left_column:
        if st.button('清空数据', key="Delete"):
            st.valid_num=0
            st.cnl_num=0
            st.invalid_num=0
            st.sigmetdata=pd.DataFrame(columns=['地名代码','气象监视台', '情报区', '天气现象', '观测或预测的位置', '最低高度','最高高度', '移动', '强度趋势'])
            st.sigmetdata_csv=pd.DataFrame(columns=['地名代码','气象监视台', '情报区','报文类型', '天气现象', '开始时间','纬度','经度','最低高度','最高高度', '移动', '强度趋势','原始报文'])
    with right_column:
        if st.sigmetdata is not None:
            st.sigmetdata.to_excel(os.path.abspath(r'data.xlsx'), index=False)
            download_button(os.path.abspath(r'data.xlsx'), '下载当前添加的所有数据')
        elif st.sigmetdata_csv is not None:
            st.sigmetdata_csv.to_excel(os.path.abspath(r'data.xlsx'), index=False)
            download_button(os.path.abspath(r'data.xlsx'), '下载当前添加的所有数据')
        else:
            st.write('--waiting update--')
