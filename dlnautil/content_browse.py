import argparse
from enum import Enum
import json
import logging
import re
import requests
from typing import List, Tuple

from xml.etree import ElementTree

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger('dlnautil')


class ClassType(Enum):
    CONTAINER = 'container'
    ITEM = 'item'


def _parse_item(item_str: str) -> dict:
    item = {}
    _logger.debug(item_str)
    attrs = ['id', 'parentID', 'childCount', 'protocolInfo', 'resolution', 'duration', 'size']
    for a in attrs:
        m = re.search(f'{a}=\"([^\s]+)\"', item_str)
        if m:
            v = m.group().replace(f'{a}=\"', '').replace(f'\"', '')
            item[a] = v

    attrs = ['dc\:title', 'dc\:date', 'upnp\:class','upnp\:album',
             'pv\:extension', 'pv\:modificationTime', 'pv\:addedTime', 'pv\:lastUpdated']
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

    _logger.debug(f'{item_str} : {item}')
    return item


def _extract_items(c: ElementTree, class_type: ClassType) -> List:
    ret = []
    ct = class_type.value
    for m in re.finditer(f'<{ct} .*</{ct}>', c.text):
        items = m.group().split(f'</{ct}>')
        for i in items:
            item = _parse_item(i)
            if item:
                ret.append(item)
    return ret


def _parse_xml_recursive(node: ElementTree, level: int = 0) -> Tuple[List, int, int]:
    level = level+1
    ret = []
    returned = 0
    total = 0
    for c in node:
        # print(f'{level} *** {c.tag} : {c.attrib} : {c.text}')
        results, returned_, total_ = _parse_xml_recursive(c, level)
        ret.extend(results)

        if 'Result' == c.tag:
            _logger.debug('Result------')
            ret.extend(_extract_items(c, ClassType.CONTAINER))
            ret.extend(_extract_items(c, ClassType.ITEM))
        elif 'NumberReturned' == c.tag:
            _logger.debug(f'returned count = {c.text}')
            returned = int(c.text)
        elif 'TotalMatches' == c.tag:
            _logger.debug(f'total count = {c.text}')
            total = int(c.text)

        if returned_ > 0 or total_ > 0:
            returned = returned_
            total = total_

    # print(f'level={level}: {returned}, {total}')

    return ret, returned, total


def _parse(s: str) -> Tuple[List, int, int]:
    et = ElementTree.fromstring(s)
    ret, returned, total = _parse_xml_recursive(et)
    return ret, returned, total


def _request_dlna_one(url: str, st: str, item_id: str = '0', start_index: int = 0) -> Tuple[List, int, int]:
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
              <StartingIndex>{start_index}</StartingIndex>
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
        items, returned, total = _parse(result)
    else:
        _logger.error(f'error{ret.status_code}')

    return items, returned, total


def _request_dlna(url: str, st: str, item_id: str = '0') -> List:
    results, returned, total = _request_dlna_one(url, st, item_id, start_index=0)

    if returned < total:
        start_index = returned
        while start_index < total:
            tmp, returned, total = _request_dlna_one(url, st, item_id, start_index=start_index)
            results.extend(tmp)
            _logger.debug(f'requested : {start_index} ~ {start_index + returned - 1} / {total}')
            if returned == 0:
                break
            start_index += returned

    if len(results) < total:
        _logger.error(f'Can not get all items. {len(results)} / {total}')
    return results


def _get_items_recursive(url: str, st: str, items: List) -> List:
    ret = []
    for child in items:
        if 'container' in child.get('class', ''):
            results = _request_dlna(url, st, child['id'])
            results.extend(_get_items_recursive(url, st, results))
            ret.extend(results)

    _logger.debug(f'*** {len(ret)}')
    return ret


def browse(url: str, st: str, item_id: str = '0', recursive: str = None, output_filename: str = None) -> List:
    _logger.debug(f'request item_id={item_id}')

    root_items = _request_dlna(url, st, item_id)
    items = root_items

    if recursive == 'true':
        items.extend(_get_items_recursive(url, st, root_items))

    if output_filename:
        output_filename = output_filename if output_filename.endswith('.json') else f'{output_filename}.json'
        with open(output_filename, 'w') as f:
            for item in items:
                f.write(json.dumps(item))
        _logger.info(f'output to {output_filename}')
    return items


def _main():
    p = argparse.ArgumentParser()
    p.add_argument('url', help='url')
    p.add_argument('st', help='st')
    p.add_argument('--id', help='item id')
    p.add_argument('--recursive', help='recursive or not (true or false)')
    p.add_argument('--output', help='output file name(json)')
    args = p.parse_args()
    _items = browse(args.url, args.st, args.id, args.recursive, args.output)

    # dump only 10 items
    print(f'##### results = {len(_items)}')
    for item in _items[:5]:
        # print(item)
        _logger.info('---')
        for k, v in item.items():
            _logger.info(f'{k} : {v}')
    '''
    print('....')
    for item in items[-5:]:
        # print(item)
        print('---')
        for k, v in item.items():
            print(f'{k} : {v}')
    '''


if __name__ == '__main__':
    _main()
