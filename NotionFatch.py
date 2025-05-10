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
def check_empty(json):
    if (len(json) == 0):
        return ""
    else:
        return json[0]['plain_text']
def split_paragraph(text):
    # 将文本每一句话用换行符分割
    punctuation_pattern = r'[,.。，！？!?]'
    return re.sub(punctuation_pattern, '\n', text)
def check_file_exist(file_list, file_name):
    if file_name in file_list:
        return True
    else:
        return False

def fetch_all_notion_database_pages(client_token: str, db_id: str, filter_: dict) -> list:
    result = []
    notion = Client(auth=client_token)
    has_more = True
    start_cursor = None
    
    while has_more:
        try:
            response = notion.databases.query(
                database_id=db_id,
                filter=filter_,
                start_cursor=start_cursor,
                page_size=100  # 每次获取100条记录
            )
            
            # 添加当前页的结果
            result.extend(response.get("results", []))
            
            # 检查是否还有更多页面
            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")
            
        except Exception as e:
            print(f"Error fetching database pages: {e}")
            break
    
    return result

def get_full_info(properties):
    title = check_empty(properties['Title']['rich_text'])
    author = check_empty(properties['Authors']['rich_text'])
    zotero_url = properties['Zotero URI']['url']
    url = properties['URL']['url']
    year = properties['Year']['number']
    intext_citation  = check_empty(properties['In-Text Citation']['rich_text'])
    basic_info = f"title: {title}\nauthor: {author}\nzotero_url: {zotero_url}\nurl: {url}\nyear: {year}\nintext_citation: {intext_citation}"
    if (len(properties['Region']['rich_text']) > 0):
        region = properties['Region']['rich_text'][0]['plain_text']
        basic_info += f"\nregion: {region}"

    if (len(properties['Abstract']['rich_text']) > 0):
        abstract = split_paragraph(properties['Abstract']['rich_text'][0]['plain_text'])
    else:
        abstract = ""

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

def get_kb_page(kb_id, api_key, page_index, base_url):
    url = f'{base_url}/datasets/{kb_id}/documents'
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
    

def post_file(kb_id, api_key,identifier, full_info, base_url):
    url = f"{base_url}/datasets/{kb_id}/document/create_by_text"
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
            "mode": "hierarchical",
            "rules": {
                "pre_processing_rules": [
                    {
                        "id": "remove_extra_spaces",
                        "enabled": False,
                    },
                    {
                        "id": "remove_urls_emails",
                        "enabled": False,
                    }
                ],
                "segmentation": {
                    "separator": "\n",
                    "max_tokens": 4000,
                },
                "parent_mode": "full-doc",
                "subchunk_segmentation": {
                    "separator": "\n",
                    "max_tokens": 128,
                }
            }
        }
    }
    response = requests.post(url, headers=headers, json=request_body)
    print(f"Response status code: {response.status_code}")

def main(client_token : str, db_id : str, kb_id : str, api_key : str, base_url : str):
    notion = Client(auth=client_token)
    calc_kb_page = partial(get_kb_page, kb_id=kb_id, api_key=api_key, base_url=base_url)
    startDate_timestamp = get_kb_list(calc_kb_page)
    startDate = convert_timestamp_to_date(startDate_timestamp)
    filter=  {
            "property": "last_modified",
            "date": {"after": startDate}
        }
    try:
        db_values = fetch_all_notion_database_pages(client_token, db_id, filter)
    except Exception as e:
        print(e)

    num = 0
    for item in db_values:
        last_modified_timestamp = convert_date_to_timestamp(item['last_edited_time'])
        if last_modified_timestamp < startDate_timestamp:
            continue
        identifier = f'{item['id']}.txt'
        properties = item['properties']
        full_info = get_full_info(properties)
        post_file(kb_id, api_key,identifier, full_info, base_url)
        num += 1

    print(f"Total number of documents updated: {num}")

if __name__ == "__main__":
    load_dotenv()
    DB_ID = os.getenv("DB_ID")
    KB_ID = os.getenv("KB_ID")
    API_KEY = os.getenv("API_KEY")
    CLIENT_TOKEN = os.getenv("CLIENT_TOKEN")
    BASE_URL = os.getenv("BASE_URL")
    main(client_token=CLIENT_TOKEN, db_id=DB_ID, kb_id=KB_ID, api_key=API_KEY, base_url=BASE_URL)