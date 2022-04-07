from io import StringIO
import logging
import socket
import time
from typing import List, Optional

import requests
from urllib.parse import urlparse
from xml.etree import ElementTree

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger('dlnautil')

_MSEARCH_QUERY = """\
M-SEARCH * HTTP/1.1\r\n
HOST: 239.255.255.250:1900\r\n
MAN: "ssdp:discover"\r\n
MX: 1\r\n
ST: ssdp:all\r\n
"""


class Server:
    def __init__(self, info: dict):
        self.info = info
        self.detail = None

    def _parse_xml(self, node: ElementTree) -> dict:
        ret = {}
        is_retrieve = False
        for c in node:
            # print(f'{c.tag} : {c.attrib} : {c.text}')
            child_ret = self._parse_xml(c)
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

    def _build_control_url(self, location: str, xml_item: dict) -> dict:
        parse_key = ['controlURL', 'serviceType', 'serviceId', 'SCPDURL', 'eventSubURL']
        ret = {}
        for k in xml_item.keys():
            for pk in parse_key:
                if pk in k:
                    ret[pk] = xml_item[k]
                    break

        path = ret['controlURL']
        if path:
            urlinfo = urlparse(location)
            ret['url'] = f'{urlinfo.scheme}://{urlinfo.netloc}{path}'
            del ret['controlURL']
        return ret

    def fetch_detail(self):
        location = self.info.get('LOCATION')
        stype = self.info.get('ST')
        if not location or not stype:
            _logger.error('lack of info')
            return

        res = requests.get(location)
        _logger.debug(res)
        if res and res.status_code == 200:
            result = res.text
            # print(result)
            et = ElementTree.fromstring(result)
            ret = self._parse_xml(et)
            if ret:
                self.detail = self._build_control_url(location, ret)

    def uniqueid(self):
        return self.info.get('USN')

    def get_info(self):
        return self.info.copy()

    def get_detail(self):
        return self.detail.copy()

    def dump_info(self, is_debug=True):
        logger_func = _logger.debug if is_debug else _logger.info
        for k, v in self.info.items():
            logger_func(f'{k} : {v}')

    def dump_detail(self, is_debug=True):
        logger_func = _logger.debug if is_debug else _logger.info
        for k, v in self.detail.items():
            logger_func(f'{k} : {v}')

    def __eq__(self, other):
        if isinstance(other, Server):
            return self.uniqueid() == other.uniqueid()
        return False

    def __str__(self):
        ret = '--- info ---\n'
        for k, v in self.info.items():
            ret += f'{k} : {v}\n'
        ret += '--- detail ---\n'
        for k, v in self.detail.items():
            ret += f'{k} : {v}\n'
        return ret

    def __hash__(self):
        return hash(self.uniqueid())


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

    results_set = set()
    for s in recvs:
        item = _parse_server(s)

        if item['USN'] in results_set:
            continue

        if 'ContentDirectory' not in item.get('ST', ''):
            continue

        _logger.debug('***** found ContentDirectory')

        server = Server(item)
        server.fetch_detail()
        server.dump_info()
        results_set.add(server)

    sock.close()
    return list(results_set)


def search() -> List[Server]:
    """Search DLNA ContentDirectory server information

    :return: list of ContentDirectory server information
    """
    return _get_servers()


def _main():
    server_infos = search()
    _logger.info('****** Found Servers ********')
    for s in server_infos:
        _logger.info('---')
        _logger.info(s)


if __name__ == '__main__':
    _main()
