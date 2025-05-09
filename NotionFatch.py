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

def convert_timestamp_to_date(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
def convert_date_to_timestamp(date):
    return datetime.strptime(date, "%Y-%m-%d").timestamp()

notion = Client(auth=os.getenv("CLIENT_TOKEN"))
db_name = os.getenv("DB_NAME")
db_id = os.getenv("DB_ID")
page_id = os.getenv("PAGE_ID")
startDate_timestamp, doc_names = get_kb_list(db_id)

startDate = convert_timestamp_to_date(startDate_timestamp)
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

pprint(db_values)