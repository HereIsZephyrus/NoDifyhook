import os
from dotenv import load_dotenv
from notion_client import Client
from pprint import pprint
from datetime import datetime
from functools import partial
import requests
import json
import re

def convert_timestamp_to_date(timestamp):
    # 转换为年月日
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
def convert_date_to_timestamp(date):
    return datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()
def split_paragraph(text):
    # 将文本每一句话用换行符分割
    punctuation_pattern = r'[,.。，！？!?]'
    return re.sub(punctuation_pattern, '\n', text)
def check_file_exist(file_list, file_name):
    if file_name in file_list:
        return True
    else:
        return False

def get_full_info(properties):
    title = properties['Title']['rich_text'][0]['plain_text']
    author = properties['Authors']['rich_text'][0]['plain_text']
    zotero_url = properties['Zotero URI']['url']
    url = properties['URL']['url']
    year = properties['Year']['number']
    intext_citation  = properties['In-Text Citation']['rich_text'][0]['plain_text']
    basic_info = f"title: {title}\nauthor: {author}\nzotero_url: {zotero_url}\nurl: {url}\nyear: {year}\nintext_citation: {intext_citation}"
    if (len(properties['Region']['rich_text']) > 0):
        region = properties['Region']['rich_text'][0]['plain_text']
        basic_info += f"\nregion: {region}"

    abstract = split_paragraph(properties['Abstract']['rich_text'][0]['plain_text'])

    note_info = ""
    if (len(properties['Methods']['rich_text']) > 0):
        methods = properties['Methods']['rich_text'][0]['plain_text']
        note_info += f"methods: {methods}\n"
    if (len(properties['Problem or Purpose']['rich_text']) > 0):
        problem = properties['Problem or Purpose']['rich_text'][0]['plain_text']
        note_info += f"problem: {problem}\n"
    if (len(properties['Key Findings']['rich_text']) > 0):
        keyfindings = properties['Key Findings']['rich_text'][0]['plain_text']
        note_info += f"keyfindings: {keyfindings}\n"
    if (len(properties['Theoretical/Conceptual Framework']['rich_text']) > 0):
        framework = properties['Theoretical/Conceptual Framework']['rich_text'][0]['plain_text']
        note_info += f"framework: {framework}\n"
    
    note_info = split_paragraph(note_info)
    return f"basic_info:\n{basic_info}\nabstract:\n{abstract}\nnote_info:\n{note_info}\n"

def get_kb_page(kb_id, api_key, page_index):
    url = f'http://dify.channingtong.cn/v1/datasets/{kb_id}/documents'
    headers = {'Authorization': f'Bearer {api_key}'}
    query_params = {'page': page_index, 'limit': 50}
    try:
        response = requests.get(url, headers=headers, params=query_params)
        # 检查响应内容是否为空
        if not response.text:
            print("Warning: Empty response received")
            return 0, False
            
        print(f"Response content: {response.text[:200]}")  # 只打印前200个字符
        
        try:
            list = response.json()
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Full response content: {response.text}")
            return 0, False
        
        # 提取每个文档的name和created_at
        last_created_at = 0
        for doc in list['data']:
            current_created_at = int(doc['created_at'])
            if current_created_at > last_created_at:
                last_created_at = current_created_at
        
        return last_created_at, list['has_more']
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        if hasattr(e.response, 'text'):
            print(f"Error response content: {e.response.text}")
        return -1, False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return -1, False

def get_kb_list(calc_kb_page):
    page_index = 1
    has_more = True
    total_last_created_at = 0
    while has_more:
        last_created_at, has_more = calc_kb_page(page_index=page_index)
        if last_created_at > total_last_created_at:
            total_last_created_at = last_created_at
        page_index += 1
    return total_last_created_at
    

def post_file(kb_id, api_key,identifier, full_info):
    url = f"http://dify.channingtong.cn/v1/datasets/{kb_id}/document/create_by_text"
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    request_body = {
        "name": identifier,
        "text": full_info,
        "indexing_technique": "high_quality",
        "doc_form": "hierarchical_model",
        "doc_language": "Chinese",
        "process_rule": {
            "mode": "custom",
            "rules": {
                "pre_process_rules": [],
                "segmentation":{
                    "separator": "\n\n",
                    "max_length": 4000,
                },
                "parent_mode": "full-doc",
                "subchunk_segmentation":{
                    "separator": "\n",
                    "max_length": 128,
                }
            }
        }
    }
    response = requests.post(url, headers=headers, json=request_body)
    print(response.json())

def main(client_token : str, db_id : str, kb_id : str, api_key : str):
    notion = Client(auth=client_token)
    calc_kb_page = partial(get_kb_page, kb_id=kb_id, api_key=api_key)
    startDate_timestamp = get_kb_list(calc_kb_page)
    startDate = convert_timestamp_to_date(startDate_timestamp)
    try:
        db_values = notion.databases.query(
                **{
                    "database_id": db_id,
                    "filter": {
                        "property": "last_modified",
                        "date": {"after": startDate}
                    }
                }
        ).get("results")
    # 打印db_values)
    except Exception as e:
        print(e)

    for item in db_values:
        last_modified_timestamp = convert_date_to_timestamp(item['last_edited_time'])
        if last_modified_timestamp < startDate_timestamp:
            continue
        identifier = f'{item['id']}.txt'
        properties = item['properties']
        full_info = get_full_info(properties)
        post_file(kb_id, api_key,identifier, full_info)

if __name__ == "__main__":
    load_dotenv()
    DB_ID = os.getenv("DB_ID")
    KB_ID = os.getenv("KB_ID")
    API_KEY = os.getenv("API_KEY")
    CLIENT_TOKEN = os.getenv("CLIENT_TOKEN")
    main(client_token=CLIENT_TOKEN, db_id=DB_ID, kb_id=KB_ID, api_key=API_KEY)