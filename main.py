#! /usr/bin/env python3

import re
import os
import json
import time
import base64
import ddddocr
import requests
import pandas as pd
from PIL import Image
from io import BytesIO
from config import config
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


# base64图片处理
def base64_to_image(base64_str):
    base64_data = re.sub('^data:image/.+;base64,', '', base64_str)
    byte_data = base64.b64decode(base64_data)
    image_data = BytesIO(byte_data)
    img = Image.open(image_data)
    return img


# 添加学生信息
def add_info(noStudyList, studentsInfo, class_name, is_Study='否'):
    for studentInfo in studentsInfo:
        if studentInfo['isStudy'] == is_Study:
            noStudyList.append(
                {'class_name': class_name,
                 'real_name': studentInfo['realname'],
                 'isStudy': studentInfo['isStudy']})


# 将json数据转为Excel
def creat_excel():
    print("开始生成Excel...")
    dataList = pd.read_json("jsonData/noStudyInfo.json")
    if not os.path.exists('Excel'):
        os.makedirs('Excel')
    date = time.strftime("Excel/%Y年%m月%d日", time.localtime())
    writer = pd.ExcelWriter(date + '未完成学习名单.xlsx', engine='xlsxwriter')
    dataList.index.name = '编号'
    dataList.index = dataList.index + 1
    dataList.rename(columns={'class_name': '班级名称', 'real_name': '姓名', 'isStudy': '是否完成学习'}, inplace=True)
    dataList.to_excel(writer, sheet_name='Sheet1')
    workbook = writer.book
    worksheet = writer.sheets['Sheet1']
    cell_format = workbook.add_format({'border': 1, 'align': 'center'})
    worksheet.set_column(0, 0, cell_format=cell_format)
    for i, col in enumerate(dataList.columns):
        max_len = max((dataList[col].astype(str).map(len).max(), len(str(dataList[col].name)))) + 30
        worksheet.set_column(i + 1, i + 1, max_len, cell_format=cell_format)
    writer.save()
    print("Excel生成完成...")


class GetNoStudyStudents(object):

    def __init__(self):
        print("开始启动服务...")
        # 启动自动化浏览器
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=config.options)
        self.driver.get(config.configs['url']['login_url'])

    def login(self):
        # 尝试登录
        if config.configs['loginCount'] > 0:
            config.configs['loginCount'] -= 1
            try:
                print("开始获取验证码...")
                verify_src = self.driver.find_element(By.CLASS_NAME, 'login-img').get_attribute('src')
                verify_img = base64_to_image(verify_src)
                # 获取验证码资源并保存本地
                if not os.path.exists('verify'):
                    os.makedirs('verify')
                verify_img.save('verify/verify_img.png')
                # 验证码orc识别
                print("开始自动识别验证码...")
                ocr = ddddocr.DdddOcr(show_ad=False, old=True)
                with open("verify/verify_img.png", 'rb') as png:
                    image = png.read()
                verify_code = ocr.classification(image)
                print("开始自动登录...")

                # 表单填充
                self.driver.find_element(By.NAME, "emial").send_keys(config.configs['user']['username'])
                self.driver.find_element(By.NAME, "password").send_keys(config.configs['user']['password'])
                self.driver.find_element(By.NAME, "verify").send_keys(verify_code)
                self.driver.find_element(By.TAG_NAME, "button").click()
                WebDriverWait(self.driver, 5).until(
                    lambda is_login: self.driver.current_url == config.configs['url']['desired_url'],
                    message="ORC跑路了，再次尝试登录...")
            except Exception as e:
                print(e)
                self.driver.refresh()
                self.login()
        else:
            print("请检查帐号密码及网络后重新启动...")
            self.driver.quit()
            exit()

    @property
    def get_token(self):
        print("开始记录登录信息...")
        cookie = self.driver.get_cookies()
        # 判断token是否正常获取
        if cookie[0]['name'] != 'token':
            print("token获取失败，请稍候重新启动...")
            self.driver.quit()
            exit()
        self.driver.quit()
        return cookie[0]['value']

    # 信息处理
    def get_info(self):
        token = self.get_token
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'zh-CN,zh;q=0.9',
            'token': token,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/101.0.4951.54 Safari/537.36',
        }
        # session请求持久化
        session = requests.session()
        session.adapters.DEFAULT_RETRIES = 5

        # 获取组织信息
        print("开始获取组织信息...")
        Organize = session.get(url="组织信息接口", headers=headers,
                               timeout=10)
        OrganizeInfo = json.loads(Organize.text)
        OrganizeId = str(OrganizeInfo['data']['id'])

        print("开始获取支部班级信息...")
        classInfo = session.get(url="支部信息接口",
                                headers=headers, timeout=10)

        # 建立未学习名单
        noStudyList = []
        for classInfo in json.loads(classInfo.text)['data']:
            print("开始处理" + classInfo['name'] + "信息...")
            # 获取团员信息
            regimentInfo = session.get(
                url="团员信息接口" +
                    str(classInfo['id']),
                headers=headers
            )
            regimentInfo = regimentInfo.json()
            add_info(noStudyList, regimentInfo['data']['data'], classInfo['name'])

            # 获取青年信息
            youngInfo = session.get(
                url="青年信息接口",
                headers=headers
            )
            youngInfo = youngInfo.json()
            add_info(noStudyList, youngInfo['data']['data'], classInfo['name'])

        print("开始数据持久化...")
        noStudyInfo = json.dumps(noStudyList, ensure_ascii=False)
        if not os.path.exists('jsonData'):
            os.makedirs('jsonData')
        with open('jsonData/noStudyInfo.json', 'w', encoding="utf-8") as f:
            f.write(noStudyInfo)


if __name__ == "__main__":
    # 开始时间
    start_time = time.time()
    noStudyStudents = GetNoStudyStudents()
    noStudyStudents.login()
    noStudyStudents.get_info()
    creat_excel()
    end_time = time.time()
    print("数据处理完成！耗时: {:.2f}秒".format(end_time - start_time))
