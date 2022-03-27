import argparse
import re
import requests
from typing import List

import pandas as pd
from xml.etree import ElementTree


_DEBUG_LOG = False


def parse_item(item_str: str) -> dict:
    item = {}
    if _DEBUG_LOG:
        print(item_str)
    attrs = ['id', 'parentID', 'childCount', 'protocolInfo', 'resolution']
    for a in attrs:
        m = re.search(f'{a}=\"([^\s]+)\"', item_str)
        if m:
            v = m.group().replace(f'{a}=\"', '').replace(f'\"', '')
            item[a] = v

    attrs = ['dc\:title', 'upnp\:class']
    for a in attrs:
        m = re.search(f'<{a}>([^\s]+)</{a}>', item_str)
        if m:
            a_ = a.replace('\\', '')
            v = m.group().replace(f'<{a_}>', '').replace(f'</{a_}>', '')
            item[a.split(':')[-1]] = v

    m = re.search(f'<res .*>([^\s]+)</res>', item_str)
    if m:
        v = m.group(1).replace(f'<{a_}>', '').replace(f'</{a_}>', '')
        item['res'] = v

    if _DEBUG_LOG:
        print(f'{item_str} : {item}')
    return item


def parse_xml(node: ElementTree, level: int = 0) -> List:
    level = level+1
    ret = []
    for c in node:
        # print(f'{level} *** {c.tag} : {c.attrib} : {c.text}')
        ret = parse_xml(c, level)
        if 'Result' == c.tag:
            print('Result------')
            for m in re.finditer('<container .*</container>', c.text):
                containers = m.group().split('</container>')
                for ct in containers:
                    item = parse_item(ct)
                    if item:
                        ret.append(item)
            for m in re.finditer('<item .*</item>', c.text):
                containers = m.group().split('</item>')
                for ct in containers:
                    item = parse_item(ct)
                    if item:
                        ret.append(item)
        if ret:
            return ret
    return ret


def parse(s: str) -> List:
    et = ElementTree.fromstring(s)
    ret = parse_xml(et)
    return ret


def request_dlna(url: str, st: str, item_id: str = '0') -> List:
    headers = {'Content-Type': "text/xml; charset=utf-8", 'SOAPACTION': f'{st}#Browse'}
    # print(headers)
    data = f"""\
        <?xml version="1.0"?>
        <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
          <s:Body>
            <u:Browse xmlns:u="{st}">
              <ObjectID>{item_id}</ObjectID>
              <BrowseFlag>BrowseDirectChildren</BrowseFlag>
              <Filter>*</Filter>
              <StartingIndex>0</StartingIndex>
              <RequestedCount>0</RequestedCount>
              <SortCriteria></SortCriteria>
            </u:Browse>
          </s:Body>
        </s:Envelope>
        """
    data = data.encode('utf-8')
    # print(url)
    # print(data)
    ret = requests.post(url, data=data, headers=headers)

    items = []
    if ret.status_code == 200:
        result = ret.text
        # print(ret.text)
        items = parse(result)
    else:
        print(f'error{ret.status_code}')

    return items


def get_items_recursive(url: str, st: str, items: List) -> List:
    ret = []
    for child in items:
        if 'container' in child.get('class', ''):
            results = request_dlna(url, st, child['id'])
            results.extend(get_items_recursive(url, st, results))
            ret.extend(results)

    print(f'*** {len(ret)}')
    return ret


def main(url: str, st: str, item_id: str = '0', recursive: str = None, output_filename: str = None):
    print(f'request {item_id}')

    root_items = request_dlna(url, st, item_id)
    items = root_items

    if recursive == 'true':
        items.extend(get_items_recursive(url, st, root_items))

    # dump only 10 items
    print(f'### results = {len(items)}')
    for item in items[:5]:
        # print(item)
        print('---')
        for k, v in item.items():
            print(f'{k} : {v}')
    print('....')
    for item in items[-5:]:
        # print(item)
        print('---')
        for k, v in item.items():
            print(f'{k} : {v}')

    if output_filename:
        output_filename = output_filename if output_filename.endswith('.csv') else f'{output_filename}.csv'
        df = pd.DataFrame(items)
        df.to_csv(f'{output_filename}.csv', index=False)
        print(f'output to {output_filename}')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('url', help='url')
    p.add_argument('st', help='st')
    p.add_argument('--id', help='item id')
    p.add_argument('--recursive', help='recursive or not (true or false)')
    p.add_argument('--output', help='output file name(csv)')
    args = p.parse_args()
    main(args.url, args.st, args.id, args.recursive, args.output)
