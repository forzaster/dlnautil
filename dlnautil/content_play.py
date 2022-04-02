import argparse
import requests
import logging


_logger = logging.getLogger('content_play')


def _request(url: str, action: str, data: str):
    headers = {'Content-Type': "text/xml; charset=utf-8",
               'SOAPACTION': f'"urn:schemas-upnp-org:service:AVTransport:1#{action}"'}
    # print(headers)
    body = f"""\
        <?xml version="1.0"?>
        <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
          <s:Body>
            <u:{action} xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
              {data}
            </u:{action}>
          </s:Body>
        </s:Envelope>
        """
    _logger.debug(url)
    _logger.debug(body)

    body = body.encode('utf-8')
    ret = requests.post(url, data=body, headers=headers)
    _logger.debug(ret.text)

    if ret.status_code == 200:
        _logger.info(f'{action} OK')
    else:
        _logger.error(f'{action} Error : {ret.status_code}')


def set_content_uri(url: str, item_url: str):
    action = 'SetAVTransportURI'
    data = f"""\
              <InstanceID>0</InstanceID>
              <CurrentURI>{item_url}</CurrentURI>
              <CurrentURIMetaData></CurrentURIMetaData>
            """
    _request(url, action, data)


def play(url: str):
    action = 'Play'
    data = f"""\
              <InstanceID>0</InstanceID>
              <Speed>1</Speed>
            """
    _request(url, action, data)


def pause(url: str):
    action = 'Pause'
    data = f"""\
              <InstanceID>0</InstanceID>
            """
    _request(url, action, data)


def stop(url: str):
    action = 'Pause'
    data = f"""\
              <InstanceID>0</InstanceID>
            """
    _request(url, action, data)


def _main():
    p = argparse.ArgumentParser()
    p.add_argument('url', help='renderer url')
    p.add_argument('action', help='action to be called ("set" or "play" or "pause" or "stop")')
    p.add_argument('--item_url', help='item url (needed for action "set"')
    args = p.parse_args()
    if args.action == 'set':
        set_content_uri(args.url, args.item_url)
    elif args.action == 'play':
        play(args.url)
    elif args.action == 'pause':
        pause(args.url)
    elif args.action == 'stop':
        stop(args.url)
    else:
        _logger.error(f'Error : {args.action} not found')
