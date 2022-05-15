from selenium import webdriver

# 配置selenium选项信息,去掉selenium特征信息
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument("--disable-blink-features")
options.add_argument("--disable-blink-features=AutomationControlled")
# options.add_argument("--proxy-server=http://代理服务器地址:代理服务器端口号")
options.add_experimental_option("excludeSwitches", ['enable-automation'])
options.add_experimental_option("useAutomationExtension", False)

configs = {
    # 配置用户名及密码
    'user': {
        'username': '',
        'password': '',
    },
    # 配置登录失败重新尝试次数
    'loginCount': 3,
    # 定义登录链接及成功后跳转链接
    'url': {
        'login_url': '',
        'desired_url': '',
    },
}
