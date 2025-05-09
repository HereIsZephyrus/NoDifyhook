import os
from dotenv import load_dotenv
from notion_client import Client  # 导入notion_client库，终端输入"pip install notion_client"进行安装
from pprint import pprint
from datetime import datetime
import requests  # 添加requests库导入

load_dotenv()
def get_kb_list(kb_id):
    url = f'http://dify.channingtong.cn/v1/datasets/{kb_id}/documents'
    headers = {
        'Authorization': f'Bearer {os.getenv("API_KEY")}'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # 检查请求是否成功
    list = response.json()
    
    # 提取每个文档的name和created_at
    last_created_at = 0
    doc_names = []
    for doc in list['data']:
        current_created_at = int(doc['created_at'])
        if current_created_at > last_created_at:
            last_created_at = current_created_at
            doc_names.append(doc['name'])
    
    return last_created_at, doc_names

notion = Client(auth=os.getenv("CLIENT_TOKEN"))
db_name = os.getenv("DB_NAME")
db_id = os.getenv("DB_ID")
page_id = os.getenv("PAGE_ID")
startDate_timestamp, doc_names = get_kb_list(db_id)
# ednDate is current date
endDate = datetime.now().strftime("%Y-%m-%d")

db_values = notion.databases.query(
        **{
            "database_id": db_id,
            "filter" : {
                "and" : [
                    {
                    "date": {
                        "after": startDate
                    }},
                    {
                    "date": {
                    "before": endDate
                    }
                    }
                ]
            }
        }
    ).get("results")
import time
import subprocess
current_time=time.strftime("%Y%m%d_%H%M", time.localtime())
file_name = "filelist"+current_time+".txt"
dict_name=f'{current_time}_PDFs'
os.system(f'/bin/mkdir {os.getcwd()}/{dict_name}') # 创建文件夹用于存储抓取到的pdf
command_header='''/usr/bin/find '/Users/channingtong/Library/Mobile Documents/iCloud~QReader~MarginStudy/Documents' -iname ''';
with open(file_name,"w") as file:
# 整理notion中获取的数据然后获得pdf路径
    title=[]
    author=[]
    date=[]
    filename=[]
    filedict=[]
    for item in db_values:
        title.append(item["properties"]["Name"]["title"][0]["plain_text"])
        author.append(item["properties"]["Author"]["rich_text"][0]["plain_text"])
        date.append(item["properties"]["Time"]["number"])
        # 抓取第一作者的姓
        first_author=author[-1].split(',')[0]
        first_author=first_author.split(' ')[-1]
        # 将当 author,ate和title截取前50个字符拼接成文件名
        filename.append('\"'+f'{first_author}*- {date[-1]} - {title[-1][:30]}'+'*\"')   
        cmd_fatch=command_header+filename[-1]
        os_fatch=subprocess.check_output(cmd_fatch,shell=True)
        if (os_fatch==b''):
            print(f'未找到{filename[-1]}')# 如果未找到pdf则输出提示手动添加一下
        else:
            filedict.append(os_fatch.decode("utf-8").strip('\n'))
        file.write(filedict[-1]+'\n'+author[-1]+'\n')
        os.system(f'/bin/cp \'{filedict[-1]}\'  {os.getcwd()}/{dict_name}')# 将pdf复制到指定文件夹
