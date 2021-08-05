# -*- coding:UTF-8 -*-
import random

import pymongo
from selenium import webdriver
from selenium.webdriver import ChromeOptions
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from pyquery import PyQuery as pq
from urllib.parse import quote
from selenium.webdriver import ActionChains
import time
from lxml import etree

KEYWORD = input('请输入你要搜索的商品：')
sta = input('请输入开始的页数：')
ove = int(input('请输入结束的页数：'))

prefs = {"": ""}
option = ChromeOptions()
option.add_experimental_option('excludeSwitches', ['enable-automation'])
prefs["credentials_enable_service"] = False
prefs["profile.password_manager_enabled"] = False
option.add_experimental_option('prefs', prefs)  # 关掉密码弹窗
# option.add_argument('headless')  # 无界面启动
browser = webdriver.Chrome(options=option)
browser.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": '''
            Object.defineProperty(navigator, 'webdriver', {
              get: () => undefined
            })
          '''
        })
browser.maximize_window()
wait = WebDriverWait(browser, 10)
'''建议设置时长30s以上'''

MONGO_URL = 'localhost'  # 地址
MONGO_DB = 'taobao' # 数据库名
MONGO_COLLECTION = KEYWORD
client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]


def index_page(page):
    """
    抓取索引页
    :param page: 页码
    """
    print('正在爬取第', page, '页')
    try:
        url = 'https://s.taobao.com/search?q=' + quote(KEYWORD)
        browser.get(url)
        if page == 1:
            html = browser.page_source  # 获取源码
            doc = etree.HTML(html)
            a = doc.xpath("//div[contains(@class,'login-blocks')]/a[@class='password-login-tab-item']/text()")
            # print(a)
            if len(a) > 0:
                name = browser.find_element_by_name("fm-login-id")
                name.clear()
                name.send_keys('username')
                passwd =browser.find_element_by_name("fm-login-password")
                passwd.clear()
                passwd.send_keys('password')
                button = browser.find_element_by_class_name('fm-button')
                button.click()
            time.sleep(5)
            get_block()
            wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '#mainsrp-pager li.item.active > span'),str(page)))  # 判断页数是否相等，返回true/false
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.m-itemlist .items .item')))  # 信息块
            # print('成功！！！！！！！！！！！！！！')
            get_products()
        if page > 1:  # 页数大于1就要模拟点击选择页数。
            get_block()
            input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager div.form > input')))
            submit = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#mainsrp-pager div.form > span.btn.J_Submit')))
            input.clear()
            input.send_keys(page)
            time.sleep(5)
            submit.click()
            wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '#mainsrp-pager li.item.active > span'), str(page)))  # 判断页数是否相等，返回true/false
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.m-itemlist .items .item')))  # 信息块
            # print('成功！！！！！！！！！！！！！！')
            get_products()
    except TimeoutException:
        index_page(page)


def get_block():
    """
    过滑块
    :return:
    """
    time.sleep(0.3)
    html = browser.page_source
    doc = etree.HTML(html)
    w = doc.xpath("//div[@class='captcha-tips']/div/text()")
    if w:
        # 移动轨迹
        track = []
        # 当前位移
        current = 0
        # 减速阈值
        mid = 150
        # 计算间隔
        t = 0.2
        # 初速度
        v = 0

        while current < 300:
            if current < mid:
                # 加速度为正2
                a = 3
            else:
                # 加速度为3
                a = random.choice([-2, 3])
            # 初速度v0
            v0 = v
            # 当前速度v = v0 + at
            v = v0 + a * t
            # 移动距离x = v0t + 1/2 * a * t^2
            move = v0 * t + 1 / 2 * a * t * t
            # 当前位移
            current += move
            # 加入轨迹
            track.append(round(move))  # 浮点数四舍五入
        slide = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'nc_iconfont')))
        ActionChains(browser).click_and_hold(slide).perform()
        time.sleep(0.2)
        for x in track:
            ActionChains(browser).move_by_offset(xoffset=x, yoffset=0).perform()
        time.sleep(0.5)
        ActionChains(browser).release().perform()  # 释放
    time.sleep(5)


def get_products():
    """
    提取商品数据
    """
    html = browser.page_source  # 获取源码
    doc = pq(html)
    items = doc('#mainsrp-itemlist .items .item').items()
    # print(items)
    for item in items:
        product = {
            'image': item.find('.pic .img').attr('data-src'),
            'price': item.find('.price').text(),
            'deal': item.find('.deal-cnt').text(),
            'title': item.find('.title').text(),
            'shop': item.find('.shop').text(),
            'location': item.find('.location').text()
        }
        print(product)
        save_to_mongo(product)

def save_to_mongo(result):
    """
    保存至MongoDB
    :param result: 结果
    """
    try:
        if db[MONGO_COLLECTION].insert(result):
            print('存储到MongoDB成功')
    except Exception:
        print('存储到MongoDB失败')


def main():
    """
    遍历每一页
    """
    for i in range(int(sta), ove+1):
        index_page(i)
    browser.close()


if __name__ == '__main__':
    main()


