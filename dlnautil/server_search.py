from io import StringIO
import logging
import socket
import time
from typing import List, Optional

import requests
from urllib.parse import urlparse
from xml.etree import ElementTree

logging.basicConfig(level=logging.DEBUG)
_logger = logging.getLogger('dlnautil')

_MSEARCH_QUERY = """\
M-SEARCH * HTTP/1.1\r\n
HOST: 239.255.255.250:1900\r\n
MAN: "ssdp:discover"\r\n
MX: 1\r\n
ST: ssdp:all\r\n
"""


def _parse_server(s: str) -> dict:
    results = {}
    f = StringIO(s)
    for l in f.readlines():
        x = l.split(':')
        if len(x) > 2:
            k = x[0].strip()
            v = l.replace(f'{x[0]}:', '').strip()
            results[k] = v
    return results


def _get_servers() -> List:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    sock.settimeout(10)

    sock.sendto(bytearray(_MSEARCH_QUERY, 'utf-8'), ('239.255.255.250', 1900))
    recvs = []

    now = time.time()
    while True:
        try:
            res, from_ = sock.recvfrom(4096)
            if res:
                _logger.debug(f'*** from={from_}')
                _logger.debug(res)
                _logger.debug(res.decode())
                recvs.append(res.decode())
        except socket.timeout:
            _logger.debug('Fin')
            break

        duration = time.time()-now
        if duration > 10:
            _logger.debug('timeout')
            break
        if not res:
            time.sleep(1)

    results = []
    results_set = set()
    for s in recvs:
        item = _parse_server(s)

        if item['USN'] in results_set:
            continue

        if 'ContentDirectory' in item.get('ST', ''):
            _logger.debug('***** found ContentDirectory')
        else:
            continue

        results.append(item)
        results_set.add(item.get('USN', ''))

        for k, v in item.items():
            _logger.debug(f'{k} : {v}')

    sock.close()
    return results


def _parse_xml(node: ElementTree) -> dict:
    ret = {}
    is_retrieve = False
    for c in node:
        # print(f'{c.tag} : {c.attrib} : {c.text}')
        child_ret = _parse_xml(c)
        ret[c.tag] = c.text
        if child_ret:
            ret = child_ret
            is_retrieve = True
            break

        if c.text and 'ContentDirectory' in c.text:
            is_retrieve = True

    if is_retrieve:
        return ret
    else:
        return None


def _build_url(location: str, xml_item: dict) -> dict:
    urlinfo = urlparse(location)
    path = ''
    serviceType = ''
    for k in xml_item.keys():
        if 'controlURL' in k:
            path = xml_item[k]
        if 'serviceType' in k:
            serviceType = xml_item[k]
    return {'url': f'{urlinfo.scheme}://{urlinfo.netloc}{path}', 'serviceType': serviceType}


def _get_server_info(server: dict) -> Optional[dict]:
    if 'ST' not in server or 'LOCATION' not in server:
        _logger.error('lack of info')
        return None

    location = server['LOCATION']
    res = requests.get(location)
    _logger.debug(res)
    if res and res.status_code == 200:
        result = res.text
        # print(result)
        et = ElementTree.fromstring(result)
        ret = _parse_xml(et)
        if ret:
            _logger.debug('===')
            for k, v in ret.items():
                _logger.debug(f'{k} : {v}')
            ret = _build_url(location, ret)
        return ret

    return None


def search():
    return _get_servers()


def _main():
    servers = search()
    _logger.info('****** Found Servers ********')
    for s in servers:
        _logger.info('---')
        _logger.info(s)
        info = _get_server_info(s)
        _logger.info(info)
        s.update(info)
    return servers


if __name__ == '__main__':
    _ = _main()
