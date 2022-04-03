import argparse
import logging
import requests
import re

from typing import List
from urllib.parse import urlparse
from xml.etree import ElementTree


logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger('content_play')


def _parse_xml(node: ElementTree, root_namespace: str, is_retrieve: bool = False) -> List:
    ret = {}
    child_ret = []
    extract_tags = ['deviceType', 'friendlyName', 'manufacturer', 'modelName', 'modelNumber']
    for c in node:
        real_tag = c.tag.replace(f'{{{root_namespace}}}', '')
        # print(f'{real_tag} : {c.attrib} : {c.text}')
        is_retrieve_child = True if real_tag == 'service' else False
        # print(f'is_retrieve={is_retrieve_child}')
        child_ret.extend(_parse_xml(c, root_namespace, is_retrieve_child))

        if is_retrieve or real_tag in extract_tags:
            ret[real_tag] = c.text

    if ret:
        child_ret.append(ret)

    return child_ret


def _get_root_namespace(et: ElementTree) -> str:
    m = re.match('{(.*)}(.*)', et.tag)
    if m:
        ns = m.group(1)
        return ns

    return None


def _add_url_to_rendererinfo(url: str, infos: List) -> List:
    urlinfo = urlparse(url)
    for info in infos:
        _logger.debug(f'{info}')
        controlURL = info.get('controlURL')
        if controlURL:
            info['url'] = f'{urlinfo.scheme}://{urlinfo.netloc}{controlURL}'
    return infos


def _request(url: str, action: str, data: str):
    headers = {'Content-Type': "text/xml; charset=utf-8",
               'SOAPACTION': f'"urn:schemas-upnp-org:service:AVTransport:1#{action}"'}
    body = f"""<?xml version="1.0"?>
               <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
                 <s:Body>
                   <u:{action} xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
                   {data}
                   </u:{action}>
                 </s:Body>
               </s:Envelope>"""
    _logger.debug(url)
    _logger.debug(headers)
    _logger.debug(body)

    body = body.encode('utf-8')
    ret = requests.post(url, data=body, headers=headers)
    _logger.debug(ret.text)

    if ret.status_code == 200:
        _logger.info(f'{action} OK')
    else:
        _logger.error(f'{action} Error : {ret.status_code}')


def get_rendererinfo(url: str):
    """Get renderer information.

    :param url: renderer URL for description
    :return: list of renderer various control URLs
    """
    headers = {'Content-Type': "text/xml; charset=utf-8"}
    ret = requests.get(url, headers=headers)

    if ret.status_code == 200:
        # print(ret.text)
        et = ElementTree.fromstring(ret.text)
        root_ns = _get_root_namespace(et)
        infos = _parse_xml(et, root_ns)
        infos = _add_url_to_rendererinfo(url, infos)
        return infos
    else:
        _logger.error(f'Error : {ret.status_code}')


def set_content_uri(url: str, item_url: str):
    """Set content URL to play.

    :param url: Renderer SetAVTransport control URL
    :param item_url: content URL
    :return:
    """
    action = 'SetAVTransportURI'
    data = f"""<InstanceID>0</InstanceID>
               <CurrentURI>{item_url}</CurrentURI>
               <CurrentURIMetaData></CurrentURIMetaData>"""
    _request(url, action, data)


def play(url: str):
    """Play (set_content_uri should be called before play)

    :param url: Renderer SetAVTransport control URL
    :return:
    """
    action = 'Play'
    data = f"""<InstanceID>0</InstanceID>
               <Speed>1</Speed>"""
    _request(url, action, data)


def pause(url: str):
    """Pause

    :param url:
    :return:
    """
    action = 'Pause'
    data = '<InstanceID>0</InstanceID>'
    _request(url, action, data)


def stop(url: str):
    """Stop

    :param url:
    :return:
    """
    action = 'Stop'
    data = '<InstanceID>0</InstanceID>'
    _request(url, action, data)


def _main():
    p = argparse.ArgumentParser()
    p.add_argument('url', help='renderer url (rederer description URL for get_renderinfo\nAVControl URL for contents play')
    p.add_argument('action', help='action to be called ("set" or "play" or "pause" or "stop")')
    p.add_argument('--item_url', help='item url (needed for action "set"')
    args = p.parse_args()
    if args.action == 'get_rendererinfo':
        infos = get_rendererinfo(args.url)
        for i, info in enumerate(infos):
            renderer_url = info.get('url')
            if renderer_url:
                _logger.info(f'{i} renderURL: {renderer_url}')
            service_type = info.get('serviceType')
            if service_type:
                _logger.info(f'{i} serviceType: {service_type}')
    elif args.action == 'set':
        set_content_uri(args.url, args.item_url)
    elif args.action == 'play':
        play(args.url)
    elif args.action == 'pause':
        pause(args.url)
    elif args.action == 'stop':
        stop(args.url)
    else:
        _logger.error(f'Error : {args.action} not found')


if __name__ == '__main__':
    _main()
