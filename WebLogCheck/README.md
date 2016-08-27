# WebLogCheck
WebLogCheck是一个自动化的web登录猜解工具，它访问给定的url链接并从响应结果中自动提取登录过程的form action及相关参数，并使用指定的用户名、密码进行登录尝试。它非常适合某些应用每次登录过程需要特定生成参数值的情况，以及某些.Net web应用登录过程，当前版本无法破解包含验证码登录过程。使用方法：

    Usages: WebLogCheck.py -t http://target.com/login.htm -u user.txt -p pass.txt
